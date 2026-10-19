from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    User,
    Job,
    Application,
    ApplicationStatus,
    Profile,
    ReadinessScore,
    UserRole,
)
from app.schemas import (
    JobCreate,
    JobResponse,
    UserResponse,
    ApplicantItem,
    ApplicantStatusUpdate,
    AdminQueueStatusResponse,
)
from app.auth import require_admin

router = APIRouter(prefix="/api/admin", tags=["Admin"])


def _to_job_response(job: Job) -> JobResponse:
    app_count = len(job.applications) if job.applications is not None else 0
    return JobResponse(
        id=job.id,
        title=job.title,
        company=job.company,
        description=job.description,
        requirements=job.requirements,
        location=job.location,
        url=job.url,
        job_type=job.job_type or "job",
        eligibility_criteria=job.eligibility_criteria or {},
        is_pinned=job.is_pinned if job.is_pinned is not None else True,
        deadline=job.deadline,
        is_active=job.is_active,
        posted_by=job.posted_by,
        applicant_count=app_count,
        created_at=job.created_at,
    )


@router.get("/jobs", response_model=List[JobResponse])
def list_admin_jobs(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only endpoint to list all job postings with applicant counts."""
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()
    return [_to_job_response(j) for j in jobs]


@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_admin_job(
    job_in: JobCreate,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only endpoint to post a job directly for students with eligibility criteria."""
    job = Job(
        title=job_in.title,
        company=job_in.company,
        description=job_in.description,
        requirements=job_in.requirements,
        location=job_in.location,
        url=job_in.url,
        job_type=job_in.job_type or "job",
        eligibility_criteria=job_in.eligibility_criteria or {},
        is_pinned=job_in.is_pinned if job_in.is_pinned is not None else True,
        deadline=job_in.deadline,
        is_active=True,
        posted_by=current_admin.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _to_job_response(job)


@router.put("/jobs/{job_id}", response_model=JobResponse)
def update_admin_job(
    job_id: int,
    job_in: JobCreate,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only endpoint to update an existing job posting."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    job.title = job_in.title
    job.company = job_in.company
    job.description = job_in.description
    job.requirements = job_in.requirements
    job.location = job_in.location
    job.url = job_in.url
    if job_in.job_type is not None:
        job.job_type = job_in.job_type
    if job_in.eligibility_criteria is not None:
        job.eligibility_criteria = job_in.eligibility_criteria
    if job_in.is_pinned is not None:
        job.is_pinned = job_in.is_pinned
    if job_in.deadline is not None:
        job.deadline = job_in.deadline

    db.commit()
    db.refresh(job)
    return _to_job_response(job)


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_job(
    job_id: int,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only endpoint to remove a job posting."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    db.delete(job)
    db.commit()
    return None


@router.get("/jobs/{job_id}/applicants", response_model=List[ApplicantItem])
def list_job_applicants(
    job_id: int,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only endpoint to view student applicants for a specific job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    apps = (
        db.query(Application)
        .filter(Application.job_id == job_id)
        .order_by(Application.created_at.desc())
        .all()
    )

    results: List[ApplicantItem] = []
    for a in apps:
        student = a.user
        profile = student.profile if student else None
        latest_score = (
            db.query(ReadinessScore)
            .filter(ReadinessScore.user_id == student.id)
            .order_by(ReadinessScore.created_at.desc())
            .first()
            if student
            else None
        )

        results.append(
            ApplicantItem(
                application_id=a.id,
                student_id=student.id if student else 0,
                student_name=student.full_name
                or (student.email.split("@")[0] if student else "Student"),
                student_email=student.email if student else "",
                readiness_score=latest_score.overall_score if latest_score else None,
                target_roles=profile.target_roles if profile and profile.target_roles else [],
                skills=profile.skills if profile and profile.skills else [],
                status=a.status,
                applied_at=a.applied_at or a.created_at,
                last_status_change_at=a.last_status_change_at or a.created_at,
                notes=a.notes,
                status_history=a.status_history or [],
            )
        )
    return results


@router.patch("/jobs/{job_id}/applicants/{application_id}/status", response_model=ApplicantItem)
def update_applicant_status(
    job_id: int,
    application_id: int,
    status_in: ApplicantStatusUpdate,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Admin promotes or updates an applicant's status (e.g. to Interview, Shortlisted, Offer).
    Records the status transition and updates movement timestamp.
    """
    app = (
        db.query(Application)
        .filter(Application.id == application_id, Application.job_id == job_id)
        .first()
    )
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found for this job",
        )

    norm_status = ApplicationStatus.normalize(status_in.status)
    old_status = app.status
    now = datetime.utcnow()
    app.status = norm_status
    app.last_status_change_at = now

    history = list(app.status_history or [])
    history.append({
        "from_status": old_status,
        "to_status": norm_status,
        "changed_at": now.isoformat(),
        "note": status_in.note or f"Applicant moved from {old_status} to {norm_status} by MSOT Admin",
    })
    app.status_history = history
    db.commit()
    db.refresh(app)

    student = app.user
    profile = student.profile if student else None
    latest_score = (
        db.query(ReadinessScore)
        .filter(ReadinessScore.user_id == student.id)
        .order_by(ReadinessScore.created_at.desc())
        .first()
        if student
        else None
    )

    return ApplicantItem(
        application_id=app.id,
        student_id=student.id if student else 0,
        student_name=student.full_name
        or (student.email.split("@")[0] if student else "Student"),
        student_email=student.email if student else "",
        readiness_score=latest_score.overall_score if latest_score else None,
        target_roles=profile.target_roles if profile and profile.target_roles else [],
        skills=profile.skills if profile and profile.skills else [],
        status=app.status,
        applied_at=app.applied_at or app.created_at,
        last_status_change_at=app.last_status_change_at or app.created_at,
        notes=app.notes,
        status_history=app.status_history or [],
    )


@router.get("/students", response_model=List[UserResponse])
def list_students(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only endpoint to inspect student accounts."""
    students = db.query(User).filter(User.role == UserRole.STUDENT).all()
    return students


@router.get("/llm-queue", response_model=AdminQueueStatusResponse)
def get_admin_llm_queue(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only endpoint for queue length, running jobs, limits, and timings."""
    from app.services.job_queue import job_queue_service
    data = job_queue_service.get_admin_queue_status(db)
    return AdminQueueStatusResponse(**data)
