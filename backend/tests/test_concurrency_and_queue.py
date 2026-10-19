from __future__ import annotations
import os
import time
import asyncio
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.database import SessionLocal, get_db
from app.models import User, Profile, BackgroundJob, UserRole
from app.services.job_queue import job_queue_service, RateLimitExceededError
from app.llm.base import LLMMessage, LLMResponse, LLMProviderRateLimitError
from app.llm.adapters.mock_adapter import MockLLMAdapter
from app.llm.adapters.ollama_adapter import OllamaAdapter
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
    email_a = f"student_a_{ts}@mirai.dev"
    email_b = f"student_b_{ts}@mirai.dev"
    email_admin = f"admin_{ts}@mirai.dev"

    client.post("/api/auth/register", json={"email": email_a, "password": "password123", "role": "student"})
    client.post("/api/auth/register", json={"email": email_b, "password": "password123", "role": "student"})
    client.post("/api/auth/register", json={"email": email_admin, "password": "password123", "role": "admin"})

    res_a = client.post("/api/auth/login", json={"email": email_a, "password": "password123"}).json()
    res_b = client.post("/api/auth/login", json={"email": email_b, "password": "password123"}).json()
    res_admin = client.post("/api/auth/login", json={"email": email_admin, "password": "password123"}).json()

    headers_a = {"Authorization": f"Bearer {res_a['access_token']}"}
    headers_b = {"Authorization": f"Bearer {res_b['access_token']}"}
    headers_admin = {"Authorization": f"Bearer {res_admin['access_token']}"}

    # Grant consent for students
    client.post("/api/profile/consent", json={"consent_given": True}, headers=headers_a)
    client.post("/api/profile/consent", json={"consent_given": True}, headers=headers_b)

    with SessionLocal() as db:
        user_a = db.query(User).filter(User.email == email_a).first()
        user_b = db.query(User).filter(User.email == email_b).first()
        admin_user = db.query(User).filter(User.email == email_admin).first()

        id_a, id_b, id_admin = user_a.id, user_b.id, admin_user.id

    return {
        "headers_a": headers_a,
        "headers_b": headers_b,
        "headers_admin": headers_admin,
        "user_a_id": id_a,
        "user_b_id": id_b,
        "admin_id": id_admin,
    }


def test_mock_20_parallel_jobs_concurrency_arithmetic(test_users):
    """
    Verification Requirement 1:
    Submit 20 review requests at once with a mock task that sleeps 1 second.
    Show that they run in parallel up to the limit (10) and that the total time matches the expected value.

    ARITHMETIC EXPLANATION:
    - Total Jobs: 20
    - Provider Concurrency Limit: 10 (hosted / mock default limit)
    - Execution Duration per task: 1.0 second
    - Number of Batches: ceil(20 / 10) = 2 batches
    - Batch 1 (10 jobs): runs from t = 0.0s to t = 1.0s
    - Batch 2 (10 jobs): runs from t = 1.0s to t = 2.0s
    - Expected Total Time: 2.0s
    - Sequential Execution Time would have been: 20 * 1.0s = 20.0s
    - Speedup Factor: 10x
    """
    headers = test_users["headers_a"]
    user_id = test_users["user_a_id"]

    # Configure mock provider limit to 10
    job_queue_service.set_concurrency_limit("mock", 10)

    # Fast task function that sleeps 1.0s to simulate LLM inference
    def slow_mock_task(payload: dict) -> dict:
        time.sleep(1.0)
        return {"status": "success", "job_number": payload.get("num")}

    # Bypass rate limiter temporarily for the 20-job burst test
    with patch.object(job_queue_service, "check_student_rate_limit", return_value=None):
        t0 = time.perf_counter()

        jobs = []
        with SessionLocal() as db:
            for i in range(20):
                j = job_queue_service.create_job(
                    user_id=user_id,
                    task_type="job_match",
                    payload={"num": i},
                    provider="mock",
                    db=db,
                )
                jobs.append(j.id)

        # Dispatch all 20 jobs simultaneously
        for job_id in jobs:
            job_queue_service.enqueue_and_dispatch(job_id, slow_mock_task, "mock")

        # Wait until all 20 jobs finish
        completed_count = 0
        max_wait = 15.0
        while time.perf_counter() - t0 < max_wait:
            with SessionLocal() as db:
                done = db.query(BackgroundJob).filter(
                    BackgroundJob.id.in_(jobs),
                    BackgroundJob.status == "done",
                ).count()
                if done == 20:
                    completed_count = done
                    break
            time.sleep(0.1)

        t_total = time.perf_counter() - t0

    print(f"\n[VERIFICATION 1] 20 Mock Jobs Concurrency Results:")
    print(f"  - Jobs completed: {completed_count}/20")
    print(f"  - Concurrency limit: 10")
    print(f"  - Measured duration: {t_total:.2f}s")
    print(f"  - Expected arithmetic: ceil(20 / 10) * 1.0s = 2.00s")
    print(f"  - Sequential duration would have been: 20.00s")

    assert completed_count == 20, f"Expected 20 completed jobs, got {completed_count}"
    # Verify measured time is close to 2.0s (allow scheduler margin 1.9s to 4.0s, strictly << 20s)
    assert 1.9 <= t_total <= 4.5, f"Total time {t_total:.2f}s did not match expected 2-batch parallel arithmetic (~2.0s)"


