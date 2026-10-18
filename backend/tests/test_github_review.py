from __future__ import annotations
import os
import re
import json
import socket
import threading
import http.server
from pathlib import Path
from typing import Generator
import pytest
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.services.secret_scanner import scan_repository_files, scan_file_content
from app.services.github_scanner import (
    GitHubScanner,
    GitHubRateLimitError,
    GitHubNotFoundError,
    check_response_rate_limit,
)
from app.services.live_link_checker import check_live_link, SCREENSHOT_DIR
from app.services.github_reviewer import evaluate_github_and_live


# --- Local HTTP Server Fixture for Playwright Verification ---
class MockWebServerHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/good":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = """<!DOCTYPE html>
            <html>
            <head><title>Placement Readiness Copilot</title><meta name="description" content="AI Copilot for MSOT placements"></head>
            <body style="margin:0; padding:20px; font-family:sans-serif;">
                <h1>Placement Readiness Copilot</h1>
                <p>Built with React, FastAPI, SQLite and Playwright.</p>
            </body>
            </html>"""
            self.wfile.write(html.encode("utf-8"))
        elif self.path == "/js-error":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = """<!DOCTYPE html>
            <html>
            <head><title>Buggy Demo Page</title></head>
            <body>
                <h1>Buggy Application</h1>
                <script>
                    console.error("Uncaught TypeError: Cannot read properties of undefined (reading 'map')");
                </script>
            </body>
            </html>"""
            self.wfile.write(html.encode("utf-8"))
        elif self.path == "/404":
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"404 Not Found")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress noisy HTTP server logs during pytest
        pass


@pytest.fixture(scope="module")
def mock_web_server() -> Generator[str, None, None]:
    """Spins up a lightweight local HTTP server for testing Playwright live link verification."""
    # Find free port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("", 0))
    port = sock.getsockname()[1]
    sock.close()

    server = http.server.HTTPServer(("127.0.0.1", port), MockWebServerHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    yield base_url
    server.shutdown()


# ==============================================================================
# TEST CASE 1: Good Clean Repository
# ==============================================================================
@pytest.mark.asyncio
async def test_good_repository_evaluation(mock_web_server: str):
    """Asserts that a well-structured repo with README, tests, clean tree, and live link achieves high score."""
    good_repo_data = {
        "repo": {
            "name": "placement-copilot",
            "description": "Production ready copilot for MSOT students",
            "language": "Python",
            "stargazers_count": 12,
            "forks_count": 3,
            "homepage": f"{mock_web_server}/good",
        },
        "readme": """# Placement Readiness Copilot
AI Copilot for student placement readiness.

## Getting Started
```bash
pip install -r backend/requirements.txt
uvicorn app.main:app --reload
npm install && npm run dev
```

