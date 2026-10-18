from __future__ import annotations
import logging
import asyncio
from typing import List, Dict, Any, Optional

from app.services.job_discovery.fetchers.base import BaseFetcher

logger = logging.getLogger(__name__)

DEFAULT_LEVER_SLUGS = [
    "netflix",
    "palantir",
    "coursera",
    "atlassian",
]


class LeverFetcher(BaseFetcher):
    """
    Fetches public job postings from Lever Public Board APIs.
    Endpoint: https://api.lever.co/v0/postings/{slug}?mode=json
    """

    source_name = "lever"

    def __init__(
        self,
        company_slugs: Optional[List[str]] = None,
        timeout_seconds: float = 10.0,
    ):
        super().__init__(timeout_seconds=timeout_seconds)
        self.company_slugs = company_slugs or DEFAULT_LEVER_SLUGS

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        tasks = [self._fetch_slug_jobs(slug) for slug in self.company_slugs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_jobs: List[Dict[str, Any]] = []
        for r in results:
            if isinstance(r, list):
                all_jobs.extend(r)
            elif isinstance(r, Exception):
                logger.warning(f"Lever slug fetch failed: {r}")

        return all_jobs

    async def _fetch_slug_jobs(self, slug: str) -> List[Dict[str, Any]]:
        url = f"https://api.lever.co/v0/postings/{slug}"
        response = await self.get_url(url, params={"mode": "json"})
        if not response:
            return []

        try:
            data = response.json()
            if not isinstance(data, list):
                return []

            standardized: List[Dict[str, Any]] = []
            for item in data:
                cats = item.get("categories") or {}
                location_name = cats.get("location") if isinstance(cats, dict) else ""

                standardized.append({
                    "id": f"lever_{slug}_{item.get('id')}",
                    "title": item.get("text", "").strip(),
                    "company": slug.replace("-", " ").title(),
                    "location": location_name or "Remote / Unspecified",
                    "url": item.get("hostedUrl") or item.get("applyUrl") or "",
                    "description": item.get("descriptionPlain") or item.get("description") or "",
                    "source": "lever",
                    "source_slug": slug,
                    "updated_at": item.get("createdAt"),
                    "metadata": {
                        "commitment": cats.get("commitment") if isinstance(cats, dict) else None,
                        "team": cats.get("team") if isinstance(cats, dict) else None,
                    },
                })
            return standardized
        except Exception as e:
            logger.warning(f"Error parsing Lever response for {slug}: {e}")
            return []
