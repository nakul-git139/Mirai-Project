from __future__ import annotations
import time
import logging
from urllib.parse import urlparse
import urllib.robotparser
from typing import Dict, Optional

logger = logging.getLogger(__name__)

DISALLOWED_DOMAINS = [
    "linkedin.com",
    "naukri.com",
    "internshala.com",
    "indeed.com",
    "glassdoor.com",
]


class DisallowedDomainError(Exception):
    """Raised when an attempt is made to fetch or scrape a disallowed domain."""
    pass


class RobotsChecker:
    """
    Validates robots.txt rules and enforces domain rate-limiting and zero-scraping policies.
    """

    def __init__(self, user_agent: str = "PlacementReadinessCopilot/1.0"):
        self.user_agent = user_agent
        self._parsers: Dict[str, urllib.robotparser.RobotFileParser] = {}
        self._last_request_times: Dict[str, float] = {}
        self._crawl_delays: Dict[str, float] = {}

    def is_disallowed_domain(self, url: str) -> bool:
        """Check if URL belongs to a strictly forbidden site (e.g. LinkedIn, Naukri)."""
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        for domain in DISALLOWED_DOMAINS:
            if domain in hostname:
                return True
        return False

    def check_allowed(self, url: str) -> bool:
        """
        Verify that fetching this URL is permitted by both project policy and robots.txt.
        Raises DisallowedDomainError if the domain is on the blocklist.
        """
        if self.is_disallowed_domain(url):
            raise DisallowedDomainError(
                f"Scraping '{url}' is strictly forbidden by project privacy and ethics policy. "
                "Use open search links instead."
            )

        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False

        host = parsed.netloc.lower()
        parser = self._get_or_load_parser(parsed.scheme, host)
        if parser is None:
            # If robots.txt cannot be fetched or parsed, default to permissive for permitted APIs
            return True

        return parser.can_fetch(self.user_agent, url)

    def wait_for_rate_limit(self, url: str, default_min_delay: float = 0.5):
        """Enforces rate limiting based on host crawl-delay or default minimum delay."""
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        if not host:
            return

        now = time.time()
        last_time = self._last_request_times.get(host, 0.0)
        delay = max(self._crawl_delays.get(host, 0.0), default_min_delay)

        elapsed = now - last_time
        if elapsed < delay:
            sleep_duration = delay - elapsed
            time.sleep(sleep_duration)

        self._last_request_times[host] = time.time()

    def _get_or_load_parser(self, scheme: str, host: str) -> Optional[urllib.robotparser.RobotFileParser]:
        if host in self._parsers:
            return self._parsers[host]

        robots_url = f"{scheme}://{host}/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        try:
            import httpx
            headers = {"User-Agent": self.user_agent}
            resp = httpx.get(robots_url, headers=headers, timeout=5.0, follow_redirects=True)
            if resp.status_code == 200:
                rp.parse(resp.text.splitlines())
                self._parsers[host] = rp
                crawl_delay = rp.crawl_delay(self.user_agent)
                if crawl_delay:
                    self._crawl_delays[host] = float(crawl_delay)
                return rp
            elif resp.status_code in (404, 410):
                # No robots.txt means all permitted
                self._parsers[host] = None
                return None
            else:
                self._parsers[host] = None
                return None
        except Exception as e:
            logger.debug(f"Could not load robots.txt for {robots_url}: {e}")
            self._parsers[host] = None
            return None


# Global singleton instance for application use
robots_checker = RobotsChecker()
