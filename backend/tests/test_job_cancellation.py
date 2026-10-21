from __future__ import annotations
import os
import time
import threading
import base64
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.database import SessionLocal, get_db
from app.models import User, BackgroundJob, UserRole
from app.services.job_queue import (
    job_queue_service,
    check_cancellation_point,
    JobExecutionHandle,
)
from app.llm.base import JobCancelledError
from app.services.settings_service import load_raw_settings
from tests.create_fixtures import FIXTURES_DIR


@pytest.fixture(autouse=True)
def clean_queue():
    """Ensure queue is clean before and after each test."""
    with SessionLocal() as db:
        db.query(BackgroundJob).filter(BackgroundJob.status.in_(["queued", "running"])).delete()
        db.commit()
    yield
    with SessionLocal() as db:
        db.query(BackgroundJob).filter(BackgroundJob.status.in_(["queued", "running"])).delete()
        db.commit()


@pytest.fixture
def client():
    """Client using SessionLocal so background workers share state."""
    app.dependency_overrides.pop(get_db, None)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_users(client: TestClient):
    """Creates Student A, Student B, and Admin test users."""
    ts = int(time.time() * 1000)
    email_a = f"student_a_canc_{ts}@mirai.dev"
    email_b = f"student_b_canc_{ts}@mirai.dev"
    email_admin = f"admin_canc_{ts}@mirai.dev"

    client.post("/api/auth/register", json={"email": email_a, "password": "password123", "role": "student"})
    client.post("/api/auth/register", json={"email": email_b, "password": "password123", "role": "student"})
    client.post("/api/auth/register", json={"email": email_admin, "password": "password123", "role": "admin"})

    res_a = client.post("/api/auth/login", json={"email": email_a, "password": "password123"}).json()
    res_b = client.post("/api/auth/login", json={"email": email_b, "password": "password123"}).json()
    res_admin = client.post("/api/auth/login", json={"email": email_admin, "password": "password123"}).json()

    headers_a = {"Authorization": f"Bearer {res_a['access_token']}"}
    headers_b = {"Authorization": f"Bearer {res_b['access_token']}"}
    headers_admin = {"Authorization": f"Bearer {res_admin['access_token']}"}

    client.post("/api/profile/consent", json={"consent_given": True}, headers=headers_a)
    client.post("/api/profile/consent", json={"consent_given": True}, headers=headers_b)

    with SessionLocal() as db:
        user_a = db.query(User).filter(User.email == email_a).first()
        user_b = db.query(User).filter(User.email == email_b).first()
        admin_user = db.query(User).filter(User.email == email_admin).first()

    return {
        "headers_a": headers_a,
        "headers_b": headers_b,
        "headers_admin": headers_admin,
        "user_a_id": user_a.id,
        "user_b_id": user_b.id,
        "admin_id": admin_user.id,
    }