def test_ollama_concurrency_limit_and_queue_positions(test_users):
    """
    Verification Requirement 2:
    With Ollama concurrency limited to 1, submit 5 jobs and show they run one at a time,
    with correct queue positions reported to each student.
    """
    headers = test_users["headers_a"]
    user_id = test_users["user_a_id"]

    # Set ollama limit strictly to 1
    job_queue_service.set_concurrency_limit("ollama", 1)

    execution_order = []

    def mock_ollama_worker(payload: dict) -> dict:
        num = payload.get("num")
        time.sleep(0.4)
        execution_order.append(num)
        return {"result": f"done-{num}"}

    with patch.object(job_queue_service, "check_student_rate_limit", return_value=None):
        job_ids = []
        with SessionLocal() as db:
            for i in range(1, 6):
                j = job_queue_service.create_job(
                    user_id=user_id,
                    task_type="job_match",
                    payload={"num": i},
                    provider="ollama",
                    db=db,
                )
                job_ids.append(j.id)

        # Before any finishes, check queue positions
        with SessionLocal() as db:
            pos_1 = job_queue_service.calculate_queue_position(job_ids[0], "ollama", db)
            pos_2 = job_queue_service.calculate_queue_position(job_ids[1], "ollama", db)
            pos_3 = job_queue_service.calculate_queue_position(job_ids[2], "ollama", db)
            pos_4 = job_queue_service.calculate_queue_position(job_ids[3], "ollama", db)
            pos_5 = job_queue_service.calculate_queue_position(job_ids[4], "ollama", db)

        print(f"\n[VERIFICATION 2] Initial Queue Positions: #{pos_1}, #{pos_2}, #{pos_3}, #{pos_4}, #{pos_5}")
        assert pos_1 == 1
        assert pos_2 == 2
        assert pos_3 == 3
        assert pos_4 == 4
        assert pos_5 == 5

        # Dispatch all 5
        for j_id in job_ids:
            job_queue_service.enqueue_and_dispatch(j_id, mock_ollama_worker, "ollama")

        # Wait for completion
        t0 = time.time()
        while time.time() - t0 < 8.0:
            with SessionLocal() as db:
                done_count = db.query(BackgroundJob).filter(
                    BackgroundJob.id.in_(job_ids),
                    BackgroundJob.status == "done",
                ).count()
                if done_count == 5:
                    break
            time.sleep(0.1)

    print(f"[VERIFICATION 2] Execution Order: {execution_order}")
    assert execution_order == [1, 2, 3, 4, 5], f"Expected sequential order [1, 2, 3, 4, 5], got {execution_order}"


def test_rate_limiting_triggers_at_limit_plus_one(client: TestClient, test_users):
    """
    Verification Requirement 4:
    Show that the rate limit triggers on request N+1, the message includes retry time,
    and another student is not affected.
    """
    headers_a = test_users["headers_a"]
    headers_b = test_users["headers_b"]
    user_a_id = test_users["user_a_id"]
    user_b_id = test_users["user_b_id"]

    # Temporarily set limit to 3 reviews per hour for fast deterministic verification
    raw_settings = {"rate_limit_reviews_per_hour": 3, "rate_limit_window_seconds": 3600}
    with patch("app.services.job_queue.load_raw_settings", return_value=raw_settings):
        # 1. Student A submits 3 jobs (N = 3) -> All succeed with HTTP 202
        for i in range(3):
            r = client.post(
                "/api/jobs/trigger",
                json={"task_type": "job_match", "payload": {"item": i}, "provider": "mock"},
                headers=headers_a,
            )
            assert r.status_code == 202, f"Request {i+1} failed with {r.status_code}: {r.text}"

        # 2. Student A submits request N+1 (4th request) -> Triggers HTTP 429
        r_exceeded = client.post(
            "/api/jobs/trigger",
            json={"task_type": "job_match", "payload": {"item": 99}, "provider": "mock"},
            headers=headers_a,
        )
        assert r_exceeded.status_code == 429, f"Expected 429 Too Many Requests, got {r_exceeded.status_code}"
        data = r_exceeded.json()
        assert "Retry-After" in r_exceeded.headers, "Expected Retry-After HTTP header"
        retry_header = int(r_exceeded.headers["Retry-After"])
        assert retry_header > 0, "Expected positive Retry-After seconds"

        detail_text = str(data.get("detail", ""))
        print(f"\n[VERIFICATION 4] Rate Limit Triggered: {detail_text} (Retry-After: {retry_header}s)")
        assert "rate limit exceeded" in detail_text.lower()
        assert "retry after" in detail_text.lower()

        # 3. Student B submits their first review -> Must succeed with HTTP 202 (not affected by Student A)
        r_student_b = client.post(
            "/api/jobs/trigger",
            json={"task_type": "job_match", "payload": {"item": "student_b_test"}, "provider": "mock"},
            headers=headers_b,
        )
        assert r_student_b.status_code == 202, f"Student B was incorrectly blocked: {r_student_b.text}"
        print(f"[VERIFICATION 4] Student B request succeeded with status 202.")


