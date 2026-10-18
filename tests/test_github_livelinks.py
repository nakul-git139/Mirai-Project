#!/usr/bin/env python3
"""
GitHub Audit & Playwright Live-Link Verification Script:
Validates repository quality benchmarks, secret detection, and live link accessibility.
Can be run directly (`python tests/test_github_livelinks.py`) or via pytest (`pytest tests/test_github_livelinks.py`).
"""
import os
import sys
import socket
import threading
import http.server
from pathlib import Path
import pytest

# Ensure backend root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.services.secret_scanner import scan_repository_files, scan_file_content
from app.services.live_link_checker import check_live_link, SCREENSHOT_DIR


class MockWebServerHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/good":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = """<!DOCTYPE html>
            <html>
            <head><title>Placement Readiness Copilot</title></head>
            <body>
                <h1>Placement Copilot Demo</h1>
                <p>Live project deployment for MSOT students.</p>
            </body>
            </html>"""
            self.wfile.write(html.encode("utf-8"))
        elif self.path == "/js-error":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = """<!DOCTYPE html>
            <html>
            <head><title>Buggy Demo</title></head>
            <body>
                <h1>Buggy Page</h1>
                <script>console.error("Uncaught TypeError: Cannot read property 'map' of undefined");</script>
            </body>
            </html>"""
            self.wfile.write(html.encode("utf-8"))
        elif self.path == "/404":
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not Found")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Quiet down server logs during testing


@pytest.fixture(scope="module")
def local_web_server():
    server = http.server.HTTPServer(("127.0.0.1", 0), MockWebServerHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


def test_secret_scanner_detection_and_no_false_positives():
    print("\n[GitHub] Testing Secret Scanner...")
    # Planted fake secrets (AKIA + 16 alphanumeric characters without 'example')
    bad_files = {
        "src/config.py": "AWS_ACCESS_KEY_ID = 'AKIA9876543210SECKEY'\nAWS_SECRET_ACCESS_KEY = 'secret'",
        "keys/id_rsa": "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0fakekeydataforsecuritytesting1234567890abcdef\n-----END RSA PRIVATE KEY-----",
    }
    findings = scan_repository_files(bad_files)
    assert len(findings) >= 2, f"Expected >=2 secret findings, got {len(findings)}"
    types = {f["type"] for f in findings}
    assert "AWS Access Key" in types
    assert "Private Key" in types
    print("  ✓ Planted AWS Key and Private Key detected successfully.")

    # Clean files with .env.example and documentation
    clean_files = {
        ".env.example": "DATABASE_URL=sqlite:///./copilot.db\nOPENAI_API_KEY=your_key_here",
        "README.md": "Use `AKIAIOSFODNN7EXAMPLE` as standard documentation example placeholder.",
        "package-lock.json": '{"version": "1.0.0", "integrity": "sha512-abc..."}',
    }
    clean_findings = scan_repository_files(clean_files)
    assert len(clean_findings) == 0, f"Expected 0 findings in clean files, got: {clean_findings}"
    print("  ✓ Zero false positives on clean files & documentation.")


@pytest.mark.asyncio
async def test_live_link_playwright_checks(local_web_server):
    print(f"\n[Live Link] Testing Playwright Live Checker against {local_web_server}...")

    # 1. Healthy page: 200 OK, zero console errors, screenshots captured
    res_good = await check_live_link(f"{local_web_server}/good", project_title="Placement Copilot")
    assert res_good["status_code"] == 200
    assert len(res_good["console_errors"]) == 0
    assert res_good["desktop_screenshot"] is not None
    assert (SCREENSHOT_DIR / res_good["desktop_screenshot"]).exists()
    assert res_good["mobile_screenshot"] is not None
    assert (SCREENSHOT_DIR / res_good["mobile_screenshot"]).exists()
    print("  ✓ Healthy 200 OK page passed with 0 console errors and dual screenshots.")

    # 2. Buggy page with JavaScript console errors
    res_buggy = await check_live_link(f"{local_web_server}/js-error")
    assert res_buggy["status_code"] == 200
    assert len(res_buggy["console_errors"]) >= 1
    assert any("TypeError" in err for err in res_buggy["console_errors"])
    print("  ✓ Planted console error caught cleanly by Playwright error listener.")

    # 3. 404 page
    res_404 = await check_live_link(f"{local_web_server}/404")
    assert res_404["status_code"] == 404
    print("  ✓ Broken 404 link detected cleanly.")


if __name__ == "__main__":
    import asyncio
    print("=" * 60)
    print(" Running GitHub Codebase & Live Link Verification")
    print("=" * 60)
    test_secret_scanner_detection_and_no_false_positives()

    server = http.server.HTTPServer(("127.0.0.1", 0), MockWebServerHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    try:
        asyncio.run(test_live_link_playwright_checks(base_url))
        print("\n[SUCCESS] GitHub & Live Link verification PASSED!")
    finally:
        server.shutdown()
