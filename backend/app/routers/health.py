from __future__ import annotations
from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
@router.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "app": "Placement Readiness Copilot",
        "service": "backend",
    }