def test_failure_paths_and_queue_resilience(test_users):
    """
    Verification Requirement 5:
    Show that an error/unreachable host causes the job to end as 'failed' with a clear message,
    and that the queue continues processing subsequent jobs afterwards.
    """
    headers = test_users["headers_a"]
    user_id = test_users["user_a_id"]

    job_queue_service.set_concurrency_limit("ollama", 1)

    def failing_task(payload: dict) -> dict:
        raise RuntimeError("Ollama provider (ollama) is currently unreachable at http://10.134.74.254:11434. Network timeout.")

    def successful_subsequent_task(payload: dict) -> dict:
        return {"status": "recovered_successfully"}

    with patch.object(job_queue_service, "check_student_rate_limit", return_value=None):
        with SessionLocal() as db:
            job_fail = job_queue_service.create_job(user_id=user_id, task_type="job_match", payload={}, provider="ollama", db=db)
            job_succ = job_queue_service.create_job(user_id=user_id, task_type="job_match", payload={}, provider="ollama", db=db)
            fail_id = str(job_fail.id)
            succ_id = str(job_succ.id)

        # Dispatch failing job first, then succeeding job
        job_queue_service.enqueue_and_dispatch(fail_id, failing_task, "ollama")
        job_queue_service.enqueue_and_dispatch(succ_id, successful_subsequent_task, "ollama")

        # Wait for completion
        t0 = time.time()
        while time.time() - t0 < 6.0:
            with SessionLocal() as db:
                f_record = db.query(BackgroundJob).filter(BackgroundJob.id == fail_id).first()
                s_record = db.query(BackgroundJob).filter(BackgroundJob.id == succ_id).first()
                if f_record and f_record.status == "failed" and s_record and s_record.status == "done":
                    break
            time.sleep(0.1)

    with SessionLocal() as db:
        f_record = db.query(BackgroundJob).filter(BackgroundJob.id == fail_id).first()
        s_record = db.query(BackgroundJob).filter(BackgroundJob.id == succ_id).first()

        print(f"\n[VERIFICATION 5] Failing job status: {f_record.status}, error: '{f_record.error_message}'")
        print(f"[VERIFICATION 5] Subsequent job status: {s_record.status}, result: {s_record.result}")

        assert f_record.status == "failed"
        assert f_record.error_message is not None
        assert "unreachable" in f_record.error_message.lower()
        # Verify subsequent job in queue executed successfully
        assert s_record.status == "done"
        assert s_record.result == {"status": "recovered_successfully"}


def test_browser_refresh_survival_and_tenant_isolation(client: TestClient, test_users):
    """
    Verification Requirement 6:
    Show that job status and result survive a refresh (student can retrieve it),
    and that Student B receives 403 Forbidden when attempting to access Student A's job.
    """
    headers_a = test_users["headers_a"]
    headers_b = test_users["headers_b"]

    # 1. Student A enqueues a review job
    r_create = client.post(
        "/api/jobs/trigger",
        json={"task_type": "job_match", "payload": {"test": "refresh_data"}, "provider": "mock"},
        headers=headers_a,
    )
    assert r_create.status_code == 202
    job_id = r_create.json()["id"]

    # 2. Simulate browser reload / refresh: Student A fetches their active jobs
    r_active = client.get("/api/jobs/my/active", headers=headers_a)
    assert r_active.status_code == 200

    # Wait for job to finish
    time.sleep(0.5)

    # Student A queries specific job status
    r_status = client.get(f"/api/jobs/status/{job_id}", headers=headers_a)
    assert r_status.status_code == 200
    data = r_status.json()
    assert data["id"] == job_id
    assert data["status"] in ["queued", "running", "done"]
    print(f"\n[VERIFICATION 6] Student A retrieved their job on refresh: status={data['status']}")

    # 3. Student B attempts to access Student A's job -> Must receive HTTP 403 Forbidden
    r_unauthorized = client.get(f"/api/jobs/status/{job_id}", headers=headers_b)
    assert r_unauthorized.status_code == 403, f"Expected 403 Forbidden, got {r_unauthorized.status_code}"
    print(f"[VERIFICATION 6] Tenant isolation verified: Student B received HTTP 403 Forbidden on Student A's job.")


