#!/usr/bin/env python3
"""
Locust Load Test Suite for Placement Readiness Copilot:
Simulates 100-150 concurrent student users hitting key application endpoints:
- Authentication & Session validation
- Profile retrieval
- 7-Dimension Placement Readiness Score & Progression Analytics
- Resume, LinkedIn, and GitHub Review endpoints
- Job Discovery Feed & Outbound Query generator
- Application Tracker (Table & Kanban views)
"""
import random
from locust import HttpUser, task, between


import os
import sys
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from locust import HttpUser, task, between
from app.auth import create_access_token

def get_seeded_student_tokens():
    try:
        from app.database import SessionLocal
        from app.models import User
        db = SessionLocal()
        tokens = []
        for email in [
            "student@msot.edu",
            "ananya.sharma@msot.edu",
            "rohan.patel@msot.edu",
            "priya.nair@msot.edu",
            "vikram.verma@msot.edu",
            "sneha.reddy@msot.edu",
        ]:
            u = db.query(User).filter_by(email=email).first()
            if u:
                tokens.append(create_access_token({"sub": str(u.id), "role": u.role, "email": u.email}))
        db.close()
        if tokens:
            return tokens
    except Exception:
        pass
    return [
        create_access_token({"sub": "11", "role": "student", "email": "student@msot.edu"}),
        create_access_token({"sub": "82", "role": "student", "email": "ananya.sharma@msot.edu"}),
    ]

PRE_GENERATED_TOKENS = get_seeded_student_tokens()


class StudentUser(HttpUser):
    wait_time = between(0.5, 1.5)

    def on_start(self):
        """Assign a token from the pre-generated pool."""
        token = random.choice(PRE_GENERATED_TOKENS)
        self.headers = {"Authorization": f"Bearer {token}"}

    @task(4)
    def view_readiness_score(self):
        """Check placement readiness composite index and component breakdown."""
        self.client.get(
            "/api/readiness/current",
            headers=self.headers,
            name="GET /api/readiness/current",
        )

    @task(2)
    def view_readiness_history(self):
        """Fetch historical progression snapshots for interactive SVG chart."""
        self.client.get(
            "/api/readiness/history",
            headers=self.headers,
            name="GET /api/readiness/history",
        )

    @task(3)
    def view_profile(self):
        """Fetch candidate profile, verified skills, and declared projects."""
        self.client.get(
            "/api/profile/me",
            headers=self.headers,
            name="GET /api/profile/me",
        )

    @task(2)
    def view_reviews(self):
        """Check review statuses for resume, linkedin, and github."""
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
        """Search job discovery feed with ranking and match scoring."""
        self.client.get(
            "/api/jobs/discover",
            headers=self.headers,
            name="GET /api/jobs/discover",
        )

    @task(2)
    def view_applications(self):
        """List active applications in Table and Kanban tracker."""
        self.client.get(
            "/api/tracker/applications",
            headers=self.headers,
            name="GET /api/tracker/applications",
        )

    @task(1)
    def student_login(self):
        """Simulate realistic concurrent login."""
        self.client.post(
            "/api/auth/login",
            json={"email": "student@msot.edu", "password": "student123"},
            name="POST /api/auth/login",
        )

    @task(2)
    def health_check(self):
        """Liveness ping."""
        self.client.get("/api/health", name="GET /api/health")
