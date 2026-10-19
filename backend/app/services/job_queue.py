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

logger = logging.getLogger(__name__)


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
    """

    def __init__(self):
        self._semaphores: Dict[str, threading.Semaphore] = {}
        self._concurrency_limits: Dict[str, int] = {}
        self._running_jobs: Dict[str, Dict[str, Any]] = {}  # job_id -> metadata
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=64)

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
        Persists a new queued background job in SQLite after validating rate limit.
        """
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        try:
            # 1. Check rate limit
            self.check_student_rate_limit(user_id, db)

            # 2. Resolve provider
            if not provider:
                raw = load_raw_settings()
                provider = raw.get("provider") or os.environ.get("DEFAULT_LLM_PROVIDER") or os.environ.get("LLM_PROVIDER", "ollama")
            provider = provider.lower()

            job_id = uuid.uuid4().hex[:16]
            job = BackgroundJob(
                id=job_id,
                user_id=user_id,
                task_type=task_type,
                provider=provider,
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
        try:
            with SessionLocal() as db:
                job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
                if not job:
                    return
                job.status = "running"
                job.started_at = datetime.utcnow()
                payload = dict(job.payload) if job.payload else {}
                task_type = job.task_type
                user_id = job.user_id
                db.commit()

            with self._lock:
                self._running_jobs[job_id] = {
                    "job_id": job_id,
                    "user_id": user_id,
                    "task_type": task_type,
                    "provider": provider,
                    "started_at": datetime.utcnow().isoformat(),
                }

            try:
                # Execute task synchronously
                result = task_fn(payload)

                with SessionLocal() as db:
                    job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
                    if job:
                        job.status = "done"
                        job.result = result
                        job.completed_at = datetime.utcnow()
                        db.commit()
            except Exception as e:
                logger.error(f"Background job {job_id} failed: {e}", exc_info=True)
                err_msg = str(e)
                # Ensure clear user-friendly message
                if "unreachable" in err_msg.lower() or "connection" in err_msg.lower():
                    err_msg = f"LLM provider ({provider}) is currently unreachable. Please check network connectivity or host status."
                elif "429" in err_msg or "rate limit" in err_msg.lower():
                    err_msg = "Hosted provider rate limit exceeded (HTTP 429). The system attempted backoff but the provider remained busy. Please try again in a few moments."
                elif "timeout" in err_msg.lower():
                    err_msg = "LLM inference request timed out. The model host is currently experiencing high load or slow compute."

                with SessionLocal() as db:
                    job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
                    if job:
                        job.status = "failed"
                        job.error_message = err_msg
                        job.completed_at = datetime.utcnow()
                        db.commit()
            finally:
                with self._lock:
                    self._running_jobs.pop(job_id, None)
        finally:
            sem.release()

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
