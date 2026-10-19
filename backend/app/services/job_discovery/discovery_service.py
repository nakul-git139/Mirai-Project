from __future__ import annotations
import os
import logging
import asyncio
import time
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models import Job as DBJob
from app.services.job_discovery.fetchers.greenhouse import GreenhouseFetcher, DEFAULT_GREENHOUSE_SLUGS
from app.services.job_discovery.fetchers.lever import LeverFetcher, DEFAULT_LEVER_SLUGS
from app.services.job_discovery.fetchers.rss import RSSFeedFetcher, DEFAULT_RSS_FEEDS
from app.services.job_discovery.deduplicator import deduplicate_jobs
from app.services.job_discovery.ranker import rank_jobs
from app.services.job_discovery.query_builder import build_boolean_query, build_open_search_links

logger = logging.getLogger(__name__)


def check_job_eligibility(
    job: DBJob,
    skills: List[str],
    target_roles: List[str],
    readiness_score: Optional[int],
) -> bool:
    """
    Evaluates student eligibility against job criteria:
    - min_readiness_score (e.g. 75)
    - required_skills (e.g. ['React', 'TypeScript'])
    - target_roles (e.g. ['Frontend Developer'])
    """
    crit = job.eligibility_criteria or {}
    if not crit:
        return True

    # 1. Readiness score threshold
    min_score = crit.get("min_readiness_score")
    if min_score is not None and min_score > 0:
        if readiness_score is None or readiness_score < min_score:
            return False

    # 2. Required skills check
    req_skills = crit.get("required_skills") or []
    if req_skills:
        student_skills_lower = {s.lower().strip() for s in (skills or []) if s}
        for rs in req_skills:
            if rs.lower().strip() not in student_skills_lower:
                return False

    # 3. Target roles check
    req_roles = crit.get("target_roles") or []
    if req_roles:
        student_roles_lower = [r.lower().strip() for r in (target_roles or []) if r]
        role_matched = any(
            any(rr.lower().strip() in sr or sr in rr.lower().strip() for rr in req_roles)
            for sr in student_roles_lower
        )
        if not role_matched:
            return False

    return True


