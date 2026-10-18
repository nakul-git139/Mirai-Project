#!/usr/bin/env python3
import json
import os
import sys
import time
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.auth import create_access_token

OUT_DIR = os.path.abspath(os.path.join(BASE_DIR, "docs", "screenshots"))
os.makedirs(OUT_DIR, exist_ok=True)

def capture_ui():
    student_token = create_access_token({"sub": "11", "role": "student", "email": "student@msot.edu"})
    student_user = {"id": 11, "email": "student@msot.edu", "role": "student", "full_name": "Alex Rivera"}

    admin_token = create_access_token({"sub": "81", "role": "admin", "email": "admin@msot.edu"})
    admin_user = {"id": 81, "email": "admin@msot.edu", "role": "admin", "full_name": "MSOT Placement Admin"}

    with sync_playwright() as p:
        # 1. Student Session
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        
        # Inject student credentials into localStorage before loading
        init_js = f"""
            localStorage.setItem('copilot_token', '{student_token}');
            localStorage.setItem('copilot_user', JSON.stringify({json.dumps(student_user)}));
        """
        context.add_init_script(init_js)
        page = context.new_page()

        print("[*] Loading Student Copilot...")
        page.goto("http://localhost:5173/")
        page.wait_for_load_state("domcontentloaded")
        time.sleep(2)

        # 1. Dashboard / Readiness Score
        print("[*] Capturing 01_readiness_dashboard.png...")
        page.click("#nav-score")
        time.sleep(1.5)
        page.screenshot(path=os.path.join(OUT_DIR, "01_readiness_dashboard.png"), full_page=False)

        # 2. Benchmark Reviews
        print("[*] Capturing 02_benchmark_reviews.png...")
        page.click("#nav-reviews")
        time.sleep(1.5)
        page.screenshot(path=os.path.join(OUT_DIR, "02_benchmark_reviews.png"), full_page=False)

        # 3. Mock Interview
        print("[*] Capturing 03_mock_interview.png...")
        page.click("#nav-interview")
        time.sleep(1.5)
        page.screenshot(path=os.path.join(OUT_DIR, "03_mock_interview.png"), full_page=False)

        # 4. Job Discovery
        print("[*] Capturing 04_job_discovery.png...")
        page.click("#nav-jobs")
        time.sleep(1.5)
        page.screenshot(path=os.path.join(OUT_DIR, "04_job_discovery.png"), full_page=False)

        # 5. Application Tracker
        print("[*] Capturing 05_job_tracker.png...")
        page.click("#nav-tracker")
        time.sleep(1.5)
        page.screenshot(path=os.path.join(OUT_DIR, "05_job_tracker.png"), full_page=False)

        browser.close()

        # 2. Admin Session
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        admin_init_js = f"""
            localStorage.setItem('copilot_token', '{admin_token}');
            localStorage.setItem('copilot_user', JSON.stringify({json.dumps(admin_user)}));
        """
        context.add_init_script(admin_init_js)
        page = context.new_page()

        print("[*] Loading Admin Portal...")
        page.goto("http://localhost:5173/")
        page.wait_for_load_state("domcontentloaded")
        time.sleep(2)

        # 6. Admin Board
        print("[*] Capturing 06_admin_board.png...")
        if page.locator("#nav-admin").count() > 0:
            page.click("#nav-admin")
            time.sleep(1.5)
            page.screenshot(path=os.path.join(OUT_DIR, "06_admin_board.png"), full_page=False)

        browser.close()
        print(f"\n[+] Successfully generated 6 high-resolution UI screenshots in: {OUT_DIR}")

if __name__ == "__main__":
    capture_ui()
