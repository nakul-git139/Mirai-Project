#!/usr/bin/env python3
"""
Locust Load Test Suite for Placement Readiness Copilot:
Includes two distinct scenarios:
1. Read-Only Traffic Scenario (StudentReadUser):
   100-150 concurrent users querying readiness scores, profile, discovery feed, and tracker.
2. Review-Submission & Queue Scenario (ReviewQueueUser):
   125 concurrent users submitting real resume reviews through the background queue
   with Mock LLM sleeping 1.0 second and per-provider concurrency limits enforced.
   Tracks submit latency, queue wait time, and total completion time.
"""
import os
import sys
import time
import random
from datetime import datetime
from locust import HttpUser, task, between, events

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.auth import create_access_token


def get_or_create_load_tokens(count=125):
    """Ensure at least `count` distinct student accounts exist to test isolated per-student queues."""
    try:
        from app.database import SessionLocal
        from app.models import User, Profile, UserRole
        from app.auth import hash_password

        db = SessionLocal()
        tokens = []
        for i in range(count):
            email = f"load_student_{i}@msot.edu"
            u = db.query(User).filter_by(email=email).first()
            if not u:
                u = User(
                    email=email,
                    hashed_password=hash_password("student123"),
                    role=UserRole.STUDENT,
                    full_name=f"Load Student {i}",
                )
                db.add(u)
                db.commit()
                db.refresh(u)
                p = Profile(user_id=u.id, consent_given=True)
                db.add(p)
                db.commit()
            tokens.append(create_access_token({"sub": str(u.id), "role": u.role, "email": u.email}))
        db.close()
        return tokens
    except Exception:
        return [create_access_token({"sub": "11", "role": "student", "email": "student@msot.edu"})]


LOAD_TOKENS = get_or_create_load_tokens(130)


class StudentReadUser(HttpUser):
    """Simulates realistic student browsing read endpoints."""
    wait_time = between(0.5, 1.5)
    weight = 3

    def on_start(self):
        token = random.choice(LOAD_TOKENS)
        self.headers = {"Authorization": f"Bearer {token}"}

    @task(4)
    def view_readiness_score(self):
        self.client.get("/api/readiness/current", headers=self.headers, name="GET /api/readiness/current")

    @task(2)
    def view_readiness_history(self):
        self.client.get("/api/readiness/history", headers=self.headers, name="GET /api/readiness/history")

    @task(3)
    def view_profile(self):
        self.client.get("/api/profile/me", headers=self.headers, name="GET /api/profile/me")

    @task(2)
    def view_reviews(self):
        endpoint = random.choice([
            "/api/reviews/resume/latest",
            "/api/reviews/linkedin/latest",
            "/api/reviews/github/latest",
        ])
        with self.client.get(endpoint, headers=self.headers, name="GET /api/reviews/{type}/latest", catch_response=True) as resp:
            if resp.status_code in [200, 404]:
                resp.success()

    @task(3)
    def discover_jobs(self):
        self.client.get("/api/jobs/discover", headers=self.headers, name="GET /api/jobs/discover")

    @task(2)
    def view_applications(self):
        self.client.get("/api/tracker/applications", headers=self.headers, name="GET /api/tracker/applications")

    @task(1)
    def student_login(self):
        self.client.post("/api/auth/login", json={"email": "student@msot.edu", "password": "student123"}, name="POST /api/auth/login")

    @task(2)
    def health_check(self):
        self.client.get("/api/health", name="GET /api/health")


_queue_user_idx = 0


class ReviewQueueUser(HttpUser):
    """
    Simulates students submitting background resume review jobs and polling for completion.
    Tests concurrency limit enforcement, queue wait time, submit latency, and total completion time.
    """
    wait_time = between(1.0, 2.0)
    weight = 1

    def on_start(self):
        global _queue_user_idx
        token = LOAD_TOKENS[_queue_user_idx % len(LOAD_TOKENS)]
        _queue_user_idx += 1
        self.headers = {"Authorization": f"Bearer {token}"}

    @task
    def submit_and_track_review(self):
        start_wall_time = time.time()

        # 1. Submit review job to background queue
        payload = {
            "task_type": "resume_review",
            "provider": "mock",
            "payload": {
                "file_path": "backend/tests/fixtures/clean_1page_resume.pdf",
                "filename": "clean_1page_resume.pdf",
            },
        }

        with self.client.post(
            "/api/jobs/trigger",
            json=payload,
            headers=self.headers,
            name="POST /api/jobs/trigger (submit review)",
            catch_response=True,
        ) as resp:
            if resp.status_code != 202:
                resp.failure(f"Expected HTTP 202 Accepted, got {resp.status_code}: {resp.text}")
                return
            resp.success()
            data = resp.json()
            job_id = data.get("id")

        if not job_id:
            return

        # 2. Poll job status until done or timeout (max 45 seconds)
        poll_start = time.time()
        job_done = False
        queue_wait_ms = None
        total_completion_ms = None

        while time.time() - poll_start < 45.0:
            time.sleep(0.4)
            with self.client.get(
                f"/api/jobs/status/{job_id}",
                headers=self.headers,
                name="GET /api/jobs/status (poll queue)",
                catch_response=True,
            ) as poll_resp:
                if poll_resp.status_code != 200:
                    poll_resp.failure(f"Poll returned status {poll_resp.status_code}")
                    break

                job_info = poll_resp.json()
                st = job_info.get("status")

                if st == "done":
                    job_done = True
                    poll_resp.success()
                    total_completion_ms = (time.time() - start_wall_time) * 1000.0

                    c_at = job_info.get("created_at")
                    s_at = job_info.get("started_at")
                    if c_at and s_at:
                        try:
                            # Parse ISO timestamps
                            dt_c = datetime.fromisoformat(c_at.replace("Z", "+00:00"))
                            dt_s = datetime.fromisoformat(s_at.replace("Z", "+00:00"))
                            queue_wait_ms = max(0.0, (dt_s - dt_c).total_seconds() * 1000.0)
                        except Exception:
                            queue_wait_ms = 0.0

                    # Fire custom Locust request metrics
                    if queue_wait_ms is not None:
                        events.request.fire(
                            request_type="QUEUE",
                            name="Queue Wait Duration (ms)",
                            response_time=queue_wait_ms,
                            response_length=0,
                            exception=None,
                        )

                    events.request.fire(
                        request_type="JOB",
                        name="Review Total Completion Duration (ms)",
                        response_time=total_completion_ms,
                        response_length=0,
                        exception=None,
                    )
                    break

                elif st == "failed":
                    poll_resp.failure(f"Job failed: {job_info.get('error_message')}")
                    break