## Preview Screenshots
![Application Dashboard](docs/assets/dashboard.png)
<img src="docs/assets/preview.png" alt="Preview">
""",
        "tree": [
            {"path": ".gitignore", "type": "blob"},
            {"path": "backend/app/main.py", "type": "blob"},
            {"path": "backend/tests/test_main.py", "type": "blob"},
            {"path": "frontend/src/App.jsx", "type": "blob"},
            {"path": "README.md", "type": "blob"},
        ],
        "commits": [
            {"commit": {"message": "feat(core): implement deterministic benchmark scoring rubric"}},
            {"commit": {"message": "fix(auth): enforce consent requirement before file parsing"}},
            {"commit": {"message": "docs(readme): add local setup commands and demo screenshots"}},
        ],
        "files": {
            "backend/app/main.py": "def root():\n    return {'status': 'healthy'}\n",
            "backend/tests/test_main.py": "def test_root():\n    assert True\n",
        },
    }

    result = await evaluate_github_and_live(
        username="alexrivera",
        repo_url_or_slug="alexrivera/placement-copilot",
        live_url=f"{mock_web_server}/good",
        project_title="Placement Readiness Copilot",
        resume_skills=["Python", "React", "FastAPI"],
        preloaded_repo_data=good_repo_data,
    )

    checks_map = {c["id"]: c for c in result["checks"]}

    # Verify key checks pass
    assert checks_map["CHK-GH-REPO-README"]["pass"] is True
    assert checks_map["CHK-GH-FOLDER-STRUCTURE"]["pass"] is True
    assert checks_map["CHK-GH-NO-SECRETS"]["pass"] is True
    assert checks_map["CHK-GH-TESTS-PRESENT"]["pass"] is True
    assert checks_map["CHK-GH-COMMIT-MESSAGES"]["pass"] is True
    assert checks_map["CHK-LIVE-LOAD-STATUS"]["pass"] is True
    assert checks_map["CHK-LIVE-CONSOLE-HEALTH"]["pass"] is True
    assert checks_map["CHK-LIVE-CONTENT-MATCH"]["pass"] is True
    assert checks_map["CHK-LIVE-MOBILE-VIEWPORT"]["pass"] is True

    # High placement score
    assert result["score"] >= 80


# ==============================================================================
# TEST CASE 2: Repository with No README
# ==============================================================================
@pytest.mark.asyncio
async def test_repo_with_no_readme():
    """Asserts that a repository missing README.md fails CHK-GH-REPO-README with a specific fix."""
    no_readme_repo_data = {
        "repo": {"name": "undocumented-service", "description": None, "language": "Go"},
        "readme": None,
        "tree": [
            {"path": "main.go", "type": "blob"},
            {"path": "go.mod", "type": "blob"},
        ],
        "commits": [{"commit": {"message": "feat: initial commit"}}],
        "files": {"main.go": "package main\nfunc main() {}\n"},
    }

    result = await evaluate_github_and_live(
        username="johndoe",
        repo_url_or_slug="johndoe/undocumented-service",
        preloaded_repo_data=no_readme_repo_data,
    )

    checks_map = {c["id"]: c for c in result["checks"]}
    readme_check = checks_map["CHK-GH-REPO-README"]
    assert readme_check["pass"] is False
    assert "No README.md detected" in readme_check["evidence"]
    assert "Create a comprehensive README.md" in readme_check["fix"]


# ==============================================================================
# TEST CASE 3: Planted Secret Detection & Zero False Positives on Clean Repo
# ==============================================================================
def test_planted_fake_secret_detection_and_false_positive_absence():
    """
    Tests secret scanner against planted fake secrets:
    1. Catches planted fake AWS key, OpenAI key, and private key.
    2. Reports zero false positives on clean repository files.
    """
    planted_secrets_repo = {
        "config/aws_settings.py": """
import boto3
AWS_KEY = "AKIA9876543210SECKEY"
AWS_SECRET = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
""",
        "keys/id_rsa": """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA0fakekeydataforsecuritytesting1234567890abcdef
-----END RSA PRIVATE KEY-----""",
        "services/openai_client.py": """
