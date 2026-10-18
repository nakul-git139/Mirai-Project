from __future__ import annotations
import os
import base64
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
import httpx

from app.services.settings_service import load_raw_settings

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


class GitHubAPIError(Exception):
    """Base exception for GitHub API errors."""
    pass


class GitHubRateLimitError(GitHubAPIError):
    """Raised when GitHub REST API rate limit is exceeded."""
    pass


class GitHubNotFoundError(GitHubAPIError):
    """Raised when user or repository is 404 Not Found or private."""
    pass


def get_github_auth_headers() -> Dict[str, str]:
    """
    Builds standard headers for GitHub REST API calls.
    Includes Authorization header if GITHUB_TOKEN is set in settings or environment.
    """
    settings = load_raw_settings()
    token = settings.get("github_token") or os.environ.get("GITHUB_TOKEN", "").strip()

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "PlacementReadinessCopilot/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def check_response_rate_limit(resp: httpx.Response, context_msg: str = ""):
    """Checks for rate limit status (HTTP 403/429) and raises informative error."""
    remaining = resp.headers.get("x-ratelimit-remaining")
    if resp.status_code in (403, 429):
        resp_text = resp.text.lower()
        if remaining == "0" or "rate limit" in resp_text:
            reset_epoch = resp.headers.get("x-ratelimit-reset")
            reset_hint = ""
            if reset_epoch:
                try:
                    reset_dt = datetime.fromtimestamp(int(reset_epoch), tz=timezone.utc)
                    reset_hint = f" Quota resets at {reset_dt.strftime('%H:%M:%S UTC')}."
                except Exception:
                    pass
            raise GitHubRateLimitError(
                f"GitHub API rate limit exceeded.{reset_hint} "
                "Provide an optional GitHub Personal Access Token in Settings to increase your quota to 5,000 requests/hour."
            )
        elif "abuse" in resp_text or "secondary" in resp_text:
            raise GitHubRateLimitError(
                "GitHub secondary rate limit triggered. Please wait a few moments before trying again."
            )

    if resp.status_code == 404:
        raise GitHubNotFoundError(f"Requested GitHub resource not found or private: {context_msg}")


def parse_github_repo_url(url_or_slug: str) -> Tuple[str, str]:
    """
    Extracts (owner, repo) from GitHub URL or slug.
    Examples:
      - 'https://github.com/torvalds/linux' -> ('torvalds', 'linux')
      - 'torvalds/linux' -> ('torvalds', 'linux')
    """
    clean = url_or_slug.strip().rstrip("/")
    if clean.startswith("https://github.com/"):
        clean = clean[len("https://github.com/"):]
    elif clean.startswith("http://github.com/"):
        clean = clean[len("http://github.com/"):]

    parts = [p for p in clean.split("/") if p]
    if len(parts) >= 2:
        return parts[0], parts[1].replace(".git", "")
    elif len(parts) == 1:
        return parts[0], parts[0]
    raise ValueError(f"Invalid GitHub repository identifier: '{url_or_slug}'. Expected 'owner/repo' or GitHub URL.")


