from __future__ import annotations
import os
import uuid
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Tuple
from sqlalchemy.orm import Session

from app import config
from app.database import SessionLocal
from app.models import BackgroundJob, User, ReviewResult
from app.services.settings_service import load_raw_settings
from app.llm.base import JobCancelledError
import contextvars

logger = logging.getLogger(__name__)

_current_job_handle: contextvars.ContextVar[Optional[JobExecutionHandle]] = contextvars.ContextVar(
    "_current_job_handle", default=None
)


def get_current_job_handle() -> Optional[JobExecutionHandle]:
    """Retrieve the JobExecutionHandle active in the current worker thread context."""
    return _current_job_handle.get()


def check_cancellation_point() -> None:
    """Check if the currently executing job has been cancelled, raising JobCancelledError if so."""
    handle = get_current_job_handle()
    if handle and handle.is_cancelled():
        raise JobCancelledError(f"Job {handle.job_id} was cancelled.")



class JobExecutionHandle:
    """
    Tracks concurrency slot reservation, in-flight cancellation events,
    active HTTP clients / resources, and safe single-release of the provider semaphore.
    """

    def __init__(self, job_id: str, provider: str, sem: threading.Semaphore):
        self.job_id = job_id
        self.provider = provider
        self.sem = sem
        self.cancel_event = threading.Event()
        self.slot_released = False
        self._lock = threading.RLock()
        self.active_client: Optional[Any] = None
        self.abort_callbacks: List[Callable[[], None]] = []
        self.timeout_timer: Optional[threading.Timer] = None

    def is_cancelled(self) -> bool:
        return self.cancel_event.is_set()

    def set_active_client(self, client: Any) -> None:
        with self._lock:
            self.active_client = client
            if self.cancel_event.is_set():
                try:
                    client.close()
                except Exception:
                    pass
                raise JobCancelledError(f"Job {self.job_id} was cancelled.")

    def clear_active_client(self, client: Any) -> None:
        with self._lock:
            if self.active_client is client:
                self.active_client = None

    def add_abort_callback(self, cb: Callable[[], None]) -> None:
        with self._lock:
            self.abort_callbacks.append(cb)
            if self.cancel_event.is_set():
                try:
                    cb()
                except Exception:
                    pass

    def release_slot(self) -> None:
        """Idempotently release provider concurrency slot."""
        with self._lock:
            if not self.slot_released:
                self.slot_released = True
                self.sem.release()

    def cancel(self, reason: str = "Job cancelled") -> None:
        """
        Trigger cooperative cancellation:
        1. Set cancellation event
        2. Abort/close in-flight HTTP client immediately
        3. Invoke any registered abort callbacks
        4. Release provider concurrency slot immediately
        """
        with self._lock:
            self.cancel_event.set()
            if self.active_client:
                try:
                    self.active_client.close()
                except Exception as e:
                    logger.debug(f"Error closing client for cancelled job {self.job_id}: {e}")
            for cb in self.abort_callbacks:
                try:
                    cb()
                except Exception as e:
                    logger.debug(f"Error in abort callback for job {self.job_id}: {e}")
            if self.timeout_timer:
                try:
                    self.timeout_timer.cancel()
                except Exception:
                    pass

        # Release concurrency slot immediately without waiting for worker thread
        self.release_slot()

    def wait_or_cancelled(self, timeout_seconds: float) -> bool:
        """Wait for timeout or until cancelled. Returns True if cancelled."""
        return self.cancel_event.wait(timeout_seconds)


class RateLimitExceededError(Exception):
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.message = message
        self.retry_after = retry_after


