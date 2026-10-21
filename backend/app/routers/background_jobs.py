from __future__ import annotations
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, BackgroundJob
from app.auth import get_current_user, require_admin
from app.schemas import (
    BackgroundJobTriggerRequest,
    BackgroundJobResponse,
    AdminQueueStatusResponse,
    CancelJobResponse,
    CancelAllJobsResponse,
)
from app.services.job_queue import job_queue_service, RateLimitExceededError
from app.services.job_dispatchers import DISPATCH_MAP

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["Background LLM Jobs"])


@router.post("/trigger", response_model=BackgroundJobResponse, status_code=status.HTTP_202_ACCEPTED)
def trigger_background_job(
    req: BackgroundJobTriggerRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Enqueue a long-running LLM task into the background execution queue.
    Enforces per-student hourly rate limits and per-provider concurrency slots.
    Returns HTTP 202 with the initial queue position.
    """
    task_type = req.task_type.strip()
    if task_type not in DISPATCH_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown task type '{task_type}'. Permitted: {list(DISPATCH_MAP.keys())}",
        )

    # Attach authenticated student context into payload
    payload = dict(req.payload or {})
    payload["user_id"] = current_user.id
    if req.provider:
        payload["provider"] = req.provider

    try:
        job = job_queue_service.create_job(
            user_id=current_user.id,
            task_type=task_type,
            payload=payload,
            provider=req.provider,
            db=db,
        )
    except RateLimitExceededError as rle:
        response.headers["Retry-After"] = str(rle.retry_after)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": rle.message,
                "retry_after": rle.retry_after,
            },
            headers={"Retry-After": str(rle.retry_after)},
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )

    # Dispatch to asynchronous worker
    task_fn = DISPATCH_MAP[task_type]
    job_queue_service.enqueue_and_dispatch(job.id, task_fn, job.provider)

    pos = job_queue_service.calculate_queue_position(job.id, job.provider, db)

    return BackgroundJobResponse(
        id=job.id,
        user_id=job.user_id,
        task_type=job.task_type,
        provider=job.provider,
        model=job.model,
        status=job.status,
        queue_position=pos,
        result=job.result,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.get("/status/{job_id}", response_model=BackgroundJobResponse)
def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Poll status of a background job (queued, running, done, failed).
    Strictly isolated: a student can only view their own jobs.
    """
    job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    if job.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You can only view status of your own jobs.",
        )

    pos = None
    if job.status == "queued":
        pos = job_queue_service.calculate_queue_position(job.id, job.provider, db)

    return BackgroundJobResponse(
        id=job.id,
        user_id=job.user_id,
        task_type=job.task_type,
        provider=job.provider,
        model=job.model,
        status=job.status,
        queue_position=pos,
        result=job.result,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.get("/my/active", response_model=List[BackgroundJobResponse])
def get_my_active_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve any queued or running jobs for the authenticated student.
    Enables instant restoration across browser reloads or tab navigation.
    """
    jobs = (
        db.query(BackgroundJob)
        .filter(
            BackgroundJob.user_id == current_user.id,
            BackgroundJob.status.in_(["queued", "running"]),
        )
        .order_by(BackgroundJob.created_at.desc())
        .all()
    )

    resp = []
    for j in jobs:
        pos = None
        if j.status == "queued":
            pos = job_queue_service.calculate_queue_position(j.id, j.provider, db)
        resp.append(
            BackgroundJobResponse(
                id=j.id,
                user_id=j.user_id,
                task_type=j.task_type,
                provider=j.provider,
                model=j.model,
                status=j.status,
                queue_position=pos,
                result=j.result,
                error_message=j.error_message,
                created_at=j.created_at,
                started_at=j.started_at,
                completed_at=j.completed_at,
            )
        )
    return resp


@router.get("/admin/queue", response_model=AdminQueueStatusResponse)
def get_admin_queue_dashboard(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Administrative overview of the LLM background processing pipeline.
    Displays queue length, running jobs, per-provider concurrency slots, and recent execution timings.
    """
    data = job_queue_service.get_admin_queue_status(db)
    return AdminQueueStatusResponse(**data)


@router.post("/{job_id}/cancel", response_model=BackgroundJobResponse)
@router.post("/cancel/{job_id}", response_model=BackgroundJobResponse)
def cancel_job_endpoint(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Cancel an active or queued background job.
    A student can cancel only their own jobs (HTTP 403 otherwise).
    Admins can cancel any job from the admin queue view.
    Immediate slot release and in-flight HTTP request abort.
    """
    try:
        job = job_queue_service.cancel_job(
            job_id=job_id,
            user_id=current_user.id,
            is_admin=(current_user.role == "admin"),
            reason=f"Cancelled by {current_user.role}",
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve),
        )
    except PermissionError as pe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe),
        )

    pos = None
    if job.status == "queued":
        pos = job_queue_service.calculate_queue_position(job.id, job.provider, db)

    return BackgroundJobResponse(
        id=job.id,
        user_id=job.user_id,
        task_type=job.task_type,
        provider=job.provider,
        status=job.status,
        queue_position=pos,
        result=job.result,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.post("/my/cancel-all", response_model=CancelAllJobsResponse)
def cancel_all_my_jobs(
    current_user: User = Depends(get_current_user),
):
    """
    Cancel all queued or running jobs for the authenticated student.
    """
    cancelled_ids = job_queue_service.cancel_all_student_jobs(user_id=current_user.id)
    return CancelAllJobsResponse(
        cancelled_count=len(cancelled_ids),
        cancelled_job_ids=cancelled_ids,
        message=f"Successfully cancelled {len(cancelled_ids)} active jobs.",
    )