class GitHubScanner:
    """Service client for fetching public GitHub metadata."""

    def __init__(self, client: Optional[httpx.Client] = None):
        self.headers = get_github_auth_headers()
        self._client = client or httpx.Client(timeout=15.0)

    def fetch_user_profile(self, username: str) -> Dict[str, Any]:
        """Fetches public user profile metadata."""
        url = f"{GITHUB_API_BASE}/users/{username}"
        resp = self._client.get(url, headers=self.headers)
        check_response_rate_limit(resp, f"User '{username}'")
        if resp.status_code != 200:
            raise GitHubAPIError(f"GitHub returned HTTP {resp.status_code} for user '{username}': {resp.text}")
        return resp.json()

    def fetch_profile_readme(self, username: str) -> Optional[str]:
        """Fetches user's special profile README (<username>/<username>/README.md)."""
        url = f"{GITHUB_API_BASE}/repos/{username}/{username}/readme"
        resp = self._client.get(url, headers=self.headers)
        if resp.status_code == 404:
            return None
        check_response_rate_limit(resp, f"Profile README for '{username}'")
        if resp.status_code == 200:
            data = resp.json()
            content_b64 = data.get("content", "")
            try:
                return base64.b64decode(content_b64).decode("utf-8", errors="replace")
            except Exception:
                return None
        return None

    def fetch_user_events_momentum(self, username: str) -> Dict[str, Any]:
        """
        Fetches user public events to assess commit momentum.
        Returns total push events and push events within last 90 days.
        """
        url = f"{GITHUB_API_BASE}/users/{username}/events/public?per_page=100"
        resp = self._client.get(url, headers=self.headers)
        if resp.status_code == 404:
            return {"push_events_90d": 0, "total_events": 0, "has_recent_activity": False}
        check_response_rate_limit(resp, f"Events for '{username}'")
        if resp.status_code != 200:
            return {"push_events_90d": 0, "total_events": 0, "has_recent_activity": False}

        events = resp.json()
        now = datetime.now(timezone.utc)
        cutoff_90d = now - timedelta(days=90)

        push_count_90d = 0
        for ev in events:
            if ev.get("type") == "PushEvent":
                created_at_str = ev.get("created_at")
                if created_at_str:
                    try:
                        ev_dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                        if ev_dt >= cutoff_90d:
                            push_count_90d += 1
                    except Exception:
                        push_count_90d += 1

        return {
            "push_events_90d": push_count_90d,
            "total_events": len(events),
            "has_recent_activity": push_count_90d >= 3,
        }

    def fetch_user_repos(self, username: str) -> List[Dict[str, Any]]:
        """Fetches top public repositories sorted by updated date."""
        url = f"{GITHUB_API_BASE}/users/{username}/repos?sort=updated&per_page=20"
        resp = self._client.get(url, headers=self.headers)
        check_response_rate_limit(resp, f"Repositories for '{username}'")
        if resp.status_code != 200:
            return []
        return resp.json()

    def fetch_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetches repository details."""
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
        resp = self._client.get(url, headers=self.headers)
        check_response_rate_limit(resp, f"Repository '{owner}/{repo}'")
        if resp.status_code != 200:
            raise GitHubAPIError(f"Failed to fetch repository '{owner}/{repo}': HTTP {resp.status_code}")
        return resp.json()

    def fetch_repo_readme(self, owner: str, repo: str) -> Optional[str]:
        """Fetches repository README.md content."""
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/readme"
        resp = self._client.get(url, headers=self.headers)
        if resp.status_code == 404:
            return None
        check_response_rate_limit(resp, f"README for '{owner}/{repo}'")
        if resp.status_code == 200:
            data = resp.json()
            content_b64 = data.get("content", "")
            try:
                return base64.b64decode(content_b64).decode("utf-8", errors="replace")
            except Exception:
                return None
        return None

    def fetch_repo_tree(self, owner: str, repo: str, default_branch: str = "main") -> List[Dict[str, Any]]:
        """Fetches recursive git tree of files."""
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
        resp = self._client.get(url, headers=self.headers)
        if resp.status_code == 404 and default_branch == "main":
            # Retry with master branch
            url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/master?recursive=1"
            resp = self._client.get(url, headers=self.headers)
        check_response_rate_limit(resp, f"Git tree for '{owner}/{repo}'")
        if resp.status_code == 200:
            return resp.json().get("tree", [])
        return []

    def fetch_repo_commits(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Fetches recent commits."""
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits?per_page=15"
        resp = self._client.get(url, headers=self.headers)
        if resp.status_code == 404:
            return []
        check_response_rate_limit(resp, f"Commits for '{owner}/{repo}'")
        if resp.status_code == 200:
            return resp.json()
        return []

    def fetch_file_content(self, owner: str, repo: str, branch: str, path: str) -> Optional[str]:
        """Fetches raw text content of a file."""
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
        resp = self._client.get(url, headers=self.headers)
        if resp.status_code == 200:
            return resp.text
        return None

    def close(self):
        self._client.close()
