from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import httpx

from app.services.job_discovery.robots_checker import robots_checker

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "PlacementReadinessCopilot/1.0 (MSOT Career Platform; student-prep)",
    "Accept": "application/json, application/xml, text/xml, */*",
}


class BaseFetcher(ABC):
    """Abstract base class for all authorized job fetchers."""

    source_name: str = "generic"

    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout_seconds = timeout_seconds

    @abstractmethod
    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """Fetch and return a list of standardized job dictionaries."""
        pass

    async def get_url(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[httpx.Response]:
        """
        Safely fetch an HTTP endpoint while enforcing:
        1. Zero-scraping blocklist (disallows LinkedIn, Naukri, etc.)
        2. Robots.txt compliance check
        3. Rate limit throttling
        4. Strict timeout boundaries
        """
        # Validate domain permissions and robots.txt
        if not robots_checker.check_allowed(url):
            logger.warning(f"Robots.txt forbids fetching {url} for user-agent")
            return None

        # Respect host rate limits
        robots_checker.wait_for_rate_limit(url)

        req_headers = DEFAULT_HEADERS.copy()
        if headers:
            req_headers.update(headers)

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
                response = await client.get(url, params=params, headers=req_headers)
                if response.status_code == 200:
                    return response
                else:
                    logger.warning(
                        f"Fetcher [{self.source_name}] received HTTP {response.status_code} from {url}"
                    )
                    return None
        except httpx.TimeoutException:
            logger.warning(f"Fetcher [{self.source_name}] timed out fetching {url} after {self.timeout_seconds}s")
            return None
        except Exception as e:
            logger.warning(f"Fetcher [{self.source_name}] error fetching {url}: {e}")
            return None