def test_mock_cancel_queued_job_updates_positions_and_never_runs(client, test_users):
    """
    VERIFICATION 1:
    Mock mode: queue 5 jobs with a slow mock (limit 1).
    Cancel the second one and show the positions of the rest update and that it never runs.
    """
    headers = test_users["headers_a"]
    user_id = test_users["user_a_id"]

    job_queue_service.set_concurrency_limit("mock", 1)

    executed_jobs = []

    def slow_mock_task(payload: dict) -> dict:
        executed_jobs.append(payload["num"])
        time.sleep(0.6)
        return {"status": "ok", "num": payload["num"]}

    with patch.object(job_queue_service, "check_student_rate_limit", return_value=None):
        job_ids = []
        with SessionLocal() as db:
            for i in range(1, 6):
                j = job_queue_service.create_job(
                    user_id=user_id,
                    task_type="job_match",
                    payload={"num": i},
                    provider="mock",
                    db=db,
                )
                job_ids.append(j.id)

        # Dispatch Job 1 (starts immediately)
        job_queue_service.enqueue_and_dispatch(job_ids[0], slow_mock_task, "mock")
        # Let worker acquire slot
        time.sleep(0.1)

        # Dispatch remaining 4 jobs
        for j_id in job_ids[1:]:
            job_queue_service.enqueue_and_dispatch(j_id, slow_mock_task, "mock")

        time.sleep(0.1)

        # Check initial queue positions for jobs 2, 3, 4, 5
        pos_before_cancel = {}
        for j_id in job_ids[1:]:
            res = client.get(f"/api/jobs/status/{j_id}", headers=headers).json()
            pos_before_cancel[j_id] = res.get("queue_position")

        print(f"\n[VERIFICATION 1] Queue positions before cancelling Job #2 ({job_ids[1]}):")
        for idx, j_id in enumerate(job_ids[1:], 2):
            print(f"  - Job #{idx} ({j_id}): position #{pos_before_cancel[j_id]}")

        assert pos_before_cancel[job_ids[1]] == 1, "Job #2 should be position 1"
        assert pos_before_cancel[job_ids[2]] == 2, "Job #3 should be position 2"
        assert pos_before_cancel[job_ids[3]] == 3, "Job #4 should be position 3"
        assert pos_before_cancel[job_ids[4]] == 4, "Job #5 should be position 4"

        # Cancel Job #2 while it is queued
        cancel_res = client.post(f"/api/jobs/{job_ids[1]}/cancel", headers=headers)
        assert cancel_res.status_code == 200, f"Expected 200, got {cancel_res.status_code}"
        cancel_data = cancel_res.json()
        assert cancel_data["status"] == "cancelled"

        # Check queue positions after cancelling Job #2
        pos_after_cancel = {}
        for j_id in job_ids[2:]:
            res = client.get(f"/api/jobs/status/{j_id}", headers=headers).json()
            pos_after_cancel[j_id] = res.get("queue_position")

        print(f"[VERIFICATION 1] Queue positions after cancelling Job #2:")
        for idx, j_id in enumerate(job_ids[2:], 3):
            print(f"  - Job #{idx} ({j_id}): position #{pos_after_cancel[j_id]} (was #{pos_before_cancel[j_id]})")

        assert pos_after_cancel[job_ids[2]] == 1, "Job #3 must now be position 1"
        assert pos_after_cancel[job_ids[3]] == 2, "Job #4 must now be position 2"
        assert pos_after_cancel[job_ids[4]] == 3, "Job #5 must now be position 3"

        # Wait for remaining jobs to finish
        t0 = time.time()
        while time.time() - t0 < 8.0:
            with SessionLocal() as db:
                done_count = db.query(BackgroundJob).filter(
                    BackgroundJob.id.in_([job_ids[0], job_ids[2], job_ids[3], job_ids[4]]),
                    BackgroundJob.status == "done",
                ).count()
                if done_count == 4:
                    break
            time.sleep(0.1)

        # Assert Job 2 NEVER ran
        print(f"[VERIFICATION 1] Executed job payloads: {executed_jobs}")
        assert 2 not in executed_jobs, f"Job #2 ran but should have been cancelled! Executed: {executed_jobs}"
        assert set(executed_jobs) == {1, 3, 4, 5}, f"Expected {1, 3, 4, 5}, got {executed_jobs}"

        # Assert Job 2 has status 'cancelled' in DB
        with SessionLocal() as db:
            j2 = db.query(BackgroundJob).filter(BackgroundJob.id == job_ids[1]).first()
            assert j2.status == "cancelled"