class JobDiscoveryService:
    """
    Coordinates multi-source job fetching from permitted public APIs,
    internal MSOT postings, deduplication, ranking, and search links generation.
    """

    def __init__(self):
        self.greenhouse_slugs = list(DEFAULT_GREENHOUSE_SLUGS)
        self.lever_slugs = list(DEFAULT_LEVER_SLUGS)
        self.rss_feeds = list(DEFAULT_RSS_FEEDS)

        # In-memory cache for raw fetched external jobs to minimize network load
        self._cached_external_jobs: List[Dict[str, Any]] = []
        self._cache_timestamp: float = 0.0
        self._cache_ttl_seconds: float = 300.0  # 5 minutes
        self._lock = asyncio.Lock()

    def get_configured_sources(self) -> Dict[str, Any]:
        """Return currently configured sources and slugs."""
        return {
            "greenhouse": {
                "slugs": self.greenhouse_slugs,
                "endpoint_template": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
            },
            "lever": {
                "slugs": self.lever_slugs,
                "endpoint_template": "https://api.lever.co/v0/postings/{slug}?mode=json",
            },
            "rss": {
                "feeds": [f["name"] for f in self.rss_feeds],
            },
            "internal_msot": {
                "description": "Direct institutional job postings from MSOT placement staff",
            },
        }

    def update_configured_slugs(
        self,
        greenhouse_slugs: Optional[List[str]] = None,
        lever_slugs: Optional[List[str]] = None,
    ):
        """Update active company slugs for Greenhouse and Lever."""
        if greenhouse_slugs is not None:
            self.greenhouse_slugs = [s.strip().lower() for s in greenhouse_slugs if s.strip()]
        if lever_slugs is not None:
            self.lever_slugs = [s.strip().lower() for s in lever_slugs if s.strip()]
        # Invalidate cache when configuration changes
        self._cache_timestamp = 0.0

    async def fetch_external_jobs(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch and cache external jobs from Greenhouse, Lever, and RSS feeds with stampede protection."""
        now = time.time()
        if not force_refresh and self._cached_external_jobs and (now - self._cache_timestamp) < self._cache_ttl_seconds:
            logger.info("Serving external raw jobs from in-memory cache")
            return list(self._cached_external_jobs)

        if os.environ.get("OFFLINE_MODE") == "1":
            return list(self._cached_external_jobs)

        async with self._lock:
            # Double-check inside lock
            now = time.time()
            if not force_refresh and self._cached_external_jobs and (now - self._cache_timestamp) < self._cache_ttl_seconds:
                return list(self._cached_external_jobs)

            gh_fetcher = GreenhouseFetcher(company_slugs=self.greenhouse_slugs)
            lv_fetcher = LeverFetcher(company_slugs=self.lever_slugs)
            rss_fetcher = RSSFeedFetcher(feeds=self.rss_feeds)

        results = await asyncio.gather(
            gh_fetcher.fetch_jobs(),
            lv_fetcher.fetch_jobs(),
            rss_fetcher.fetch_jobs(),
            return_exceptions=True,
        )

        external_jobs: List[Dict[str, Any]] = []
        if isinstance(results[0], list):
            external_jobs.extend(results[0])
            logger.info(f"Fetched {len(results[0])} jobs from Greenhouse")
        elif isinstance(results[0], Exception):
            logger.warning(f"Greenhouse fetch encountered exception: {results[0]}")

        if isinstance(results[1], list):
            external_jobs.extend(results[1])
            logger.info(f"Fetched {len(results[1])} jobs from Lever")
        elif isinstance(results[1], Exception):
            logger.warning(f"Lever fetch encountered exception: {results[1]}")

        if isinstance(results[2], list):
            external_jobs.extend(results[2])
            logger.info(f"Fetched {len(results[2])} jobs from RSS feeds")
        elif isinstance(results[2], Exception):
            logger.warning(f"RSS fetch encountered exception: {results[2]}")

        self._cached_external_jobs = external_jobs
        self._cache_timestamp = now
        return list(external_jobs)

    async def fetch_all_raw_jobs(
        self,
        db: Optional[Session] = None,
        force_refresh: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Fetch external jobs plus any active database jobs without eligibility filtering.
        """
        all_raw_jobs = await self.fetch_external_jobs(force_refresh=force_refresh)

        if db is not None:
            try:
                db_jobs = db.query(DBJob).filter(DBJob.is_active == True).all()
                for dj in db_jobs:
                    all_raw_jobs.append({
                        "id": f"msot_direct_{dj.id}",
                        "title": dj.title,
                        "company": dj.company,
                        "location": dj.location or "On Campus / Hybrid",
                        "url": dj.url or f"/jobs/{dj.id}",
                        "description": f"{dj.description}\n\nRequirements:\n{dj.requirements or ''}",
                        "source": "msot_direct",
                        "source_slug": "msot",
                        "updated_at": dj.created_at.isoformat() if dj.created_at else None,
                        "is_pinned": dj.is_pinned,
                        "db_job_id": dj.id,
                        "metadata": {
                            "posted_by": dj.posted_by,
                            "is_direct": True,
                            "is_pinned": dj.is_pinned,
                            "db_job_id": dj.id,
                            "job_type": dj.job_type,
                            "eligibility_criteria": dj.eligibility_criteria or {},
                        },
                    })
                logger.info(f"Ingested {len(db_jobs)} MSOT institutional jobs from database")
            except Exception as e:
                logger.warning(f"Could not load MSOT database jobs: {e}")

        return all_raw_jobs

    async def discover_jobs(
        self,
        skills: List[str],
        target_roles: List[str],
        readiness_score: Optional[int] = None,
        locations: Optional[List[str]] = None,
        job_types: Optional[List[str]] = None,
        db: Optional[Session] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute full discovery workflow:
        1. Query & Open Search links generation
        2. Ingestion: external boards + eligible MSOT direct postings
        3. Deduplication
        4. Ranking & Pinning eligible MSOT postings to top
        """
        # 1. Generate Boolean search query and open search links
        boolean_query = build_boolean_query(
            skills=skills,
            job_types=job_types,
            locations=locations,
            target_roles=target_roles,
        )
        primary_role = target_roles[0] if target_roles else None
        open_search_links = build_open_search_links(
            query=boolean_query,
            location=locations[0] if locations else "India",
            primary_role=primary_role,
        )

        # 2. Ingest external jobs
        raw_jobs = await self.fetch_external_jobs(force_refresh=force_refresh)

        # Ingest eligible MSOT internal direct postings from database
        if db is not None:
            try:
                db_jobs = db.query(DBJob).filter(DBJob.is_active == True).all()
                for dj in db_jobs:
                    # Enforce eligibility gate: only eligible students see the job
                    if check_job_eligibility(
                        job=dj,
                        skills=skills,
                        target_roles=target_roles,
                        readiness_score=readiness_score,
                    ):
                        raw_jobs.append({
                            "id": f"msot_direct_{dj.id}",
                            "title": dj.title,
                            "company": dj.company,
                            "location": dj.location or "On Campus / Hybrid",
                            "url": dj.url or f"/jobs/{dj.id}",
                            "description": f"{dj.description}\n\nRequirements:\n{dj.requirements or ''}",
                            "source": "msot_direct",
                            "source_slug": "msot",
                            "updated_at": dj.created_at.isoformat() if dj.created_at else None,
                            "is_pinned": dj.is_pinned,
                            "db_job_id": dj.id,
                            "metadata": {
                                "posted_by": dj.posted_by,
                                "is_direct": True,
                                "is_pinned": dj.is_pinned,
                                "db_job_id": dj.id,
                                "job_type": dj.job_type,
                                "eligibility_criteria": dj.eligibility_criteria or {},
                            },
                        })
                logger.info(f"Ingested eligible MSOT institutional jobs from database")
            except Exception as e:
                logger.warning(f"Could not load MSOT database jobs: {e}")

        # 3. Deduplicate
        unique_jobs = deduplicate_jobs(raw_jobs)

        # 4. Rank and generate match reasons
        ranked_jobs = rank_jobs(
            jobs=unique_jobs,
            skills=skills,
            target_roles=target_roles,
            readiness_score=readiness_score,
            preferred_locations=locations,
        )

        # 5. Pin eligible MSOT institutional jobs to the top
        for j in ranked_jobs:
            if j.get("source") == "msot_direct" or "msot_direct" in j.get("sources", []):
                j["is_pinned"] = True
                # Extract db_job_id
                meta = j.get("metadata") or {}
                if "db_job_id" in meta:
                    j["db_job_id"] = meta["db_job_id"]
                elif str(j.get("id", "")).startswith("msot_direct_"):
                    try:
                        j["db_job_id"] = int(str(j["id"]).replace("msot_direct_", ""))
                    except Exception:
                        pass

        # Sort: pinned jobs FIRST (1), then descending by match_score
        ranked_jobs.sort(
            key=lambda j: (1 if j.get("is_pinned") else 0, j.get("match_score", 0)),
            reverse=True,
        )

        # Collect source breakdown
        source_counts: Dict[str, int] = {}
        for j in ranked_jobs:
            for s in j.get("sources", [j.get("source")]):
                if s:
                    source_counts[s] = source_counts.get(s, 0) + 1

        return {
            "total_raw": len(raw_jobs),
            "total_unique": len(unique_jobs),
            "source_counts": source_counts,
            "boolean_query": boolean_query,
            "open_search_links": open_search_links,
            "jobs": ranked_jobs,
        }



# Global singleton service
job_discovery_service = JobDiscoveryService()
