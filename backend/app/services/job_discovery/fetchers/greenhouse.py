from __future__ import annotations
import logging
import asyncio
from typing import List, Dict, Any, Optional

from app.services.job_discovery.fetchers.base import BaseFetcher

logger = logging.getLogger(__name__)

DEFAULT_GREENHOUSE_SLUGS = [
    "cloudflare",
    "gitlab",
    "stripe",
    "figma",
    "automattic",
]


class GreenhouseFetcher(BaseFetcher):
    """
    Fetches public job postings from Greenhouse Public Board APIs.
    Endpoint: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true
    """

    source_name = "greenhouse"

    def __init__(
        self,
        company_slugs: Optional[List[str]] = None,
        timeout_seconds: float = 10.0,
    ):
        super().__init__(timeout_seconds=timeout_seconds)
        self.company_slugs = company_slugs or DEFAULT_GREENHOUSE_SLUGS

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        tasks = [self._fetch_slug_jobs(slug) for slug in self.company_slugs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_jobs: List[Dict[str, Any]] = []
        for r in results:
            if isinstance(r, list):
                all_jobs.extend(r)
            elif isinstance(r, Exception):
                logger.warning(f"Greenhouse slug fetch failed: {r}")

        return all_jobs

    async def _fetch_slug_jobs(self, slug: str) -> List[Dict[str, Any]]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
        response = await self.get_url(url, params={"content": "true"})
        if not response:
            return []

        try:
            data = response.json()
            jobs_list = data.get("jobs", [])
            standardized: List[Dict[str, Any]] = []

            for item in jobs_list:
                loc_obj = item.get("location") or {}
                location_name = loc_obj.get("name") if isinstance(loc_obj, dict) else str(loc_obj)

                standardized.append({
                    "id": f"greenhouse_{slug}_{item.get('id')}",
                    "title": item.get("title", "").strip(),
                    "company": slug.replace("-", " ").title(),
                    "location": location_name or "Remote / Unspecified",
                    "url": item.get("absolute_url") or "",
                    "description": item.get("content") or "",
                    "source": "greenhouse",
                    "source_slug": slug,
                    "updated_at": item.get("updated_at"),
                    "metadata": {
                        "departments": [d.get("name") for d in item.get("departments", []) if isinstance(d, dict)],
                        "offices": [o.get("name") for o in item.get("offices", []) if isinstance(o, dict)],
                    },
                })
            return standardized
        except Exception as e:
            logger.warning(f"Error parsing Greenhouse response for {slug}: {e}")
            return []