def test_cancel_running_job_aborts_provider_releases_slot_within_one_second(client, test_users):
    """
    VERIFICATION 2:
    Cancel the running job and show that the mock provider call was aborted,
    the slot was released, and the next job started within a second.
    Show the cancelled job stays "cancelled" after the mock call would have finished.
    """
    headers = test_users["headers_a"]
    user_id = test_users["user_a_id"]

    job_queue_service.set_concurrency_limit("mock", 1)

    mock_started = threading.Event()
    mock_aborted = threading.Event()
    mock_completed_late = threading.Event()

    def abortable_mock_task(payload: dict) -> dict:
        mock_started.set()
        t0 = time.time()
        try:
            # Simulate a 2.5s inference
            while time.time() - t0 < 2.5:
                check_cancellation_point()
                time.sleep(0.05)
            mock_completed_late.set()
            return {"status": "ok"}
        except JobCancelledError:
            mock_aborted.set()
            raise

    job_2_started = threading.Event()

    def normal_mock_task(payload: dict) -> dict:
        job_2_started.set()
        time.sleep(0.2)
        return {"status": "job2_done"}

    with patch.object(job_queue_service, "check_student_rate_limit", return_value=None):
        with SessionLocal() as db:
            j1 = job_queue_service.create_job(user_id=user_id, task_type="job_match", payload={"name": "j1"}, provider="mock", db=db)
            j2 = job_queue_service.create_job(user_id=user_id, task_type="job_match", payload={"name": "j2"}, provider="mock", db=db)
            j1_id = j1.id
            j2_id = j2.id

        # Dispatch Job 1
        job_queue_service.enqueue_and_dispatch(j1_id, abortable_mock_task, "mock")
        assert mock_started.wait(timeout=2.0), "Job 1 should start running"

        # Dispatch Job 2 (queued, waiting for limit 1 slot)
        job_queue_service.enqueue_and_dispatch(j2_id, normal_mock_task, "mock")
        time.sleep(0.1)

        # Cancel Job 1 while it is running
        t_cancel = time.perf_counter()
        cancel_res = client.post(f"/api/jobs/{j1_id}/cancel", headers=headers)
        assert cancel_res.status_code == 200
        assert cancel_res.json()["status"] == "cancelled"

        # Verify Job 2 starts within 1 second of cancellation
        started_in_time = job_2_started.wait(timeout=1.0)
        t_job_2_started = time.perf_counter() - t_cancel

        print(f"\n[VERIFICATION 2] Running Job Cancellation:")
        print(f"  - Cancel request time: 0.00s")
        print(f"  - Job #2 started elapsed: {t_job_2_started:.3f}s (must be < 1.0s)")
        print(f"  - In-flight mock call aborted event: {mock_aborted.is_set()}")
        print(f"  - Mock completed late event: {mock_completed_late.is_set()}")

        assert started_in_time, f"Job #2 did not start within 1s (took {t_job_2_started:.3f}s)"
        assert t_job_2_started < 1.0, f"Expected slot release within 1s, got {t_job_2_started:.3f}s"
        assert mock_aborted.wait(timeout=1.5), "In-flight provider call must be aborted"
        assert not mock_completed_late.is_set(), "Late completion must not have fired"

        # Wait until after the original 2.5s duration would have finished
        time.sleep(2.6)

        # Verify Job 1 stays 'cancelled' in DB and was not overwritten
        with SessionLocal() as db:
            j1_db = db.query(BackgroundJob).filter(BackgroundJob.id == j1_id).first()
            j2_db = db.query(BackgroundJob).filter(BackgroundJob.id == j2_id).first()

            print(f"  - Final Job #1 status in DB after delay: {j1_db.status} (result={j1_db.result})")
            print(f"  - Final Job #2 status in DB: {j2_db.status}")

            assert j1_db.status == "cancelled", "Job 1 must permanently remain 'cancelled'"
            assert j1_db.result is None, "Job 1 must never have its result overwritten"
            assert j2_db.status == "done"