class JobQueueService:
    """
    Centralized in-process background job execution engine.
    Manages:
    - Provider concurrency limits via threading.Semaphore
    - Dynamic queue position reporting for waiting students
    - Per-student sliding-window rate limiting
    - Multi-threaded worker dispatch for long-running LLM tasks
    - Clean cooperative job cancellation and immediate slot release
    - Watchdog timeouts and startup cleanup
    """

    def __init__(self):
        self._semaphores: Dict[str, threading.Semaphore] = {}
        self._concurrency_limits: Dict[str, int] = {}
        self._running_jobs: Dict[str, Dict[str, Any]] = {}  # job_id -> metadata
        self._job_handles: Dict[str, JobExecutionHandle] = {}  # job_id -> handle
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=64)
        self._boot_time = datetime.utcnow()

    def get_provider_limit(self, provider: str) -> int:
        provider = provider.lower()
        with self._lock:
            if provider in self._concurrency_limits:
                return self._concurrency_limits[provider]

        # Check settings
        raw = load_raw_settings()
        custom_limits = raw.get("concurrency_limits", {})
        if provider in custom_limits:
            return int(custom_limits[provider])

        # Check env
        env_key = f"LLM_CONCURRENCY_{provider.upper()}"
        if env_key in os.environ:
            try:
                return int(os.environ[env_key])
            except ValueError:
                pass

        # Fallback to defaults
        if provider == "ollama":
            return 1
        return 10

    def set_concurrency_limit(self, provider: str, limit: int):
        provider = provider.lower()
        limit = max(1, limit)
        with self._lock:
            self._concurrency_limits[provider] = limit
            self._semaphores[provider] = threading.Semaphore(limit)
        logger.info(f"Updated concurrency limit for provider '{provider}' to {limit}")

    def _ensure_semaphore(self, provider: str) -> threading.Semaphore:
        provider = provider.lower()
        with self._lock:
            if provider not in self._semaphores:
                limit = self.get_provider_limit(provider)
                self._semaphores[provider] = threading.Semaphore(limit)
                self._concurrency_limits[provider] = limit
            return self._semaphores[provider]

    def check_student_rate_limit(self, user_id: int, db: Session) -> None:
        """
        Enforce per-student rate limiting (reviews per hour).
        Raises RateLimitExceededError if student exceeds quota.
        """
        raw_settings = load_raw_settings()
        limit = raw_settings.get("rate_limit_reviews_per_hour", config.DEFAULT_RATE_LIMIT_REVIEWS_PER_HOUR)
        window_seconds = raw_settings.get("rate_limit_window_seconds", config.DEFAULT_RATE_LIMIT_WINDOW_SECONDS)

        cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)

        # Count reviews or background jobs created by student in the window
        recent_jobs = (
            db.query(BackgroundJob)
            .filter(
                BackgroundJob.user_id == user_id,
                BackgroundJob.created_at >= cutoff,
            )
            .order_by(BackgroundJob.created_at.asc())
            .all()
        )

        if len(recent_jobs) >= limit:
            oldest_in_window = recent_jobs[0].created_at
            elapsed = (datetime.utcnow() - oldest_in_window).total_seconds()
            retry_after = max(1, int(window_seconds - elapsed))
            raise RateLimitExceededError(
                message=f"Rate limit exceeded. Maximum {limit} reviews per hour. Please retry after {retry_after} seconds.",
                retry_after=retry_after,
            )

    def calculate_queue_position(self, job_id: str, provider: str, db: Session) -> Optional[int]:
        """
        Calculates position in queue for a job waiting for the given provider.
        Position 1 means next in line.
        """
        job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
        if not job or job.status != "queued":
            return None

        # Count queued jobs for this provider created at or before this job
        prior_jobs_count = (
            db.query(BackgroundJob)
            .filter(
                BackgroundJob.provider == provider,
                BackgroundJob.status == "queued",
                BackgroundJob.created_at <= job.created_at,
            )
            .count()
        )
        return max(1, prior_jobs_count)

    def create_job(
        self,
        user_id: int,
        task_type: str,
        payload: Dict[str, Any],
        provider: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> BackgroundJob:
        """
        Persists a new queued background job in SQLite after validating rate limit
        and performing fail-fast connectivity checks.
        """
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        try:
            # 1. Check rate limit
            self.check_student_rate_limit(user_id, db)

            raw = load_raw_settings()

            # 2. Resolve provider (environment variable overrides settings; settings override defaults)
            if not provider:
                if os.environ.get("LLM_PROVIDER"):
                    provider = os.environ.get("LLM_PROVIDER")
                else:
                    provider = raw.get("provider") or os.environ.get("DEFAULT_LLM_PROVIDER") or config.DEFAULT_LLM_PROVIDER
            provider = provider.lower()

            # 3. Resolve model
            from app.services.settings_service import DEFAULT_MODELS, check_ollama_connectivity
            model = raw.get("model") or DEFAULT_MODELS.get(provider, "")
            if provider == "ollama" and ("gpt" in model.lower() or "claude" in model.lower() or "gemini" in model.lower()):
                model = DEFAULT_MODELS.get("ollama", "qwen2.5:3b")

            # 4. Fail fast if Ollama is selected but unreachable or misconfigured
            if provider == "ollama":
                base_url = raw.get("ollama_base_url", config.DEFAULT_OLLAMA_BASE_URL)
                ok, err_msg = check_ollama_connectivity(base_url)
                if not ok:
                    raise ValueError(err_msg)

            # Store resolved provider & model into payload and job record
            payload = dict(payload or {})
            payload["provider"] = provider
            payload["model"] = model

            job_id = uuid.uuid4().hex[:16]
            job = BackgroundJob(
                id=job_id,
                user_id=user_id,
                task_type=task_type,
                provider=provider,
                model=model,
                status="queued",
                payload=payload,
                result=None,
                error_message=None,
                created_at=datetime.utcnow(),
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            return job
        finally:
            if close_db:
                db.close()

    def enqueue_and_dispatch(
        self,
        job_id: str,
        task_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
        provider: str,
    ):
        """
        Dispatches background task to the threadpool. The worker thread acquires
        the provider's semaphore (respecting concurrency limits) and processes the job.
        """
        self._executor.submit(self._worker_thread, job_id, task_fn, provider)

    def _worker_thread(
        self,
        job_id: str,
        task_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
        provider: str,
    ):
        provider = provider.lower()
        sem = self._ensure_semaphore(provider)

        # Wait to acquire slot within provider concurrency limit (blocks this thread in pool)
        sem.acquire()
        handle = JobExecutionHandle(job_id=job_id, provider=provider, sem=sem)
        token = _current_job_handle.set(handle)

        with self._lock:
            self._job_handles[job_id] = handle

        try:
            # Check if job was cancelled while waiting in the queue
            with SessionLocal() as db:
                job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
                if not job or job.status == "cancelled":
                    logger.info(f"Job {job_id} was cancelled before worker execution; releasing slot.")
                    handle.release_slot()
                    return

                job.status = "running"
                job.started_at = datetime.utcnow()
                payload = dict(job.payload) if job.payload else {}
                # Guarantee provider and model are in payload for dispatchers
                payload["provider"] = job.provider
                payload["model"] = job.model
                task_type = job.task_type
                user_id = job.user_id
                model_name = job.model
                db.commit()

            with self._lock:
                self._running_jobs[job_id] = {
                    "job_id": job_id,
                    "user_id": user_id,
                    "task_type": task_type,
                    "provider": provider,
                    "model": model_name,
                    "started_at": datetime.utcnow().isoformat(),
                }

            # Setup timeout watchdog timer
            max_run_time = self.get_max_run_time_seconds()
            if max_run_time > 0:
                timer = threading.Timer(max_run_time, self._handle_job_timeout, args=[job_id, max_run_time])
                timer.daemon = True
                handle.timeout_timer = timer
                timer.start()

            try:
                # Execute task synchronously
                result = task_fn(payload)

                with SessionLocal() as db:
                    job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
                    # A cancelled job must NEVER be overwritten later by a late "done" result
                    if job and job.status != "cancelled":
                        job.status = "done"
                        job.result = result
                        job.completed_at = datetime.utcnow()
                        db.commit()
            except JobCancelledError:
                logger.info(f"Background job {job_id} aborted cleanly due to cancellation.")
                with SessionLocal() as db:
                    job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
                    if job and job.status not in ["cancelled", "failed"]:
                        job.status = "cancelled"
                        job.error_message = getattr(handle, "cancel_reason", "Cancelled by user") or "Cancelled by user"
                        job.completed_at = datetime.utcnow()
                        db.commit()
            except Exception as e:
                # Check if job was cancelled while the exception happened
                with SessionLocal() as db:
                    job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
                    if job and job.status == "cancelled":
                        logger.info(f"Background job {job_id} was cancelled; ignoring late failure: {e}")
                    elif job:
                        logger.error(f"Background job {job_id} failed: {e}", exc_info=True)
                        err_msg = str(e)
                        # Ensure clear user-friendly message
                        if "unreachable" in err_msg.lower() or "connection" in err_msg.lower():
                            err_msg = f"LLM provider ({provider}) is currently unreachable. Please check network connectivity or host status."
                        elif "429" in err_msg or "rate limit" in err_msg.lower():
                            err_msg = "Hosted provider rate limit exceeded (HTTP 429). The system attempted backoff but the provider remained busy. Please try again in a few moments."
                        elif "timeout" in err_msg.lower():
                            err_msg = "LLM inference request timed out. The model host is currently experiencing high load or slow compute."

                        job.status = "failed"
                        job.error_message = err_msg
                        job.completed_at = datetime.utcnow()
                        db.commit()
            finally:
                if handle.timeout_timer:
                    try:
                        handle.timeout_timer.cancel()
                    except Exception:
                        pass
                with self._lock:
                    self._running_jobs.pop(job_id, None)
                    self._job_handles.pop(job_id, None)
        finally:
            _current_job_handle.reset(token)
            handle.release_slot()

    def get_max_run_time_seconds(self) -> int:
        if "JOB_MAX_RUN_TIME_SECONDS" in os.environ:
            try:
                return int(os.environ["JOB_MAX_RUN_TIME_SECONDS"])
            except ValueError:
                pass
        return config.DEFAULT_JOB_MAX_RUN_TIME_SECONDS

    def _handle_job_timeout(self, job_id: str, timeout_sec: int):
        logger.warning(f"Background job {job_id} exceeded maximum run time of {timeout_sec}s. Aborting.")
        reason = f"Job timed out: exceeded maximum execution time of {timeout_sec}s."
        with SessionLocal() as db:
            job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
            if job and job.status == "running":
                job.status = "failed"
                job.error_message = reason
                job.completed_at = datetime.utcnow()
                db.commit()

        with self._lock:
            handle = self._job_handles.get(job_id)
        if handle:
            handle.cancel(reason=reason)

    def cleanup_stale_jobs_on_startup(self, before: Optional[datetime] = None):
        """
        Safety net: At backend startup, any job left in 'queued' or 'running'
        from a previous run is marked 'failed' with message 'interrupted by restart'.
        """
        cutoff = before or self._boot_time
        with SessionLocal() as db:
            stale_jobs = (
                db.query(BackgroundJob)
                .filter(
                    BackgroundJob.status.in_(["queued", "running"]),
                    BackgroundJob.created_at <= cutoff,
                )
                .all()
            )
            count = len(stale_jobs)
            for j in stale_jobs:
                j.status = "failed"
                j.error_message = "interrupted by restart"
                j.completed_at = datetime.utcnow()
            if count > 0:
                db.commit()
                logger.info(f"Startup queue cleanup: marked {count} stale jobs as 'failed: interrupted by restart'.")

    def cancel_job(
        self,
        job_id: str,
        user_id: Optional[int] = None,
        is_admin: bool = False,
        reason: str = "Cancelled by user",
    ) -> BackgroundJob:
        """
        Cancels a queued or running background job.
        - Enforces ownership: student can cancel only their own jobs; admin can cancel any job.
        - If queued: marks cancelled in DB and removes from queue immediately.
        - If running: aborts in-flight HTTP request, stops backoff, releases slot immediately.
        """
        with SessionLocal() as db:
            job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
            if not job:
                raise ValueError(f"Job '{job_id}' not found.")

            if user_id is not None and not is_admin and job.user_id != user_id:
                raise PermissionError("You can only cancel your own jobs.")

            if job.status in ["done", "failed", "cancelled"]:
                return job

            # Mark as cancelled in DB
            job.status = "cancelled"
            job.error_message = reason
            job.completed_at = datetime.utcnow()
            db.commit()
            db.refresh(job)

        # If running, abort handle immediately
        with self._lock:
            handle = self._job_handles.get(job_id)

        if handle:
            handle.cancel(reason=reason)

        return job

    def cancel_all_student_jobs(self, user_id: int) -> List[str]:
        """Cancel all pending (queued or running) jobs for a student."""
        with SessionLocal() as db:
            jobs = (
                db.query(BackgroundJob)
                .filter(
                    BackgroundJob.user_id == user_id,
                    BackgroundJob.status.in_(["queued", "running"]),
                )
                .all()
            )
            job_ids = [j.id for j in jobs]

        cancelled = []
        for j_id in job_ids:
            try:
                self.cancel_job(j_id, user_id=user_id, is_admin=False)
                cancelled.append(j_id)
            except Exception as e:
                logger.warning(f"Could not cancel job {j_id}: {e}")
        return cancelled

    def get_admin_queue_status(self, db: Session) -> Dict[str, Any]:
        """
        Assembles real-time queue metrics for the Admin view.
        """
        from sqlalchemy import func
        provider_counts = (
            db.query(BackgroundJob.provider, func.count(BackgroundJob.id))
            .filter(BackgroundJob.status == "queued")
            .group_by(BackgroundJob.provider)
            .all()
        )
        provider_queues = {p: count for p, count in provider_counts}

        total_queued = sum(provider_queues.values())

        # Detailed queued jobs list
        queued_records = (
            db.query(BackgroundJob, User.email)
            .join(User, BackgroundJob.user_id == User.id)
            .filter(BackgroundJob.status == "queued")
            .order_by(BackgroundJob.created_at.asc())
            .limit(50)
            .all()
        )
        queued_list = []
        for idx, (j, email) in enumerate(queued_records):
            wait_sec = int((datetime.utcnow() - j.created_at).total_seconds())
            queued_list.append({
                "job_id": j.id,
                "user_id": j.user_id,
                "email": email,
                "task_type": j.task_type,
                "provider": j.provider,
                "queue_position": idx + 1,
                "wait_seconds": wait_sec,
                "created_at": j.created_at.isoformat(),
            })

        # Running jobs list
        running_records = (
            db.query(BackgroundJob, User.email)
            .join(User, BackgroundJob.user_id == User.id)
            .filter(BackgroundJob.status == "running")
            .order_by(BackgroundJob.started_at.asc())
            .all()
        )
        running_list = []
        for j, email in running_records:
            started = j.started_at or j.created_at
            elapsed_sec = int((datetime.utcnow() - started).total_seconds())
            running_list.append({
                "job_id": j.id,
                "user_id": j.user_id,
                "email": email,
                "task_type": j.task_type,
                "provider": j.provider,
                "elapsed_seconds": elapsed_sec,
                "started_at": started.isoformat(),
            })

        # Limits
        limits = {
            "ollama": self.get_provider_limit("ollama"),
            "openai": self.get_provider_limit("openai"),
            "claude": self.get_provider_limit("claude"),
            "gemini": self.get_provider_limit("gemini"),
            "mock": self.get_provider_limit("mock"),
        }

        # Recent timing logs
        from app.services.timing_logger import get_recent_timing_logs
        recent_timings = get_recent_timing_logs(limit=20)

        return {
            "total_queue_length": total_queued,
            "provider_queues": provider_queues,
            "provider_limits": limits,
            "running_jobs_count": len(running_list),
            "running_jobs": running_list,
            "queued_jobs": queued_list,
            "recent_timings": recent_timings,
        }


# Global singleton service
job_queue_service = JobQueueService()
