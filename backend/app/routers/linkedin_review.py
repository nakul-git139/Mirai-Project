from __future__ import annotations
import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Profile, UploadedFile, ReviewResult
from app.auth import get_current_user
from app.schemas import LinkedInReviewResponse, LinkedInReviewTextRequest, BackgroundJobResponse
from app.services.linkedin_reviewer import review_linkedin
from app.services.profile_parser import parse_resume_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reviews/linkedin", tags=["LinkedIn Reviews"])


def get_student_resume_context(user: User, profile: Profile, db: Session) -> Dict[str, Any]:
    """
    Retrieves the candidate's verified resume context for cross-referencing.
    """
    resume_context: Dict[str, Any] = {
        "experience": [],
        "projects": [],
        "skills": profile.skills or [],
        "target_roles": profile.target_roles or ["Full Stack Engineer"],
        "raw_text": profile.raw_resume_text or "",
    }

    if profile.parsed_resume:
        resume_context["experience"] = profile.parsed_resume.get("experience", [])
        resume_context["projects"] = profile.parsed_resume.get("projects", [])
        if profile.parsed_resume.get("skills"):
            existing = set(resume_context["skills"])
            resume_context["skills"] = sorted(list(existing.union(profile.parsed_resume["skills"])))
        if profile.parsed_resume.get("raw_text") and not resume_context["raw_text"]:
            resume_context["raw_text"] = profile.parsed_resume["raw_text"]
    else:
        # Check if there is an uploaded resume file
        latest_resume = (
            db.query(UploadedFile)
            .filter(UploadedFile.user_id == user.id, UploadedFile.file_type == "resume")
            .order_by(UploadedFile.created_at.desc())
            .first()
        )
        if latest_resume and os.path.exists(latest_resume.file_path):
            try:
                with open(latest_resume.file_path, "rb") as f:
                    file_bytes = f.read()
                parsed = parse_resume_file(file_bytes, latest_resume.filename)
                resume_context["experience"] = parsed.get("experience", [])
                resume_context["projects"] = parsed.get("projects", [])
                resume_context["raw_text"] = parsed.get("raw_text", "")
                if parsed.get("skills"):
                    resume_context["skills"] = parsed["skills"]
            except Exception as e:
                logger.warning(f"Could not parse resume file for LinkedIn cross-check: {e}")

    # Fallback: check profile.projects
    if not resume_context["projects"] and profile.projects:
        resume_context["projects"] = profile.projects

    return resume_context