def test_student_b_cannot_cancel_student_a_job_admin_can(client, test_users):
    """
    VERIFICATION 3:
    Show that student B cannot cancel student A's job (403),
    and that an admin can (200). Also test student cancel-all.
    """
    headers_a = test_users["headers_a"]
    headers_b = test_users["headers_b"]
    headers_admin = test_users["headers_admin"]
    user_a_id = test_users["user_a_id"]

    job_queue_service.set_concurrency_limit("mock", 1)

    with patch.object(job_queue_service, "check_student_rate_limit", return_value=None):
        with SessionLocal() as db:
            job_a = job_queue_service.create_job(user_id=user_a_id, task_type="job_match", payload={"test": 1}, provider="mock", db=db)
            job_a_id = job_a.id

        # 1. Student B attempts to cancel Student A's job -> 403 Forbidden
        res_b = client.post(f"/api/jobs/{job_a_id}/cancel", headers=headers_b)
        print(f"\n[VERIFICATION 3] Student B cancel attempt on Student A job: HTTP {res_b.status_code}")
        assert res_b.status_code == 403, f"Expected 403 Forbidden, got {res_b.status_code}"

        # 2. Admin attempts to cancel Student A's job -> 200 OK
        res_admin = client.post(f"/api/jobs/{job_a_id}/cancel", headers=headers_admin)
        print(f"[VERIFICATION 3] Admin cancel attempt on Student A job: HTTP {res_admin.status_code}")
        assert res_admin.status_code == 200, f"Expected 200 OK, got {res_admin.status_code}"
        assert res_admin.json()["status"] == "cancelled"

        # 3. Test Student "Cancel all my jobs"
        with SessionLocal() as db:
            j_multi_1 = job_queue_service.create_job(user_id=user_a_id, task_type="job_match", payload={"m": 1}, provider="mock", db=db)
            j_multi_2 = job_queue_service.create_job(user_id=user_a_id, task_type="job_match", payload={"m": 2}, provider="mock", db=db)
            id_1 = str(j_multi_1.id)
            id_2 = str(j_multi_2.id)

        res_cancel_all = client.post("/api/jobs/my/cancel-all", headers=headers_a)
        assert res_cancel_all.status_code == 200
        data_all = res_cancel_all.json()
        print(f"[VERIFICATION 3] Cancel all my jobs: {data_all}")
        assert data_all["cancelled_count"] >= 2
        assert id_1 in data_all["cancelled_job_ids"]
        assert id_2 in data_all["cancelled_job_ids"]



def test_startup_cleanup_marks_leftover_jobs_failed_interrupted_by_restart(client, test_users):
    """
    VERIFICATION 4:
    Show the startup cleanup: leave a job "running", restart the backend,
    and show it becomes "failed: interrupted by restart" and does not block the queue.
    """
    user_id = test_users["user_a_id"]

    # Insert simulated orphaned jobs left in DB from an abrupt process termination
    id_stale_1 = f"stale_running_{int(time.time()*1000)}"
    id_stale_2 = f"stale_queued_{int(time.time()*1000)}"
    with SessionLocal() as db:
        hung_running = BackgroundJob(
            id=id_stale_1,
            user_id=user_id,
            task_type="resume_review",
            provider="ollama",
            status="running",
            payload={},
            created_at=datetime.utcnow() - timedelta(minutes=10),
            started_at=datetime.utcnow() - timedelta(minutes=9),
        )
        hung_queued = BackgroundJob(
            id=id_stale_2,
            user_id=user_id,
            task_type="linkedin_review",
            provider="ollama",
            status="queued",
            payload={},
            created_at=datetime.utcnow() - timedelta(minutes=5),
        )
        db.add(hung_running)
        db.add(hung_queued)
        db.commit()

    # Simulate backend restart cleanup
    job_queue_service.cleanup_stale_jobs_on_startup()

    with SessionLocal() as db:
        r1 = db.query(BackgroundJob).filter(BackgroundJob.id == id_stale_1).first()
        r2 = db.query(BackgroundJob).filter(BackgroundJob.id == id_stale_2).first()

        print(f"\n[VERIFICATION 4] Startup cleanup verification:")
        print(f"  - Stale running job status: {r1.status}, error_message: '{r1.error_message}'")
        print(f"  - Stale queued job status: {r2.status}, error_message: '{r2.error_message}'")

        assert r1.status == "failed"
        assert r1.error_message == "interrupted by restart"
        assert r2.status == "failed"
        assert r2.error_message == "interrupted by restart"

    # Confirm queue is completely unblocked and fresh jobs execute normally
    def fast_task(p: dict) -> dict:
        return {"status": "fresh_job_done"}

    with SessionLocal() as db:
        fresh = job_queue_service.create_job(user_id=user_id, task_type="job_match", payload={}, provider="mock", db=db)
        fresh_id = fresh.id

    job_queue_service.enqueue_and_dispatch(fresh_id, fast_task, "mock")

    time.sleep(0.3)
    with SessionLocal() as db:
        fresh_db = db.query(BackgroundJob).filter(BackgroundJob.id == fresh_id).first()
        assert fresh_db.status == "done"
        print(f"  - Fresh job status after restart: {fresh_db.status}")


