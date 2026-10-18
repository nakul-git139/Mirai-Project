from __future__ import annotations
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Profile
from app.auth import get_current_user
from app.schemas import ReadinessResponse, ReadinessHistoryItem
from app.services.readiness_service import (
    compute_and_save_readiness_score,
    get_current_readiness_score,
    get_readiness_history,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/readiness", tags=["Readiness Score"])


@router.get("/current", response_model=ReadinessResponse)
def get_readiness_score(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the student's current placement readiness score (0-100),
    component breakdown (7 dimensions), missing components, and top 5 actions.
    Enforces privacy consent.
    """
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile or not profile.consent_given:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Consent required to calculate placement readiness score. Please give consent in Profile & My Data.",
        )

    return get_current_readiness_score(db, current_user.id)


@router.post("/recalculate", response_model=ReadinessResponse)
def recalculate_readiness_score(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Forces recalculation of the student's placement readiness score
    across all 7 components and persists a new snapshot point to history.
    """
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile or not profile.consent_given:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Consent required to calculate placement readiness score. Please give consent in Profile & My Data.",
        )

    return compute_and_save_readiness_score(db, current_user.id)


@router.get("/history", response_model=List[ReadinessHistoryItem])
def get_score_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns chronological score history snapshots for rendering
    the score-history progression chart.
    """
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile or not profile.consent_given:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Consent required to view score history. Please give consent in Profile & My Data.",
        )

    return get_readiness_history(db, current_user.id)