@router.post("", response_model=LinkedInReviewResponse)
async def trigger_linkedin_review_pdf(
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Triggers a placement readiness benchmark review of the student's LinkedIn profile via PDF export.
    Enforces student consent.
    Can review an uploaded PDF export or fall back to stored profile data.
    """
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile or not profile.consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent is required before reviewing your LinkedIn profile. Please grant consent first in the Profile tab.",
        )

    file_bytes: Optional[bytes] = None
    filename: str = "linkedin_profile.pdf"
    text_content: Optional[str] = None

    if file is not None:
        filename = file.filename or "linkedin_profile.pdf"
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File upload for LinkedIn review must be a PDF export.",
            )
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded LinkedIn PDF export is empty.",
            )
    else:
        # Check if student uploaded a LinkedIn PDF earlier
        latest_li_file = (
            db.query(UploadedFile)
            .filter(UploadedFile.user_id == current_user.id, UploadedFile.file_type == "linkedin")
            .order_by(UploadedFile.created_at.desc())
            .first()
        )
        if latest_li_file and os.path.exists(latest_li_file.file_path):
            try:
                with open(latest_li_file.file_path, "rb") as f:
                    file_bytes = f.read()
                filename = latest_li_file.filename
            except Exception as e:
                logger.error(f"Error reading stored LinkedIn file: {e}")

        if not file_bytes:
            # Check if student has stored linkedin_data
            if profile.linkedin_data:
                li_data = profile.linkedin_data
                # Format into text representation
                parts = []
                if li_data.get("headline"):
                    parts.append(li_data["headline"])
                if li_data.get("about"):
                    parts.append(f"About\n{li_data['about']}")
                if li_data.get("experience"):
                    exp_strs = []
                    for exp in li_data["experience"]:
                        exp_strs.append(f"{exp.get('title', '')} at {exp.get('company', '')}")
                    parts.append("Experience\n" + "\n".join(exp_strs))
                if li_data.get("skills"):
                    parts.append("Skills\n" + ", ".join(li_data["skills"]))
                text_content = "\n\n".join(parts)

            if not text_content:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No LinkedIn profile data found. Please upload a LinkedIn PDF export or paste your profile text.",
                )

    resume_context = get_student_resume_context(current_user, profile, db)

    try:
        review_data = review_linkedin(
            file_bytes=file_bytes,
            text=text_content,
            filename=filename,
            resume_context=resume_context,
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        logger.error(f"Error during LinkedIn review: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LinkedIn review failed: {str(e)}",
        )

    # Persist review result
    review_record = ReviewResult(
        user_id=current_user.id,
        review_type="linkedin",
        score=review_data["score"],
        summary=review_data["summary"],
        checks=review_data["checks"],
        rewrites=review_data.get("rewrites", {}),
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
        logger.warning(f"Could not update readiness score after LinkedIn PDF review: {re}")

    return LinkedInReviewResponse(
        id=review_record.id,
        user_id=review_record.user_id,
        review_type=review_record.review_type,
        score=review_record.score,
        summary=review_record.summary,
        checks=review_record.checks,
        rewrites=review_record.rewrites or {},
        created_at=review_record.created_at,
    )


@router.post("/paste", response_model=LinkedInReviewResponse)
async def trigger_linkedin_review_text(
    body: LinkedInReviewTextRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Triggers a placement readiness benchmark review of the student's LinkedIn profile via pasted text.
    Enforces student consent.
    """
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile or not profile.consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent is required before reviewing your LinkedIn profile. Please grant consent first in the Profile tab.",
        )

    if not body.text or not body.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pasted profile text cannot be empty.",
        )

    resume_context = get_student_resume_context(current_user, profile, db)

    try:
        review_data = review_linkedin(
            text=body.text.strip(),
            resume_context=resume_context,
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        logger.error(f"Error during pasted LinkedIn review: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LinkedIn review failed: {str(e)}",
        )

    # Persist review record
    review_record = ReviewResult(
        user_id=current_user.id,
        review_type="linkedin",
        score=review_data["score"],
        summary=review_data["summary"],
        checks=review_data["checks"],
        rewrites=review_data.get("rewrites", {}),
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
        logger.warning(f"Could not update readiness score after LinkedIn text review: {re}")

    return LinkedInReviewResponse(
        id=review_record.id,
        user_id=review_record.user_id,
        review_type=review_record.review_type,
        score=review_record.score,
        summary=review_record.summary,
        checks=review_record.checks,
        rewrites=review_record.rewrites or {},
        created_at=review_record.created_at,
    )


@router.get("/latest", response_model=LinkedInReviewResponse)
def get_latest_linkedin_review(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves the authenticated student's most recent LinkedIn review result.
    """
    latest_review = (
        db.query(ReviewResult)
        .filter(ReviewResult.user_id == current_user.id, ReviewResult.review_type == "linkedin")
        .order_by(ReviewResult.created_at.desc())
        .first()
    )
    if not latest_review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No LinkedIn review found. Please upload a LinkedIn PDF export or paste profile text to run a review.",
        )

    return LinkedInReviewResponse(
        id=latest_review.id,
        user_id=latest_review.user_id,
        review_type=latest_review.review_type,
        score=latest_review.score,
        summary=latest_review.summary,
        checks=latest_review.checks,
        rewrites=latest_review.rewrites or {},
        created_at=latest_review.created_at,
    )


@router.post("/async", response_model=BackgroundJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_linkedin_review_async(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = None,
    provider: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Asynchronously triggers a placement readiness review of the student's LinkedIn profile as a background job.
    Enforces student consent, per-student hourly rate limits, and per-provider concurrency slots.
    """
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile or not profile.consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent is required before reviewing your LinkedIn profile. Please grant consent first in the Profile tab.",
        )

    payload: Dict[str, Any] = {"user_id": current_user.id}
    if file is not None:
        content = await file.read()
        import base64
        payload["file_b64"] = base64.b64encode(content).decode("ascii")
        payload["filename"] = file.filename or "linkedin_profile.pdf"
    elif text:
        payload["text"] = text
    if provider:
        payload["provider"] = provider

    from app.services.job_queue import job_queue_service, RateLimitExceededError
    from app.services.job_dispatchers import run_linkedin_review

    try:
        job = job_queue_service.create_job(
            user_id=current_user.id,
            task_type="linkedin_review",
            payload=payload,
            provider=provider,
            db=db,
        )
    except RateLimitExceededError as rle:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"message": rle.message, "retry_after": rle.retry_after},
            headers={"Retry-After": str(rle.retry_after)},
        )

    job_queue_service.enqueue_and_dispatch(job.id, run_linkedin_review, job.provider)
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