def test_per_job_maximum_run_time_releases_hung_slot(client, test_users):
    """
    VERIFICATION 5:
    Show the per-job maximum run time releasing a hung job's slot.
    """
    user_id = test_users["user_a_id"]
    job_queue_service.set_concurrency_limit("mock", 1)

    # Set maximum run time to 1 second for this test
    os.environ["JOB_MAX_RUN_TIME_SECONDS"] = "1"

    hung_job_aborted = threading.Event()

    def hung_task(payload: dict) -> dict:
        t0 = time.time()
        try:
            while time.time() - t0 < 10.0:
                check_cancellation_point()
                time.sleep(0.05)
            return {"status": "hung_completed"}
        except JobCancelledError:
            hung_job_aborted.set()
            raise

    job_next_done = threading.Event()

    def next_task(payload: dict) -> dict:
        job_next_done.set()
        return {"status": "next_completed"}

    try:
        with patch.object(job_queue_service, "check_student_rate_limit", return_value=None):
            with SessionLocal() as db:
                hung_j = job_queue_service.create_job(user_id=user_id, task_type="job_match", payload={"hung": True}, provider="mock", db=db)
                next_j = job_queue_service.create_job(user_id=user_id, task_type="job_match", payload={"next": True}, provider="mock", db=db)
                hung_id = hung_j.id
                next_id = next_j.id

            t_start = time.perf_counter()
            job_queue_service.enqueue_and_dispatch(hung_id, hung_task, "mock")
            time.sleep(0.1)
            job_queue_service.enqueue_and_dispatch(next_id, next_task, "mock")

            # Wait for next job to complete (watchdog timeout is 1s, next job should complete in ~1.5s total)
            finished = job_next_done.wait(timeout=3.5)
            t_elapsed = time.perf_counter() - t_start

            print(f"\n[VERIFICATION 5] Max Run Time Watchdog:")
            print(f"  - Configured watchdog timeout: 1.0s")
            print(f"  - Total elapsed until next job completed: {t_elapsed:.2f}s")
            print(f"  - Hung job aborted event: {hung_job_aborted.is_set()}")

            assert finished, "Next job was starved by hung job"
            assert hung_job_aborted.wait(timeout=1.5), "Hung job must have been aborted by watchdog"

            with SessionLocal() as db:
                h_rec = db.query(BackgroundJob).filter(BackgroundJob.id == hung_id).first()
                n_rec = db.query(BackgroundJob).filter(BackgroundJob.id == next_id).first()

                print(f"  - Hung job final status: {h_rec.status}, error: '{h_rec.error_message}'")
                print(f"  - Next job final status: {n_rec.status}")

                assert h_rec.status == "failed"
                assert "exceeded maximum execution time" in h_rec.error_message
                assert n_rec.status == "done"
    finally:
        os.environ.pop("JOB_MAX_RUN_TIME_SECONDS", None)