def test_admin_queue_dashboard_authorization(client: TestClient, test_users):
    """
    Verification Requirement 7:
    Show that the admin queue dashboard strictly enforces admin-only access (401 / 403 / 200).
    """
    headers_student = test_users["headers_a"]
    headers_admin = test_users["headers_admin"]

    # 1. Unauthenticated -> 401 Unauthorized
    r_unauth = client.get("/api/admin/llm-queue")
    assert r_unauth.status_code == 401, f"Expected 401, got {r_unauth.status_code}"

    # 2. Student -> 403 Forbidden
    r_student = client.get("/api/admin/llm-queue", headers=headers_student)
    assert r_student.status_code == 403, f"Expected 403, got {r_student.status_code}"

    # 3. Admin -> 200 OK
    r_admin = client.get("/api/admin/llm-queue", headers=headers_admin)
    assert r_admin.status_code == 200, f"Expected 200, got {r_admin.status_code}"
    data = r_admin.json()
    assert "total_queue_length" in data
    assert "running_jobs_count" in data
    assert "provider_limits" in data
    assert "recent_timings" in data

    print(f"\n[VERIFICATION 7] Admin telemetry verified: 401 (unauth) -> 403 (student) -> 200 (admin).")
    print(f"  - Provider Limits: {data['provider_limits']}")
    print(f"  - Total Queue Length: {data['total_queue_length']}")


@pytest.mark.live
def test_live_remote_ollama_five_concurrent_reviews():
    """
    Verification Requirement 3:
    Submit 5 real resume reviews at once to remote Ollama (qwen2.5:3b at http://10.134.74.60:11434)
    and show that they queue and complete one by one with no timeouts or crashes.
    Report the time for each job.
    """
    ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://10.134.74.60:11434")
    good_resume_path = os.path.join(FIXTURES_DIR, "resume_good.pdf")
    with open(good_resume_path, "rb") as f:
        pdf_bytes = f.read()

    job_queue_service.set_concurrency_limit("ollama", 1)

    import base64
    pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")

    # Create 1 test user for the live check
    with SessionLocal() as db:
        test_user = db.query(User).filter(User.role == UserRole.STUDENT).first()
        if not test_user:
            test_user = User(email=f"live_tester_{int(time.time())}@mirai.dev", hashed_password="pw", role=UserRole.STUDENT)
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
        user_id = test_user.id

    from app.services.job_dispatchers import run_resume_review

    # Bypass rate limiter for this specific 5-job live test
    with patch.object(job_queue_service, "check_student_rate_limit", return_value=None):
        jobs = []
        with SessionLocal() as db:
            for i in range(1, 6):
                j = job_queue_service.create_job(
                    user_id=user_id,
                    task_type="resume_review",
                    payload={"file_b64": pdf_b64, "filename": "resume_good.pdf", "user_id": user_id, "provider": "ollama"},
                    provider="ollama",
                    db=db,
                )
                jobs.append(str(j.id))

        t_start = time.perf_counter()
        # Dispatch all 5 simultaneously
        for j_id in jobs:
            job_queue_service.enqueue_and_dispatch(j_id, run_resume_review, "ollama")

        # Monitor each job until all complete
        durations = {}
        max_live_wait = 300.0  # Up to 5 minutes for 5 LLM inferences on remote CPU

        while time.perf_counter() - t_start < max_live_wait:
            with SessionLocal() as db:
                records = db.query(BackgroundJob).filter(BackgroundJob.id.in_(jobs)).all()
                for rec in records:
                    if rec.id not in durations and rec.status in ["done", "failed"]:
                        started = rec.started_at or rec.created_at
                        completed = rec.completed_at or datetime.utcnow()
                        dur = (completed - started).total_seconds()
                        durations[rec.id] = (rec.status, dur, rec.result.get("score") if rec.result else None)

                if len(durations) == 5:
                    break
            time.sleep(1.0)

    t_total = time.perf_counter() - t_start

    print(f"\n[VERIFICATION 3] Live Remote Ollama 5-Job Execution Report (Host: {ollama_url}):")
    print(f"Total Wall Clock Duration: {t_total:.2f}s")
    for idx, j_id in enumerate(jobs, 1):
        status, dur, score = durations.get(j_id, ("unknown", 0.0, None))
        print(f"  - Job #{idx} ({j_id}): status={status}, duration={dur:.2f}s, score={score}")

    assert len(durations) == 5, f"Expected all 5 jobs to complete, but only {len(durations)} completed"
    for j_id, (status, dur, score) in durations.items():
        assert status == "done", f"Job {j_id} did not complete successfully (status={status})"
        assert dur > 0.0, "Expected positive duration"