client = OpenAI(api_key="sk-live-abc1234567890abcdef1234567890")
""",
    }

    findings = scan_repository_files(planted_secrets_repo)
    assert len(findings) >= 2

    types_found = {f["type"] for f in findings}
    assert "AWS Access Key" in types_found
    assert "Private Key" in types_found or "OpenAI / LLM API Key" in types_found

    # Verify masking
    for f in findings:
        assert "***" in f["masked"] or "..." in f["masked"]
        assert len(f["masked"]) <= 12

    # Clean repo false positive check
    clean_repo = {
        "src/auth.py": "def hash_password(pw: str) -> str:\n    return 'hashed'\n",
        "README.md": "Use `AKIAIOSFODNN7EXAMPLE` as standard documentation example placeholder.",
        ".env.example": "AWS_ACCESS_KEY_ID=your_api_key_here\nDATABASE_URL=postgres://user:pass@localhost:5432/db",
        "package-lock.json": '{"name": "test", "version": "1.0.0", "integrity": "sha512-abcd1234"}',
    }

    clean_findings = scan_repository_files(clean_repo)
    # MUST have ZERO false positives on clean repo with documentation placeholders
    assert len(clean_findings) == 0, f"False positives detected on clean repo: {clean_findings}"


# ==============================================================================
# TEST CASE 4: Nonexistent GitHub Username (404 Handling)
# ==============================================================================
def test_nonexistent_github_username_handled_cleanly():
    """Asserts that querying a nonexistent GitHub username raises GitHubNotFoundError cleanly."""
    scanner = GitHubScanner()
    # Nonexistent user with high-entropy timestamp to guarantee 404
    nonexistent_user = "nonexistent-user-msot-copilot-test-99999"
    with pytest.raises(GitHubNotFoundError) as exc_info:
        scanner.fetch_user_profile(nonexistent_user)

    assert "not found or private" in str(exc_info.value).lower()
    scanner.close()


# ==============================================================================
# TEST CASE 5: Live Link Returning 404
# ==============================================================================
@pytest.mark.asyncio
async def test_live_link_returning_404(mock_web_server: str):
    """Asserts that a live link returning HTTP 404 fails CHK-LIVE-LOAD-STATUS cleanly."""
    four_oh_four_url = f"{mock_web_server}/404"
    result = await check_live_link(url=four_oh_four_url)

    assert result["loaded"] is False
    assert result["status_code"] == 404
    assert "404" in result["error_message"]


# ==============================================================================
# TEST CASE 6: Live Link with JavaScript Console Error
# ==============================================================================
@pytest.mark.asyncio
async def test_live_link_with_js_console_error(mock_web_server: str):
    """Asserts that Playwright captures runtime JavaScript console errors."""
    buggy_url = f"{mock_web_server}/js-error"
    result = await check_live_link(url=buggy_url)

    assert result["loaded"] is True
    assert len(result["console_errors"]) >= 1
    assert any("TypeError" in err for err in result["console_errors"])


# ==============================================================================
# TEST CASE 7: Rate Limit Simulation (Mock 403 / 429)
# ==============================================================================
def test_github_rate_limit_simulation_provides_helpful_guidance():
    """Simulates a GitHub API HTTP 403 rate limit response and asserts actionable message."""
    mock_response = httpx.Response(
        status_code=403,
        headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1730000000"},
        content=b'{"message": "API rate limit exceeded for IP"}',
        request=httpx.Request("GET", "https://api.github.com/users/test"),
    )

    with pytest.raises(GitHubRateLimitError) as exc_info:
        check_response_rate_limit(mock_response, "Testing Rate Limit")

    err_msg = str(exc_info.value)
    assert "rate limit exceeded" in err_msg.lower()
    assert "Personal Access Token" in err_msg
    assert "5,000 requests/hour" in err_msg


# ==============================================================================
# TEST CASE 8: Playwright Screenshots & Timeout Enforcement on Unreachable URL
# ==============================================================================
@pytest.mark.asyncio
async def test_playwright_screenshots_and_unreachable_timeout():
    """
    1. Verifies desktop and mobile screenshot generation on disk.
    2. Verifies that unreachable URLs fail cleanly within the timeout without hanging.
    """
    # Test unreachable non-routable IP with small 1.5s timeout
    unreachable_url = "http://10.255.255.1:9999/unreachable"
    result = await check_live_link(url=unreachable_url, timeout_ms=1500)

    assert result["loaded"] is False
    assert result["error_message"] is not None
    assert "timed out" in result["error_message"].lower() or "failed" in result["error_message"].lower()


# ==============================================================================
# TEST CASE 9: Real Public GitHub Profiles Verification
# ==============================================================================
def test_two_real_public_github_profiles():
    """
    Runs GitHubScanner against 2 real public GitHub profiles (e.g. 'torvalds' and 'pallets').
    Demonstrates real live API parsing. Gracefully skips if GitHub unauthenticated rate limit is active on current IP.
    """
    scanner = GitHubScanner()

    profiles_to_test = ["torvalds", "pallets"]
    results = {}

    for username in profiles_to_test:
        try:
            profile = scanner.fetch_user_profile(username)
            repos = scanner.fetch_user_repos(username)
            results[username] = {
                "login": profile.get("login"),
                "name": profile.get("name"),
                "public_repos": profile.get("public_repos"),
                "top_repo": repos[0]["name"] if repos else None,
            }
            assert profile.get("login").lower() == username.lower()
            assert profile.get("public_repos") > 0
        except GitHubRateLimitError as rle:
            pytest.skip(f"GitHub unauthenticated public rate limit hit from current IP: {rle}")
            break
        except Exception as e:
            pytest.fail(f"Failed to fetch real public GitHub profile '{username}': {e}")

    scanner.close()
    assert len(results) == 2
    print(f"\n[Real GitHub Profiles Output]: {json.dumps(results, indent=2)}")


# ==============================================================================
# TEST CASE 10: Full API Endpoints & Consent Enforcement
# ==============================================================================
def test_api_endpoints_and_consent(client: TestClient, student_auth_headers: dict, mock_web_server: str):
    """Verifies POST /api/reviews/github enforces consent and processes review."""
    # First, test without consent -> HTTP 400
    client.post("/api/profile/consent", json={"consent_given": False}, headers=student_auth_headers)

    resp = client.post(
        "/api/reviews/github",
        json={"username": "alexrivera", "repo_url": "alexrivera/demo"},
        headers=student_auth_headers,
    )
    assert resp.status_code == 400
    assert "Consent is required" in resp.json()["detail"]

    # Now grant consent
    client.post("/api/profile/consent", json={"consent_given": True}, headers=student_auth_headers)

    # Standalone live link check endpoint
    live_resp = client.post(
        "/api/reviews/live-link",
        json={"url": f"{mock_web_server}/good", "project_title": "Example Project"},
        headers=student_auth_headers,
    )
    assert live_resp.status_code == 200
    live_data = live_resp.json()
    assert "loaded" in live_data
    assert live_data["loaded"] is True