@pytest.mark.live
def test_live_remote_ollama_cancellation_and_resumption(client, test_users):
    """
    VERIFICATION 6 (Live Check):
    Start a real review on the remote Ollama (qwen2.5:3b), cancel it after a few seconds,
    show that the host stops generating, the slot is released, and a new review runs normally afterwards.
    """
    raw_settings = load_raw_settings()
    ollama_url = raw_settings.get("ollama_base_url", "http://localhost:11434")
    model = raw_settings.get("model", "qwen2.5:3b")

    headers = test_users["headers_a"]
    user_id = test_users["user_a_id"]

    good_resume_path = os.path.join(FIXTURES_DIR, "resume_good.pdf")
    with open(good_resume_path, "rb") as f:
        pdf_bytes = f.read()
    pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")

    job_queue_service.set_concurrency_limit("ollama", 1)

    from app.services.job_dispatchers import run_resume_review

    print(f"\n[VERIFICATION 6] Live Remote Ollama Cancellation Test (Target: {ollama_url}, Model: qwen2.5:3b):")

    with patch.object(job_queue_service, "check_student_rate_limit", return_value=None):
        # 1. Trigger first live resume review
        with SessionLocal() as db:
            j1 = job_queue_service.create_job(
                user_id=user_id,
                task_type="resume_review",
                payload={"file_b64": pdf_b64, "filename": "resume_good.pdf", "user_id": user_id, "provider": "ollama"},
                provider="ollama",
                db=db,
            )
            j1_id = j1.id

        t0 = time.perf_counter()
        job_queue_service.enqueue_and_dispatch(j1_id, run_resume_review, "ollama")

        # Wait until it reaches running state
        while time.perf_counter() - t0 < 10.0:
            with SessionLocal() as db:
                rec = db.query(BackgroundJob).filter(BackgroundJob.id == j1_id).first()
                if rec and rec.status == "running":
                    break
            time.sleep(0.2)

        print(f"  - Job #1 ({j1_id}) entered 'running' at t=+{(time.perf_counter() - t0):.2f}s")

        # Let remote inference run for 2.5 seconds to establish generation on the remote CPU
        time.sleep(2.5)

        # 2. Cancel Job #1 while in-flight
        t_cancel = time.perf_counter()
        cancel_resp = client.post(f"/api/jobs/{j1_id}/cancel", headers=headers)
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "cancelled"

        print(f"  - Job #1 cancel request executed at t=+{(t_cancel - t0):.2f}s (HTTP 200, status=cancelled)")

        # Verify Job #1 status in DB
        with SessionLocal() as db:
            rec1 = db.query(BackgroundJob).filter(BackgroundJob.id == j1_id).first()
            assert rec1.status == "cancelled"

        # 3. Immediately queue a fresh review Job #2
        with SessionLocal() as db:
            j2 = job_queue_service.create_job(
                user_id=user_id,
                task_type="resume_review",
                payload={"file_b64": pdf_b64, "filename": "resume_good.pdf", "user_id": user_id, "provider": "ollama"},
                provider="ollama",
                db=db,
            )
            j2_id = j2.id

        t2_start = time.perf_counter()
        job_queue_service.enqueue_and_dispatch(j2_id, run_resume_review, "ollama")

        # Wait for Job #2 to complete
        job_2_done = False
        max_wait = 60.0
        while time.perf_counter() - t2_start < max_wait:
            with SessionLocal() as db:
                rec2 = db.query(BackgroundJob).filter(BackgroundJob.id == j2_id).first()
                if rec2 and rec2.status in ["done", "failed"]:
                    job_2_done = True
                    break
            time.sleep(1.0)

        t2_elapsed = time.perf_counter() - t2_start
        print(f"  - Job #2 ({j2_id}) completed with status '{rec2.status}' in {t2_elapsed:.2f}s (Score: {rec2.result.get('score') if rec2.result else None})")

        assert job_2_done, f"Job #2 did not complete within {max_wait}s"
        assert rec2.status == "done", f"Job #2 failed: {rec2.error_message}"
        assert rec2.result is not None
        assert rec2.result.get("score") is not None

        # Confirm Job #1 remained cancelled
        with SessionLocal() as db:
            rec1_after = db.query(BackgroundJob).filter(BackgroundJob.id == j1_id).first()
            print(f"  - Job #1 status after Job #2 completed: '{rec1_after.status}'")
            assert rec1_after.status == "cancelled"
