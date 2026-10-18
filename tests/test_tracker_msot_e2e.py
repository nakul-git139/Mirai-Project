#!/usr/bin/env python3
"""
Application Tracker & MSOT Admin Board End-to-End Test Script:
Validates admin campus job posting, benchmark eligibility gating,
student application tracking, admin candidate review & status progression,
has_movement detection, and role-based access control.
Can be run directly (`python tests/test_tracker_msot_e2e.py`) or via pytest (`pytest tests/test_tracker_msot_e2e.py`).
"""
import os
import sys
from datetime import datetime, timedelta
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.main import app
from app.models import User, UserRole, Job, Application, ApplicationStatus, Profile, ReadinessScore
from app.auth import hash_password, create_access_token
from app.database import get_db, SessionLocal


def test_tracker_msot_full_lifecycle(client: TestClient = None, db_session: Session = None):
    # Standalone fallback if invoked without pytest fixtures
    standalone = False
    import uuid
    uid = uuid.uuid4().hex[:6]
    if client is None or db_session is None:
        standalone = True
        client = TestClient(app)
        db_session = SessionLocal()

    try:
        print("\n[Tracker & MSOT] 1. Creating Admin User and Posting Campus Job...")
        admin = User(
            email=f"admin_e2e_tracker_{uid}@msot.edu",
            hashed_password=hash_password("adminpass123"),
            role=UserRole.ADMIN,
            full_name="MSOT Admin Officer",
            is_active=True,
        )
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)

        admin_token = create_access_token(data={"sub": str(admin.id), "role": admin.role, "email": admin.email})
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Admin creates campus job with eligibility: min score 75, React + TypeScript
        job_payload = {
            "title": "Campus Frontend Associate",
            "company": "MSOT Strategic Partner Corp",
            "description": "Fellowship for high-readiness frontend candidates.",
            "requirements": "React & TypeScript proficiency.",
            "location": "Bangalore / Hybrid",
            "url": "https://careers.partnercorp.dev/campus-2026",
            "job_type": "job",
            "is_pinned": True,
            "eligibility_criteria": {
                "min_readiness_score": 75,
                "required_skills": ["React", "TypeScript"],
                "target_roles": ["Frontend Engineer"],
            },
        }
        post_res = client.post("/api/admin/jobs", json=job_payload, headers=admin_headers)
        assert post_res.status_code == 201
        created_job = post_res.json()
        job_id = created_job["id"]
        print(f"  ✓ Admin posted job ID {job_id}: '{created_job['title']}' (Pinned: {created_job['is_pinned']})")

        # 2. Ineligible Student (Score 50) tries to discover
        ineligible = User(
            email=f"student_ineligible_{uid}@msot.edu",
            hashed_password=hash_password("pass123"),
            role=UserRole.STUDENT,
            full_name="Ineligible Bob",
            is_active=True,
        )
        db_session.add(ineligible)
        db_session.commit()
        db_session.refresh(ineligible)
        db_session.add(Profile(user_id=ineligible.id, consent_given=True, skills=["HTML", "CSS"], target_roles=["Frontend Engineer"]))
        db_session.add(ReadinessScore(user_id=ineligible.id, overall_score=50, breakdown={"overall": 50}))
        db_session.commit()

        token_ineligible = create_access_token(data={"sub": str(ineligible.id), "role": ineligible.role, "email": ineligible.email})
        headers_ineligible = {"Authorization": f"Bearer {token_ineligible}"}

        from unittest.mock import patch, AsyncMock
        from app.services.job_discovery import job_discovery_service

        with patch.object(job_discovery_service, "fetch_external_jobs", new_callable=AsyncMock) as mock_ext:
            mock_ext.return_value = []

            res_disc_ineligible = client.get("/api/jobs/discover", headers=headers_ineligible)
            assert res_disc_ineligible.status_code == 200
            ineligible_job_ids = [j["id"] for j in res_disc_ineligible.json()["jobs"]]
            assert job_id not in ineligible_job_ids
            print("  ✓ Ineligible student (score 50) correctly filtered out from institutional job feed.")

            # 3. Eligible Student (Score 85) discovers the job pinned at the top
            eligible = User(
                email=f"student_eligible_{uid}@msot.edu",
                hashed_password=hash_password("pass123"),
                role=UserRole.STUDENT,
                full_name="Alice Frontend",
                is_active=True,
            )
            db_session.add(eligible)
            db_session.commit()
            db_session.refresh(eligible)
            db_session.add(Profile(user_id=eligible.id, consent_given=True, skills=["React", "TypeScript", "Tailwind"], target_roles=["Frontend Engineer"]))
            db_session.add(ReadinessScore(user_id=eligible.id, overall_score=85, breakdown={"overall": 85}))
            db_session.commit()

            token_eligible = create_access_token(data={"sub": str(eligible.id), "role": eligible.role, "email": eligible.email})
            headers_eligible = {"Authorization": f"Bearer {token_eligible}"}

            res_disc_eligible = client.get("/api/jobs/discover", headers=headers_eligible)
            assert res_disc_eligible.status_code == 200
            eligible_jobs = res_disc_eligible.json()["jobs"]
            assert len(eligible_jobs) > 0
            first_job = eligible_jobs[0]
            assert first_job["title"] == created_job["title"]
            assert first_job["is_pinned"] is True
            assert first_job["db_job_id"] == job_id
            print(f"  ✓ Eligible student (score 85) sees campus job pinned at top position.")

        # 4. Student logs application in Tracker
        app_payload = {
            "company": created_job["company"],
            "role": created_job["title"],
            "link": created_job["url"],
            "job_id": job_id,
            "status": "Applied",
            "notes": "Applied via MSOT campus portal.",
        }
        apply_res = client.post("/api/tracker/applications", json=app_payload, headers=headers_eligible)
        assert apply_res.status_code == 201
        app_data = apply_res.json()
        application_id = app_data["id"]
        assert app_data["status"] == "Applied"
        assert len(app_data["status_history"]) == 1
        print(f"  ✓ Student logged application ID {application_id} with status 'Applied'.")

        # 5. Admin queries applicants for the job
        applicants_res = client.get(f"/api/admin/jobs/{job_id}/applicants", headers=admin_headers)
        assert applicants_res.status_code == 200
        applicants = applicants_res.json()
        assert len(applicants) == 1
        assert applicants[0]["student_email"] == f"student_eligible_{uid}@msot.edu"
        assert applicants[0]["readiness_score"] == 85
        print(f"  ✓ Admin viewed applicant '{applicants[0]['student_name']}' with readiness score {applicants[0]['readiness_score']}.")

        # 6. Admin promotes student to 'Interview'
        promote_res = client.patch(
            f"/api/admin/jobs/{job_id}/applicants/{application_id}/status",
            json={"status": "Interview", "note": "Selected for Round 1 Technical Interview"},
            headers=admin_headers,
        )
        assert promote_res.status_code == 200
        updated = promote_res.json()
        assert updated["status"] == "Interview"
        print("  ✓ Admin promoted candidate application status to 'Interview'.")

        # 7. Student checks movement view
        movement_res = client.get("/api/tracker/applications?movement_only=true", headers=headers_eligible)
        assert movement_res.status_code == 200
        movement_apps = movement_res.json()["applications"]
        assert len(movement_apps) == 1
        assert movement_apps[0]["id"] == application_id
        assert movement_apps[0]["status"] == "Interview"
        print("  ✓ Student movement view correctly highlighted promoted application.")

        # 8. Student RBAC: Student cannot access admin endpoints
        student_post_admin = client.post("/api/admin/jobs", json=job_payload, headers=headers_eligible)
        assert student_post_admin.status_code == 403
        student_view_applicants = client.get(f"/api/admin/jobs/{job_id}/applicants", headers=headers_eligible)
        assert student_view_applicants.status_code == 403
        print("  ✓ RBAC enforced: Student cannot post admin jobs or view applicant drawer (403 Forbidden).")

    finally:
        if standalone:
            db_session.close()


if __name__ == "__main__":
    print("=" * 60)
    print(" Running Tracker & MSOT Admin Board End-to-End Verification")
    print("=" * 60)
    test_tracker_msot_full_lifecycle()
    print("\n[SUCCESS] Tracker & MSOT E2E lifecycle tests PASSED!")
