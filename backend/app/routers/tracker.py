from __future__ import annotations
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Job, Application, ApplicationStatus
from app.auth import get_current_user
from app.schemas import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationResponse,
    ApplicationListResponse,
    FollowupReminderItem,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tracker", tags=["Application Tracker"])


def _to_application_response(
    app: Application, reminder_days_override: Optional[int] = None
) -> ApplicationResponse:
    now = datetime.utcnow()
    last_change = app.last_status_change_at or app.created_at or now
    days_since_update = max(0, (now - last_change).days)

    threshold = (
        reminder_days_override
        if reminder_days_override is not None
        else (app.followup_reminder_days or 7)
    )

    # Has movement: any progression beyond Saved/Applied (Shortlisted, Interview, Offer, Rejected)
    # or multiple recorded status transitions
    has_movement = (
        app.status in [
            ApplicationStatus.SHORTLISTED,
            ApplicationStatus.INTERVIEW,
            ApplicationStatus.OFFER,
            ApplicationStatus.REJECTED,
        ]
        or len(app.status_history or []) > 1
    )

    # Reminders trigger for active applications awaiting external response
    is_reminder_due = (
        app.status in [
            ApplicationStatus.APPLIED,
            ApplicationStatus.SHORTLISTED,
            ApplicationStatus.INTERVIEW,
        ]
        and days_since_update >= threshold
    )

    return ApplicationResponse(
        id=app.id,
        user_id=app.user_id,
        job_id=app.job_id,
        company=app.company or (app.job.company if app.job else "Unknown Company"),
        role=app.role or (app.job.title if app.job else "Unknown Role"),
        link=app.link or (app.job.url if app.job else None),
        status=app.status,
        notes=app.notes,
        applied_at=app.applied_at,
        last_status_change_at=last_change,
        status_history=app.status_history or [],
        followup_reminder_days=app.followup_reminder_days or 7,
        has_movement=has_movement,
        is_reminder_due=is_reminder_due,
        days_since_update=days_since_update,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


@router.get("/applications", response_model=ApplicationListResponse)
def list_applications(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    movement_only: bool = Query(False, description="Filter for applications with recent movement"),
    reminders_only: bool = Query(False, description="Filter for applications requiring follow-up"),
    reminder_days: Optional[int] = Query(None, description="Configurable inactive days threshold"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List applications for the authenticated student.
    Supports status filters, Kanban counts, 'has movement' view, and follow-up reminders.
    """
    apps = (
        db.query(Application)
        .filter(Application.user_id == current_user.id)
        .order_by(Application.last_status_change_at.desc())
        .all()
    )

    counts = {s: 0 for s in ApplicationStatus.ALL}
    all_responses: List[ApplicationResponse] = []
    movement_count = 0
    reminders_count = 0

    for a in apps:
        resp = _to_application_response(a, reminder_days_override=reminder_days)
        if resp.status in counts:
            counts[resp.status] += 1
        if resp.has_movement:
            movement_count += 1
        if resp.is_reminder_due:
            reminders_count += 1
        all_responses.append(resp)

    # Apply filters
    filtered = all_responses
    if status_filter:
        norm_filter = ApplicationStatus.normalize(status_filter)
        filtered = [r for r in filtered if r.status == norm_filter]

    if movement_only:
        filtered = [r for r in filtered if r.has_movement]

    if reminders_only:
        filtered = [r for r in filtered if r.is_reminder_due]

    return ApplicationListResponse(
        applications=filtered,
        counts_by_status=counts,
        total_count=len(all_responses),
        movement_count=movement_count,
        reminders_count=reminders_count,
    )


@router.post("/applications", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(
    app_in: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Log an application (from One-click 'Open & Apply' or manual entry).
    Strictly prevents duplicate applications for the same job (HTTP 409 Conflict).
    """
    # 1. Check duplicate by job_id
    if app_in.job_id is not None:
        existing = (
            db.query(Application)
            .filter(
                Application.user_id == current_user.id,
                Application.job_id == app_in.job_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"You have already logged an application for this job (Current status: '{existing.status}').",
            )

    # 2. Check duplicate by company & role (case-insensitive)
    cleaned_company = app_in.company.strip()
    cleaned_role = app_in.role.strip()
    existing_by_name = (
        db.query(Application)
        .filter(
            Application.user_id == current_user.id,
            Application.company.ilike(cleaned_company),
            Application.role.ilike(cleaned_role),
        )
        .first()
    )
    if existing_by_name and app_in.job_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"You already have an application tracked for '{cleaned_role}' at '{cleaned_company}' (Status: '{existing_by_name.status}').",
        )

    norm_status = ApplicationStatus.normalize(app_in.status or ApplicationStatus.APPLIED)
    now = datetime.utcnow()
    applied_at = app_in.applied_at or (now if norm_status != ApplicationStatus.SAVED else None)

    # Populate job metadata if job_id was provided
    company_name = cleaned_company
    role_title = cleaned_role
    link_url = app_in.link
    if app_in.job_id:
        target_job = db.query(Job).filter(Job.id == app_in.job_id).first()
        if target_job:
            company_name = target_job.company or company_name
            role_title = target_job.title or role_title
            link_url = target_job.url or link_url

    history_entry = {
        "from_status": None,
        "to_status": norm_status,
        "changed_at": now.isoformat(),
        "note": app_in.notes or f"Application logged as {norm_status}",
    }

    new_app = Application(
        user_id=current_user.id,
        job_id=app_in.job_id,
        company=company_name,
        role=role_title,
        link=link_url,
        status=norm_status,
        notes=app_in.notes,
        applied_at=applied_at,
        last_status_change_at=now,
        status_history=[history_entry],
        followup_reminder_days=app_in.followup_reminder_days or 7,
    )
    db.add(new_app)
    db.commit()
    db.refresh(new_app)

    return _to_application_response(new_app)


@router.get("/applications/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve full application details including status history."""
    app = (
        db.query(Application)
        .filter(Application.id == application_id, Application.user_id == current_user.id)
        .first()
    )
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return _to_application_response(app)


@router.patch("/applications/{application_id}", response_model=ApplicationResponse)
def update_application(
    application_id: int,
    app_in: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update application status, notes, or reminder days.
    Transitions append an entry to `status_history` and update `last_status_change_at`.
    """
    app = (
        db.query(Application)
        .filter(Application.id == application_id, Application.user_id == current_user.id)
        .first()
    )
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    now = datetime.utcnow()
    changed = False

    if app_in.status is not None:
        norm_status = ApplicationStatus.normalize(app_in.status)
        if norm_status != app.status:
            old_status = app.status
            app.status = norm_status
            app.last_status_change_at = now
            if norm_status != ApplicationStatus.SAVED and not app.applied_at:
                app.applied_at = now

            history = list(app.status_history or [])
            history.append({
                "from_status": old_status,
                "to_status": norm_status,
                "changed_at": now.isoformat(),
                "note": app_in.notes or f"Moved from {old_status} to {norm_status}",
            })
            app.status_history = history
            changed = True

    if app_in.notes is not None:
        app.notes = app_in.notes
        changed = True

    if app_in.company is not None:
        app.company = app_in.company.strip()
        changed = True

    if app_in.role is not None:
        app.role = app_in.role.strip()
        changed = True

    if app_in.link is not None:
        app.link = app_in.link.strip()
        changed = True

    if app_in.followup_reminder_days is not None:
        app.followup_reminder_days = app_in.followup_reminder_days
        changed = True

    if app_in.applied_at is not None:
        app.applied_at = app_in.applied_at
        changed = True

    if changed:
        db.commit()
        db.refresh(app)

    return _to_application_response(app)


@router.delete("/applications/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove an application from the tracker."""
    app = (
        db.query(Application)
        .filter(Application.id == application_id, Application.user_id == current_user.id)
        .first()
    )
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    db.delete(app)
    db.commit()
    return None


@router.get("/reminders", response_model=List[FollowupReminderItem])
def get_followup_reminders(
    days: Optional[int] = Query(None, description="Configurable inactive days threshold"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns active applications that have had no movement or status update for >= N days.
    """
    apps = (
        db.query(Application)
        .filter(Application.user_id == current_user.id)
        .order_by(Application.last_status_change_at.asc())
        .all()
    )

    now = datetime.utcnow()
    reminders: List[FollowupReminderItem] = []

    for a in apps:
        threshold = days if days is not None else (a.followup_reminder_days or 7)
        last_change = a.last_status_change_at or a.created_at or now
        days_inactive = max(0, (now - last_change).days)

        if a.status in [ApplicationStatus.APPLIED, ApplicationStatus.SHORTLISTED, ApplicationStatus.INTERVIEW]:
            if days_inactive >= threshold:
                action = (
                    "Send a polite recruiter follow-up email inquiring on application review status."
                    if a.status == ApplicationStatus.APPLIED
                    else "Check recruiter portal and prepare STAR responses for upcoming interview rounds."
                )
                reminders.append(
                    FollowupReminderItem(
                        application_id=a.id,
                        company=a.company or (a.job.company if a.job else "Unknown Company"),
                        role=a.role or (a.job.title if a.job else "Unknown Role"),
                        status=a.status,
                        applied_at=a.applied_at,
                        last_status_change_at=last_change,
                        days_inactive=days_inactive,
                        recommended_action=action,
                    )
                )

    return reminders
