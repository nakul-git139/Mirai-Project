from __future__ import annotations
import logging
import asyncio
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional

from app.services.job_discovery.fetchers.base import BaseFetcher

logger = logging.getLogger(__name__)

DEFAULT_RSS_FEEDS = [
    {
        "name": "WeWorkRemotely",
        "url": "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "type": "rss_xml",
    },
    {
        "name": "Remotive",
        "url": "https://remotive.com/api/remote-jobs?category=software-dev&limit=25",
        "type": "remotive_json",
    },
]


class RSSFeedFetcher(BaseFetcher):
    """
    Fetches remote jobs from public RSS XML feeds (We Work Remotely) and official public feed APIs (Remotive).
    """

    source_name = "rss"

    def __init__(
        self,
        feeds: Optional[List[Dict[str, str]]] = None,
        timeout_seconds: float = 10.0,
    ):
        super().__init__(timeout_seconds=timeout_seconds)
        self.feeds = feeds or DEFAULT_RSS_FEEDS

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        tasks = [self._fetch_feed(feed) for feed in self.feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_jobs: List[Dict[str, Any]] = []
        for r in results:
            if isinstance(r, list):
                all_jobs.extend(r)
            elif isinstance(r, Exception):
                logger.warning(f"RSS feed fetch failed: {r}")

        return all_jobs

    async def _fetch_feed(self, feed: Dict[str, str]) -> List[Dict[str, Any]]:
        feed_type = feed.get("type", "rss_xml")
        feed_url = feed.get("url", "")
        feed_name = feed.get("name", "RSS")

        response = await self.get_url(feed_url)
        if not response:
            return []

        if feed_type == "remotive_json":
            return self._parse_remotive_json(response, feed_name)
        else:
            return self._parse_rss_xml(response, feed_name)

    def _parse_remotive_json(self, response, feed_name: str) -> List[Dict[str, Any]]:
        try:
            data = response.json()
            jobs_list = data.get("jobs", [])
            standardized: List[Dict[str, Any]] = []

            for item in jobs_list:
                standardized.append({
                    "id": f"remotive_{item.get('id')}",
                    "title": item.get("title", "").strip(),
                    "company": item.get("company_name", "Remote Company").strip(),
                    "location": item.get("candidate_required_location") or "Remote",
                    "url": item.get("url") or "",
                    "description": item.get("description") or "",
                    "source": "rss_remotive",
                    "source_slug": "remotive",
                    "updated_at": item.get("publication_date"),
                    "metadata": {
                        "job_type": item.get("job_type"),
                        "category": item.get("category"),
                        "tags": item.get("tags", []),
                    },
                })
            return standardized
        except Exception as e:
            logger.warning(f"Error parsing Remotive JSON feed: {e}")
            return []

    def _parse_rss_xml(self, response, feed_name: str) -> List[Dict[str, Any]]:
        try:
            root = ET.fromstring(response.content)
            channel = root.find("channel")
            if channel is None:
                channel = root

            standardized: List[Dict[str, Any]] = []
            for idx, item in enumerate(channel.findall("item")):
                title_elem = item.find("title")
                link_elem = item.find("link")
                desc_elem = item.find("description")
                pubdate_elem = item.find("pubDate")

                raw_title = title_elem.text.strip() if title_elem is not None and title_elem.text else "Untitled"
                link = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
                desc = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""
                pub_date = pubdate_elem.text.strip() if pubdate_elem is not None and pubdate_elem.text else None

                # Extract company and title if format is "Company: Title" or "Title at Company"
                company = feed_name
                job_title = raw_title
                if ":" in raw_title:
                    parts = raw_title.split(":", 1)
                    company = parts[0].strip()
                    job_title = parts[1].strip()
                elif " at " in raw_title:
                    parts = raw_title.rsplit(" at ", 1)
                    job_title = parts[0].strip()
                    company = parts[1].strip()

                standardized.append({
                    "id": f"weworkremotely_{idx}_{hash(link) % 1000000}",
                    "title": job_title,
                    "company": company,
                    "location": "Remote",
                    "url": link,
                    "description": desc,
                    "source": "rss_weworkremotely",
                    "source_slug": "weworkremotely",
                    "updated_at": pub_date,
                    "metadata": {},
                })
            return standardized
        except Exception as e:
            logger.warning(f"Error parsing RSS XML feed {feed_name}: {e}")
            return []
