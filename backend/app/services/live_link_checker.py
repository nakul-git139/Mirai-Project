from __future__ import annotations
import os
import uuid
import logging
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError

logger = logging.getLogger(__name__)

SCREENSHOT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_TIMEOUT_MS = 15000  # Strict 15-second maximum page load timeout


async def check_live_link(
    url: str,
    project_title: Optional[str] = None,
    expected_keywords: Optional[List[str]] = None,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> Dict[str, Any]:
    """
    Evaluates a live deployment link using headless Playwright:
    1. Loads page with strict timeout, records HTTP status and navigation duration.
    2. Collects runtime JS console errors and uncaught exceptions.
    3. Captures desktop screenshot (1280x720).
    4. Evaluates in mobile viewport (375x667) and captures mobile screenshot.
    5. Extracts visible text and evaluates content match against project claims.
    """
    result: Dict[str, Any] = {
        "url": url,
        "loaded": False,
        "status_code": None,
        "load_time_ms": 0,
        "console_errors": [],
        "network_errors": [],
        "title": "",
        "meta_description": "",
        "desktop_screenshot": None,
        "mobile_screenshot": None,
        "mobile_overflow": False,
        "content_match": False,
        "content_overlap_ratio": 0.0,
        "extracted_snippet": "",
        "error_message": None,
    }

    if not url or not (url.startswith("http://") or url.startswith("https://") or url.startswith("file://")):
        result["error_message"] = "Invalid URL: Must start with http://, https://, or file://"
        return result

    run_id = uuid.uuid4().hex[:12]
    desktop_filename = f"{run_id}_desktop.png"
    mobile_filename = f"{run_id}_mobile.png"
    desktop_filepath = SCREENSHOT_DIR / desktop_filename
    mobile_filepath = SCREENSHOT_DIR / mobile_filename

    async with async_playwright() as p:
        browser = None
        try:
            browser = await p.chromium.launch(headless=True)
            
            # --- 1. Desktop Context & Evaluation ---
            desktop_context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 PlacementReadinessBot/1.0",
            )
            desktop_page = await desktop_context.new_page()

            # Attach event listeners
            console_errors: List[str] = []
            network_errors: List[str] = []

            desktop_page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}") if msg.type in ("error",) else None)
            desktop_page.on("pageerror", lambda exc: console_errors.append(f"[pageerror] {str(exc)}"))
            desktop_page.on("requestfailed", lambda req: network_errors.append(f"{req.url} failed: {req.failure}"))

            start_time = asyncio.get_event_loop().time()
            try:
                response = await desktop_page.goto(
                    url,
                    timeout=timeout_ms,
                    wait_until="domcontentloaded",
                )
                end_time = asyncio.get_event_loop().time()
                result["load_time_ms"] = int((end_time - start_time) * 1000)

                if response is not None:
                    result["status_code"] = response.status
                    if 200 <= response.status < 400:
                        result["loaded"] = True
                    else:
                        result["loaded"] = False
                        result["error_message"] = f"Server returned HTTP {response.status} error."
                else:
                    # e.g. file:// URL or non-HTTP response
                    result["loaded"] = True
                    result["status_code"] = 200

                # Allow a brief moment for dynamic client-side JS hydration
                await asyncio.sleep(0.5)

                result["title"] = (await desktop_page.title()) or ""
                
                # Extract meta description
                try:
                    meta_desc_handle = await desktop_page.query_selector('meta[name="description"]')
                    if meta_desc_handle:
                        result["meta_description"] = (await meta_desc_handle.get_attribute("content")) or ""
                except Exception:
                    pass

                # Extract visible text snippet
                try:
                    raw_text = await desktop_page.inner_text("body")
                    cleaned_text = " ".join(raw_text.split())
                    result["extracted_snippet"] = cleaned_text[:500]
                except Exception:
                    cleaned_text = ""

                # Capture desktop screenshot
                try:
                    await desktop_page.screenshot(path=str(desktop_filepath), full_page=False)
                    result["desktop_screenshot"] = desktop_filename
                except Exception as sc_err:
                    logger.warning(f"Could not take desktop screenshot: {sc_err}")

            except PlaywrightTimeoutError:
                result["error_message"] = f"Page navigation timed out after {timeout_ms // 1000} seconds."
                result["loaded"] = False
                return result
            except PlaywrightError as pe:
                result["error_message"] = f"Navigation failed: {str(pe)}"
                result["loaded"] = False
                return result
            finally:
                result["console_errors"] = console_errors
                result["network_errors"] = network_errors
                await desktop_context.close()

            # --- 2. Mobile Context & Responsive Viewport Evaluation ---
            if result["loaded"]:
                mobile_context = await browser.new_context(
                    viewport={"width": 375, "height": 667},
                    is_mobile=True,
                    has_touch=True,
                    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1 PlacementReadinessBot/1.0",
                )
                mobile_page = await mobile_context.new_page()
                try:
                    await mobile_page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                    await asyncio.sleep(0.3)

                    # Check for horizontal viewport overflow
                    try:
                        has_overflow = await mobile_page.evaluate(
                            "() => document.documentElement.scrollWidth > window.innerWidth + 5"
                        )
                        result["mobile_overflow"] = bool(has_overflow)
                    except Exception:
                        result["mobile_overflow"] = False

                    # Capture mobile screenshot
                    await mobile_page.screenshot(path=str(mobile_filepath), full_page=False)
                    result["mobile_screenshot"] = mobile_filename
                except Exception as m_err:
                    logger.warning(f"Mobile evaluation error: {m_err}")
                finally:
                    await mobile_context.close()

            # --- 3. Content Match Heuristic ---
            if result["loaded"]:
                claims_tokens: set[str] = set()
                if project_title:
                    claims_tokens.update(re_tokens(project_title))
                if expected_keywords:
                    for kw in expected_keywords:
                        claims_tokens.update(re_tokens(kw))

                if claims_tokens:
                    page_tokens = set(re_tokens(result["title"] + " " + result["meta_description"] + " " + result.get("extracted_snippet", "")))
                    overlap = claims_tokens.intersection(page_tokens)
                    ratio = len(overlap) / max(len(claims_tokens), 1)
                    result["content_overlap_ratio"] = round(ratio, 2)
                    result["content_match"] = ratio >= 0.25
                else:
                    result["content_match"] = True
                    result["content_overlap_ratio"] = 1.0

        except Exception as e:
            logger.error(f"Live link checker unexpected error: {e}", exc_info=True)
            result["error_message"] = f"Failed to check live URL: {str(e)}"
        finally:
            if browser:
                await browser.close()

    return result


def re_tokens(text: str) -> List[str]:
    """Helper to tokenize alphanumeric words of length >= 3."""
    import re
    tokens = re.findall(r"[a-zA-Z0-9_\-]{3,}", text.lower())
    # Exclude common stopwords
    stopwords = {"and", "the", "for", "with", "this", "that", "from", "your", "app", "web", "http", "https"}
    return [t for t in tokens if t not in stopwords]
