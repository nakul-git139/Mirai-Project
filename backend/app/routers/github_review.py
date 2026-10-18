from __future__ import annotations
import os
import re
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Profile, ReviewResult
from app.auth import get_current_user
from app.schemas import (
    GitHubReviewRequest,
    GitHubReviewResponse,
    LiveLinkCheckRequest,
)
from app.services.github_reviewer import evaluate_github_and_live
from app.services.live_link_checker import check_live_link, SCREENSHOT_DIR
from app.services.github_scanner import GitHubRateLimitError, GitHubNotFoundError, GitHubAPIError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reviews", tags=["GitHub & Live Link Reviews"])


@router.post("/github", response_model=GitHubReviewResponse)
async def trigger_github_review(
    req: Optional[GitHubReviewRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Triggers a placement readiness benchmark review of the student's GitHub profile,
    codebase repository, and live deployment link.
    Enforces student consent.
    """
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile or not profile.consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent is required before reviewing your GitHub and codebase. Please grant consent first in the Profile tab.",
        )

    # Resolve inputs: request body > profile fields > projects
    username = (req.username.strip() if req and req.username else None) or profile.github_username
    if not username and profile.github_url:
        match = re.search(r"github\.com/([a-zA-Z0-9_\-]+)", profile.github_url)
        if match:
            username = match.group(1)

    repo_url = req.repo_url.strip() if req and req.repo_url else None
    live_url = req.live_url.strip() if req and req.live_url else None
    project_title = req.project_title if req else None

    # Fallback to stored projects if not passed in request
    if (not repo_url or not live_url) and profile.projects:
        for p in profile.projects:
            if isinstance(p, dict):
                if not repo_url and p.get("repo_url"):
                    repo_url = p.get("repo_url")
                if not live_url and p.get("live_url"):
                    live_url = p.get("live_url")
                if not project_title and p.get("title"):
                    project_title = p.get("title")

    if not username and not repo_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub username or repository URL is required. Please provide it in the request or update your Profile.",
        )

    try:
        review_data = await evaluate_github_and_live(
            username=username,
            repo_url_or_slug=repo_url,
            live_url=live_url,
            project_title=project_title,
            resume_skills=profile.skills or [],
        )
    except GitHubRateLimitError as rle:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(rle),
        )
    except GitHubNotFoundError as nfe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(nfe),
        )
    except GitHubAPIError as gae:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub API error: {str(gae)}",
        )
    except Exception as e:
        logger.error(f"GitHub review failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Review evaluation failed: {str(e)}",
        )

    # Persist review result in SQLite
    review_row = ReviewResult(
        user_id=current_user.id,
        review_type="github",
        score=review_data["score"],
        summary=review_data["summary"],
        checks=review_data["checks"],
        rewrites={
            "repo_details": review_data.get("repo_details", {}),
            "live_link_results": review_data.get("live_link_results"),
            "screenshots": review_data.get("screenshots", {}),
        },
    )
    db.add(review_row)
    db.commit()
    db.refresh(review_row)

    # Automatically update placement readiness score snapshot
    try:
        from app.services.readiness_service import compute_and_save_readiness_score
        compute_and_save_readiness_score(db, current_user.id)
    except Exception as re:
        logger.warning(f"Could not update readiness score after GitHub review: {re}")

    return GitHubReviewResponse(
        id=review_row.id,
        user_id=review_row.user_id,
        review_type="github",
        score=review_row.score,
        summary=review_row.summary,
        checks=review_row.checks,
        repo_details=review_data.get("repo_details", {}),
        live_link_results=review_data.get("live_link_results"),
        screenshots=review_data.get("screenshots", {}),
        created_at=review_row.created_at,
    )


@router.get("/github/latest", response_model=GitHubReviewResponse)
def get_latest_github_review(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves the student's most recent GitHub & codebase benchmark review."""
    latest = (
        db.query(ReviewResult)
        .filter(
            ReviewResult.user_id == current_user.id,
            ReviewResult.review_type == "github",
        )
        .order_by(ReviewResult.created_at.desc())
        .first()
    )
    if not latest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No GitHub review has been performed yet.",
        )

    rewrites = latest.rewrites or {}
    return GitHubReviewResponse(
        id=latest.id,
        user_id=latest.user_id,
        review_type="github",
        score=latest.score,
        summary=latest.summary,
        checks=latest.checks,
        repo_details=rewrites.get("repo_details", {}),
        live_link_results=rewrites.get("live_link_results"),
        screenshots=rewrites.get("screenshots", {}),
        created_at=latest.created_at,
    )


@router.post("/live-link")
async def trigger_live_link_check(
    req: LiveLinkCheckRequest,
    current_user: User = Depends(get_current_user),
):
    """Direct live deployment link verification with headless Playwright."""
    result = await check_live_link(
        url=req.url,
        project_title=req.project_title,
        expected_keywords=req.expected_keywords,
    )
    return result


@router.get("/screenshots/{filename}")
def get_screenshot(filename: str):
    """Secure static image server for desktop and mobile preview screenshots."""
    # Sanitize filename
    if not re.match(r"^[a-zA-Z0-9_\-]+\.png$", filename):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename format.")

    file_path = SCREENSHOT_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Screenshot not found.")

    return FileResponse(str(file_path), media_type="image/png")
