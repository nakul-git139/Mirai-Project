from __future__ import annotations
import logging
import time
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Profile, ReadinessScore
from app.auth import get_current_user_optional, require_admin
from app.schemas import (
    JobDiscoveryResponse,
    BooleanQueryRequest,
    BooleanQueryResponse,
    SourcesConfigRequest,
    OpenSearchLinks,
)
from app.services.job_discovery import (
    job_discovery_service,
    build_boolean_query,
    build_open_search_links,
)
from app.services.job_discovery.fetchers.greenhouse import GreenhouseFetcher
from app.services.job_discovery.fetchers.lever import LeverFetcher
from app.services.job_discovery.fetchers.rss import RSSFeedFetcher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["Job Discovery"])


@router.get("/discover", response_model=JobDiscoveryResponse)
async def discover_jobs(
    skills: Optional[str] = Query(None, description="Comma-separated skills override"),
    target_role: Optional[str] = Query(None, description="Target role override"),
    location: Optional[str] = Query(None, description="Preferred location"),
    min_score: int = Query(0, ge=0, le=100, description="Minimum match score filter"),
    force_refresh: bool = Query(False, description="Bypass cache and refetch from live sources"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    Discovers jobs from permitted public sources (Greenhouse, Lever, RSS feeds, MSOT internal).
    Computes boolean search query, open search links, deduplicates postings,
    and ranks jobs against the student's profile and readiness score.
    """
    profile_skills: List[str] = []
    target_roles: List[str] = []
    readiness_score: Optional[int] = None
    pref_locations: List[str] = ["remote", "bangalore"]

    # If student is logged in, extract profile context
    if current_user:
        profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
        if profile:
            if profile.skills:
                profile_skills.extend(profile.skills)
            if profile.parsed_resume and isinstance(profile.parsed_resume, dict):
                resume_skills = profile.parsed_resume.get("skills", [])
                for sk in resume_skills:
                    if sk and sk not in profile_skills:
                        profile_skills.append(sk)
            if profile.target_roles:
                target_roles.extend(profile.target_roles)

        # Get latest readiness score
        latest_score = (
            db.query(ReadinessScore)
            .filter(ReadinessScore.user_id == current_user.id)
            .order_by(ReadinessScore.created_at.desc())
            .first()
        )
        if latest_score:
            readiness_score = latest_score.overall_score

    # Apply query parameter overrides
    if skills:
        override_skills = [s.strip() for s in skills.split(",") if s.strip()]
        if override_skills:
            profile_skills = override_skills

    if target_role:
        target_roles = [target_role.strip()]

    if location:
        pref_locations = [location.strip(), "remote"]

    # Provide defaults if profile is sparse
    if not profile_skills:
        profile_skills = ["React", "JavaScript", "Python", "SQL"]
    if not target_roles:
        target_roles = ["Software Engineer", "Frontend Developer"]

    # Execute discovery workflow
    result = await job_discovery_service.discover_jobs(
        skills=profile_skills,
        target_roles=target_roles,
        readiness_score=readiness_score,
        locations=pref_locations,
        db=db,
        force_refresh=force_refresh,
    )

    # Filter by minimum match score if specified
    if min_score > 0:
        result["jobs"] = [j for j in result["jobs"] if j.get("match_score", 0) >= min_score]

    return result


@router.post("/query", response_model=BooleanQueryResponse)
def generate_query(req: BooleanQueryRequest):
    """
    Generates exact Boolean search queries and outbound open search deep links
    for LinkedIn, Naukri, Internshala, and Google Jobs.
    """
    boolean_query = build_boolean_query(
        skills=req.skills,
        job_types=req.job_types,
        locations=req.locations,
        target_roles=req.target_roles,
    )
    primary_role = req.target_roles[0] if req.target_roles else None
    open_search_links = build_open_search_links(
        query=boolean_query,
        location=req.locations[0] if req.locations else "India",
        primary_role=primary_role,
    )
    return {
        "boolean_query": boolean_query,
        "open_search_links": open_search_links,
    }


@router.get("/sources")
def get_sources():
    """Return list of permitted ingestion sources and configured company slugs."""
    return job_discovery_service.get_configured_sources()


@router.post("/sources")
def update_sources(
    req: SourcesConfigRequest,
    admin_user: User = Depends(require_admin),
):
    """Update active company slugs for Greenhouse and Lever (Admin only)."""
    job_discovery_service.update_configured_slugs(
        greenhouse_slugs=req.greenhouse_slugs,
        lever_slugs=req.lever_slugs,
    )
    return {
        "status": "updated",
        "configured": job_discovery_service.get_configured_sources(),
    }


@router.post("/sources/test")
async def test_source(
    source: str = Query(..., description="Source name: greenhouse, lever, or rss"),
    slug: Optional[str] = Query(None, description="Company slug (for greenhouse/lever)"),
):
    """
    Test live fetching from an authorized source with latency tracking and fault boundary.
    """
    start_time = time.time()
    source_lower = source.lower().strip()

    try:
        if source_lower == "greenhouse":
            target_slug = slug or "cloudflare"
            fetcher = GreenhouseFetcher(company_slugs=[target_slug], timeout_seconds=10.0)
            jobs = await fetcher.fetch_jobs()
        elif source_lower == "lever":
            target_slug = slug or "netflix"
            fetcher = LeverFetcher(company_slugs=[target_slug], timeout_seconds=10.0)
            jobs = await fetcher.fetch_jobs()
        elif source_lower == "rss":
            fetcher = RSSFeedFetcher(timeout_seconds=10.0)
            jobs = await fetcher.fetch_jobs()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown source '{source}'. Permitted: greenhouse, lever, rss",
            )

        latency_ms = int((time.time() - start_time) * 1000)
        return {
            "source": source_lower,
            "slug": slug,
            "status": "success",
            "count": len(jobs),
            "latency_ms": latency_ms,
            "sample_jobs": [
                {"title": j["title"], "company": j["company"], "location": j["location"]}
                for j in jobs[:3]
            ],
        }
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        return {
            "source": source_lower,
            "slug": slug,
            "status": "error",
            "error": str(e),
            "latency_ms": latency_ms,
            "count": 0,
        }
