from __future__ import annotations
import os
import io
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response, Header, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Profile, UploadedFile, ReviewResult
from app.auth import get_current_user
from app.schemas import ResumeReviewResponse, BackgroundJobResponse
from app.services.resume_reviewer import review_resume, render_resume_preview_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reviews", tags=["Resume Reviews"])


def get_latest_resume_file(user: User, db: Session) -> Optional[UploadedFile]:
    """Finds the most recently uploaded resume file for the user."""
    return (
        db.query(UploadedFile)
        .filter(UploadedFile.user_id == user.id, UploadedFile.file_type == "resume")
        .order_by(UploadedFile.created_at.desc())
        .first()
    )


@router.post("/resume", response_model=ResumeReviewResponse)
async def trigger_resume_review(
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Triggers a placement readiness benchmark review of the student's resume.
    Enforces student consent.
    Can review the student's currently stored resume or an uploaded file.
    """
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile or not profile.consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent is required before reviewing your resume. Please grant consent first in the Profile tab.",
        )

    file_bytes: bytes = b""
    filename: str = ""

    if file is not None:
        filename = file.filename or "resume.pdf"
        file_bytes = await file.read()
    else:
        # Fetch existing uploaded resume from user
        latest_file = get_latest_resume_file(current_user, db)
        if not latest_file or not os.path.exists(latest_file.file_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No resume found on file. Please upload a resume first.",
            )
        filename = latest_file.filename
        try:
            with open(latest_file.file_path, "rb") as f:
                file_bytes = f.read()
        except Exception as e:
            logger.error(f"Error reading resume file {latest_file.file_path}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not read stored resume file.",
            )

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The resume file is empty.",
        )

    profile_context = {
        "github_url": profile.github_url,
        "leetcode_url": profile.leetcode_url,
        "target_roles": profile.target_roles,
    }

    try:
        review_data = review_resume(
            file_bytes=file_bytes,
            filename=filename,
            profile_data=profile_context,
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        logger.error(f"Error during resume review: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Review failed: {str(e)}",
        )

    # Persist review result to database
    review_record = ReviewResult(
        user_id=current_user.id,
        review_type="resume",
        score=review_data["score"],
        summary=review_data["summary"],
        checks=review_data["checks"],
        created_at=datetime.utcnow(),
    )
    db.add(review_record)
    db.commit()
    db.refresh(review_record)

    # Automatically update placement readiness score snapshot
    try:
        from app.services.readiness_service import compute_and_save_readiness_score
        compute_and_save_readiness_score(db, current_user.id)
    except Exception as re:
        logger.warning(f"Could not update readiness score after resume review: {re}")

    return ResumeReviewResponse(
        id=review_record.id,
        user_id=review_record.user_id,
        review_type=review_record.review_type,
        score=review_record.score,
        summary=review_record.summary,
        checks=review_record.checks,
        created_at=review_record.created_at,
    )


@router.post("/resume/async", response_model=BackgroundJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_resume_review_async(
    file: Optional[UploadFile] = File(None),
    provider: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Asynchronously triggers a placement readiness review of the student's resume as a background job.
    Enforces student consent, per-student hourly rate limits, and per-provider concurrency slots.
    """
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile or not profile.consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent is required before reviewing your resume. Please grant consent first in the Profile tab.",
        )

    payload: Dict[str, Any] = {"user_id": current_user.id}
    if file is not None:
        content = await file.read()
        import base64
        payload["file_b64"] = base64.b64encode(content).decode("ascii")
        payload["filename"] = file.filename or "resume.pdf"
    if provider:
        payload["provider"] = provider

    from app.services.job_queue import job_queue_service, RateLimitExceededError
    from app.services.job_dispatchers import run_resume_review

    try:
        job = job_queue_service.create_job(
            user_id=current_user.id,
            task_type="resume_review",
            payload=payload,
            provider=provider,
            db=db,
        )
    except RateLimitExceededError as rle:
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

    job_queue_service.enqueue_and_dispatch(job.id, run_resume_review, job.provider)
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


@router.get("/resume/latest", response_model=ResumeReviewResponse)
def get_latest_resume_review(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves the authenticated student's most recent resume review result.
    """
    latest_review = (
        db.query(ReviewResult)
        .filter(ReviewResult.user_id == current_user.id, ReviewResult.review_type == "resume")
        .order_by(ReviewResult.created_at.desc())
        .first()
    )
    if not latest_review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume review found. Please upload a resume and run a review first.",
        )

    rewrites = latest_review.rewrites or {}
    return ResumeReviewResponse(
        id=latest_review.id,
        user_id=latest_review.user_id,
        review_type=latest_review.review_type,
        score=latest_review.score,
        summary=latest_review.summary,
        checks=latest_review.checks,
        reviewed_with=rewrites.get("reviewed_with"),
        code_only_checks=rewrites.get("code_only_checks", [1, 2, 3, 4, 5, 6, 7, 8]),
        created_at=latest_review.created_at,
    )


def get_user_for_preview(
    token_param: Optional[str] = None,
    current_user: Optional[User] = Depends(lambda: None),
    db: Session = Depends(get_db),
) -> User:
    # If caller has normal header, get_current_user will be resolved or we check query
    return current_user


@router.get("/resume/preview-image")
def get_resume_preview_image(
    token: Optional[str] = None,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    """
    Renders and serves a PNG image preview of page 1 of the student's latest uploaded resume.
    Supports either Authorization: Bearer header or ?token=<jwt> query parameter for browser <img> tags.
    """
    raw_token = None
    if authorization and authorization.lower().startswith("bearer "):
        raw_token = authorization.split(" ", 1)[1].strip()
    elif token:
        raw_token = token.strip()

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required to view resume preview.",
        )

    user: Optional[User] = None
    try:
        from app.auth import decode_access_token
        payload = decode_access_token(raw_token)
        user_id = payload.get("sub")
        if user_id:
            user = db.query(User).filter(User.id == int(user_id)).first()
    except Exception:
        pass

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication credentials.",
        )

    latest_file = get_latest_resume_file(user, db)
    if not latest_file or not os.path.exists(latest_file.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No uploaded resume file found to preview.",
        )

    with open(latest_file.file_path, "rb") as f:
        file_bytes = f.read()

    png_bytes = render_resume_preview_image(file_bytes, latest_file.filename)
    if not png_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Preview image generation is only supported for PDF resumes.",
        )

    return Response(content=png_bytes, media_type="image/png")

