from __future__ import annotations
from datetime import datetime, timedelta
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models import (
    User,
    UserRole,
    Job,
    Application,
    ApplicationStatus,
    Profile,
    ReadinessScore,
)
from app.auth import hash_password, create_access_token


def _create_test_student(
    db: Session,
    email: str,
    full_name: str,
    skills: list[str],
    target_roles: list[str],
    readiness_score: int,
) -> tuple[User, dict]:
    user = User(
        email=email,
        hashed_password=hash_password("studentpass123"),
        role=UserRole.STUDENT,
        full_name=full_name,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = Profile(
        user_id=user.id,
        consent_given=True,
        skills=skills,
        target_roles=target_roles,
    )
    db.add(profile)

    score = ReadinessScore(
        user_id=user.id,
        overall_score=readiness_score,
        breakdown={"resume": readiness_score, "overall": readiness_score},
    )
    db.add(score)
    db.commit()

    token = create_access_token(data={"sub": str(user.id), "role": user.role, "email": user.email})
    headers = {"Authorization": f"Bearer {token}"}
    return user, headers


# =========================================================================
# 1. End-to-End Workflow:
# Admin posts job -> Eligible sees pinned -> Ineligible does not see ->
# Student applies -> Admin sees applicant -> Status changes to Interview ->
# Movement view shows it
# =========================================================================

def test_e2e_admin_post_eligibility_apply_and_movement_flow(
    client: TestClient,
    db_session: Session,
    admin_auth_headers: dict,
):
    # 1. Admin posts an MSOT institutional opening with benchmark criteria
    job_payload = {
        "title": "Staff Campus Frontend Fellow",
        "company": "MSOT Strategic Partner Corp",
        "description": "Fellowship program for high-readiness frontend candidates.",
        "requirements": "Hands-on React & TypeScript proficiency.",
        "location": "Bangalore / Hybrid",
        "url": "https://careers.partnercorp.dev/fellowship-2026",
        "job_type": "job",
        "is_pinned": True,
        "eligibility_criteria": {
            "min_readiness_score": 75,
            "required_skills": ["React", "TypeScript"],
            "target_roles": ["Frontend Engineer"],
        },
    }
    post_res = client.post("/api/admin/jobs", json=job_payload, headers=admin_auth_headers)
    assert post_res.status_code == 201
    created_job = post_res.json()
    job_id = created_job["id"]
    assert created_job["title"] == "Staff Campus Frontend Fellow"
    assert created_job["is_pinned"] is True

    # 2. Setup Eligible Student A (Score 85, React + TypeScript, Frontend Engineer)
    student_a, headers_a = _create_test_student(
        db=db_session,
        email="student_a_eligible@mirai.dev",
        full_name="Alice Frontend",
        skills=["React", "TypeScript", "TailwindCSS"],
        target_roles=["Frontend Engineer"],
        readiness_score=85,
    )

    # 3. Setup Ineligible Student B (Score 60, Python, Backend Engineer)
    student_b, headers_b = _create_test_student(
        db=db_session,
        email="student_b_ineligible@mirai.dev",
        full_name="Bob Backend",
        skills=["Python", "Django", "PostgreSQL"],
        target_roles=["Backend Engineer"],
        readiness_score=60,
    )

    # 4. Student A discovers jobs -> MUST see the MSOT job PINNED AT THE TOP
    res_a = client.get("/api/jobs/discover?force_refresh=true", headers=headers_a)
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert len(data_a["jobs"]) > 0
    first_job = data_a["jobs"][0]
    assert first_job["title"] == "Staff Campus Frontend Fellow"
    assert first_job["is_pinned"] is True
    assert first_job["db_job_id"] == job_id

    # 5. Student B discovers jobs -> MUST NOT see the job anywhere
    res_b = client.get("/api/jobs/discover", headers=headers_b)
    assert res_b.status_code == 200
    data_b = res_b.json()
    job_titles_b = [j["title"] for j in data_b["jobs"]]
    assert "Staff Campus Frontend Fellow" not in job_titles_b

    # 6. Student A applies to the job ("Open & Apply" / Tracker API)
    apply_payload = {
        "job_id": job_id,
        "company": "MSOT Strategic Partner Corp",
        "role": "Staff Campus Frontend Fellow",
        "link": "https://careers.partnercorp.dev/fellowship-2026",
        "status": "Applied",
        "notes": "Applied via One-Click Open & Apply.",
    }
    apply_res = client.post("/api/tracker/applications", json=apply_payload, headers=headers_a)
    assert apply_res.status_code == 201
    app_data = apply_res.json()
    app_id = app_data["id"]
    assert app_data["status"] == "Applied"
    assert app_data["has_movement"] is False

    # 7. Admin views applicant list for the job -> sees Student A
    applicants_res = client.get(f"/api/admin/jobs/{job_id}/applicants", headers=admin_auth_headers)
    assert applicants_res.status_code == 200
    applicants = applicants_res.json()
    assert len(applicants) == 1
    assert applicants[0]["student_id"] == student_a.id
    assert applicants[0]["student_email"] == "student_a_eligible@mirai.dev"
    assert applicants[0]["readiness_score"] == 85
    assert applicants[0]["status"] == "Applied"

    # 8. Admin promotes Student A to "Interview"
    status_update_res = client.patch(
        f"/api/admin/jobs/{job_id}/applicants/{app_id}/status",
        json={"status": "Interview", "note": "Candidate advanced to Round 1 Technical Interview"},
        headers=admin_auth_headers,
    )
    assert status_update_res.status_code == 200
    updated_applicant = status_update_res.json()
    assert updated_applicant["status"] == "Interview"

    # 9. Student A's "Has Movement" view shows the promoted application
    movement_res = client.get("/api/tracker/applications?movement_only=true", headers=headers_a)
    assert movement_res.status_code == 200
    movement_data = movement_res.json()
    assert movement_data["movement_count"] >= 1
    assert any(a["id"] == app_id and a["status"] == "Interview" for a in movement_data["applications"])
    
    # Verify transition is recorded in status_history
    app_detail_res = client.get(f"/api/tracker/applications/{app_id}", headers=headers_a)
    assert app_detail_res.status_code == 200
    detail = app_detail_res.json()
    assert detail["has_movement"] is True
    history = detail["status_history"]
    assert len(history) >= 2
    assert history[-1]["from_status"] == "Applied"
    assert history[-1]["to_status"] == "Interview"


# =========================================================================
# 2. Permissions Test: Student cannot post jobs or view applicant lists (403)
# =========================================================================

def test_permissions_student_cannot_post_or_view_applicants(
    client: TestClient,
    student_auth_headers: dict,
):
    # Attempt to post a job as student
    post_res = client.post(
        "/api/admin/jobs",
        json={"title": "Hacker Job", "company": "Malicious Corp", "description": "test"},
        headers=student_auth_headers,
    )
    assert post_res.status_code == 403
    assert "Admin privileges required" in post_res.json()["detail"]

    # Attempt to view applicants as student
    get_applicants_res = client.get(
        "/api/admin/jobs/1/applicants",
        headers=student_auth_headers,
    )
    assert get_applicants_res.status_code == 403

    # Attempt to update applicant status as student
    patch_applicant_res = client.patch(
        "/api/admin/jobs/1/applicants/1/status",
        json={"status": "Interview"},
        headers=student_auth_headers,
    )
    assert patch_applicant_res.status_code == 403


# =========================================================================
# 3. Duplicate Application Handling (Applying twice to the same job)
# =========================================================================

def test_duplicate_application_handling(
    client: TestClient,
    db_session: Session,
    student_auth_headers: dict,
):
    # Create a job in DB
    job = Job(
        title="Software Engineer Intern",
        company="Stripe",
        description="Core infra internship.",
        is_active=True,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    # First application: succeeds (201 Created)
    payload = {
        "job_id": job.id,
        "company": "Stripe",
        "role": "Software Engineer Intern",
        "status": "Applied",
    }
    first_res = client.post("/api/tracker/applications", json=payload, headers=student_auth_headers)
    assert first_res.status_code == 201

    # Second application to the same job: MUST return 409 Conflict
    second_res = client.post("/api/tracker/applications", json=payload, headers=student_auth_headers)
    assert second_res.status_code == 409
    assert "already logged an application" in second_res.json()["detail"]


# =========================================================================
# 4. Inactivity Follow-up Reminders Test (Configurable Interval)
# =========================================================================

def test_followup_reminders_fire_after_n_days(
    client: TestClient,
    db_session: Session,
    student_user: User,
    student_auth_headers: dict,
):
    # Create an application that was last updated 10 days ago
    ten_days_ago = datetime.utcnow() - timedelta(days=10)
    stale_app = Application(
        user_id=student_user.id,
        company="Delayed Response Corp",
        role="Backend Developer",
        status=ApplicationStatus.APPLIED,
        applied_at=ten_days_ago,
        last_status_change_at=ten_days_ago,
        followup_reminder_days=7,
        status_history=[{
            "from_status": None,
            "to_status": "Applied",
            "changed_at": ten_days_ago.isoformat(),
            "note": "Initial application",
        }],
    )
    db_session.add(stale_app)
    db_session.commit()
    db_session.refresh(stale_app)

    # When query threshold is 7 days: 10 >= 7 -> REMINDER FIRES
    res_7 = client.get("/api/tracker/reminders?days=7", headers=student_auth_headers)
    assert res_7.status_code == 200
    reminders_7 = res_7.json()
    assert any(r["application_id"] == stale_app.id for r in reminders_7)
    target_rem = next(r for r in reminders_7 if r["application_id"] == stale_app.id)
    assert target_rem["days_inactive"] >= 10
    assert "recruiter follow-up" in target_rem["recommended_action"]

    # When query threshold is 14 days: 10 < 14 -> REMINDER DOES NOT FIRE
    res_14 = client.get("/api/tracker/reminders?days=14", headers=student_auth_headers)
    assert res_14.status_code == 200
    reminders_14 = res_14.json()
    assert not any(r["application_id"] == stale_app.id for r in reminders_14)


# =========================================================================
# 5. Tracker CRUD, Kanban Statuses, and Delete
# =========================================================================

def test_tracker_crud_and_status_transitions(
    client: TestClient,
    student_auth_headers: dict,
):
    # Create Saved application
    res = client.post(
        "/api/tracker/applications",
        json={"company": "Vercel", "role": "Full Stack Dev", "status": "Saved"},
        headers=student_auth_headers,
    )
    assert res.status_code == 201
    app_id = res.json()["id"]
    assert res.json()["status"] == "Saved"

    # Promote to Shortlisted
    patch_res = client.patch(
        f"/api/tracker/applications/{app_id}",
        json={"status": "Shortlisted", "notes": "Passed initial recruiter screening"},
        headers=student_auth_headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "Shortlisted"
    assert patch_res.json()["has_movement"] is True

    # Check Kanban counts
    list_res = client.get("/api/tracker/applications", headers=student_auth_headers)
    assert list_res.status_code == 200
    counts = list_res.json()["counts_by_status"]
    assert counts["Shortlisted"] >= 1
    assert "Saved" in counts
    assert "Applied" in counts
    assert "Interview" in counts
    assert "Offer" in counts
    assert "Rejected" in counts

    # Delete application
    del_res = client.delete(f"/api/tracker/applications/{app_id}", headers=student_auth_headers)
    assert del_res.status_code == 204

    # Subsequent fetch returns 404
    get_res = client.get(f"/api/tracker/applications/{app_id}", headers=student_auth_headers)
    assert get_res.status_code == 404
