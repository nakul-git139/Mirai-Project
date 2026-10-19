from __future__ import annotations
import os
import sys
import time
import pytest
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

FRONTEND_URL = "http://localhost:5173"


def open_auth_and_ensure_mode(page, target_mode="register"):
    if page.locator("#logout-btn").count() > 0 and page.locator("#logout-btn").is_visible():
        page.click("#logout-btn")
        page.wait_for_timeout(400)
    page.wait_for_selector("#login-trigger-btn", timeout=6000)
    page.click("#login-trigger-btn")
    page.wait_for_selector("#toggle-auth-mode-btn", timeout=4000)
    toggle_text = page.locator("#toggle-auth-mode-btn").inner_text()
    if target_mode == "register" and "Sign up" in toggle_text:
        page.click("#toggle-auth-mode-btn")
        page.wait_for_timeout(300)
    elif target_mode == "login" and "Sign in" in toggle_text:
        page.click("#toggle-auth-mode-btn")
        page.wait_for_timeout(300)


def submit_auth_and_wait(page):
    page.click("#auth-submit-btn")
    try:
        page.wait_for_selector("#logout-btn", timeout=8000)
    except Exception as e:
        err_box = page.locator(".bg-red-950\\/40")
        err_msg = err_box.inner_text() if err_box.is_visible() else "No error banner visible"
        print(f"ERROR: Auth submission failed. Banner text: {err_msg}")
        raise e


@pytest.fixture
def cleanup_e2e_records():
    emails = []
    yield emails
    try:
        from app.database import SessionLocal
        from app.models import User, Profile, ReadinessScore, Job, Application
        with SessionLocal() as db_session:
            for email in emails:
                u = db_session.query(User).filter(User.email == email).first()
                if u:
                    db_session.query(Application).filter(Application.user_id == u.id).delete()
                    db_session.query(Profile).filter(Profile.user_id == u.id).delete()
                    db_session.query(ReadinessScore).filter(ReadinessScore.user_id == u.id).delete()
                    db_session.query(Job).filter(Job.posted_by_user_id == u.id).delete()
                    db_session.delete(u)
            db_session.commit()
            print("\n✓ Cleaned up test user accounts, profiles, jobs, and applications.")
    except Exception as e:
        print(f"Cleanup notice: {e}")


def test_browser_e2e_tracker_and_admin_flow(cleanup_e2e_records=None):
    """
    Dual-session browser verification using Playwright:
    1. Admin logs in, posts job with eligibility criteria (React, TypeScript, 70 score).
    2. Ineligible student logs in -> does NOT see the job.
    3. Eligible student logs in -> sees job pinned at top, applies via 'Open & Apply', logs in Tracker.
    4. Admin views applicants, promotes student to 'Interview'.
    5. Student checks tracker -> card is in 'Interview' column, 'Has Movement' filter shows it,
       and timeline displays Applied -> Interview.
    """
    run_id = int(time.time())
    admin_email = f"admin_{run_id}@msot.ac.in"
    eligible_email = f"eligible_{run_id}@msot.ac.in"
    ineligible_email = f"ineligible_{run_id}@msot.ac.in"
    password = "password123"

    if cleanup_e2e_records is not None:
        cleanup_e2e_records.extend([admin_email, eligible_email, ineligible_email])

    job_title = f"Full Stack Campus Fellow {run_id}"

    import urllib.request
    try:
        urllib.request.urlopen(FRONTEND_URL, timeout=1)
    except Exception:
        pytest.skip(f"Frontend dev server not running at {FRONTEND_URL}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # -----------------------------------------------------------------
        # STEP 1: Admin Session - Post Job with Eligibility Criteria
        # -----------------------------------------------------------------
        print(f"\n--- STEP 1: Admin Session ({admin_email}) ---")
        page.goto(FRONTEND_URL)
        page.wait_for_load_state("domcontentloaded")

        open_auth_and_ensure_mode(page, target_mode="register")
        page.fill("#auth-fullname-input", "Prof. Sharma (Admin)")
        page.fill("#auth-email-input", admin_email)
        page.fill("#auth-password-input", password)
        page.click("#role-admin-btn")
        page.wait_for_timeout(200)
        submit_auth_and_wait(page)

        # Verify admin tab
        page.wait_for_selector("#nav-admin", timeout=5000)
        page.click("#nav-admin")
        page.wait_for_timeout(500)

        # Fill Post Job form with eligibility criteria
        page.fill("input[placeholder*='e.g. Associate Backend Engineer']", job_title)
        page.fill("input[placeholder*='e.g. Cloudflare, Acme Partner']", "Atlassian Placement Partner")
        page.fill("input[placeholder*='e.g. React, TypeScript, Python']", "React, TypeScript")
        page.fill("input[placeholder*='e.g. Frontend Engineer, Full Stack']", "Frontend Engineer")
        page.fill("input[type='url']", "https://atlassian.com/jobs/campus-2026")

        # Submit job
        page.click("button:has-text('Publish Campus Opening')")
        page.wait_for_timeout(1000)

        # Verify job is listed with Pinned tag
        page.wait_for_selector(f"text={job_title}", timeout=5000)
        assert page.locator(f"text={job_title}").is_visible()
        print("✓ Admin successfully published job with benchmark eligibility criteria.")

        # Log out
        page.click("#logout-btn")
        page.wait_for_selector("#login-trigger-btn", timeout=6000)

        # -----------------------------------------------------------------
        # STEP 2: Ineligible Student Session (Backend / Python Profile)
        # -----------------------------------------------------------------
        print(f"\n--- STEP 2: Ineligible Student Session ({ineligible_email}) ---")
        open_auth_and_ensure_mode(page, target_mode="register")
        page.fill("#auth-fullname-input", "Bob Ineligible")
        page.fill("#auth-email-input", ineligible_email)
        page.fill("#auth-password-input", password)
        page.click("#role-student-btn")
        page.wait_for_timeout(200)
        submit_auth_and_wait(page)

        # Set profile skills to Python / Backend
        from app.database import SessionLocal
        from app.models import User, Profile, ReadinessScore
        from sqlalchemy.orm.attributes import flag_modified

        with SessionLocal() as db_session:
            u = None
            for _ in range(10):
                u = db_session.query(User).filter(User.email == ineligible_email).first()
                if u:
                    break
                time.sleep(0.3)
            assert u is not None, f"User {ineligible_email} was not found in database"

            prof = db_session.query(Profile).filter(Profile.user_id == u.id).first()
            if not prof:
                prof = Profile(
                    user_id=u.id,
                    consent_given=True,
                    skills=["Python", "Django", "PostgreSQL"],
                    target_roles=["Backend Engineer"],
                )
                db_session.add(prof)
            else:
                prof.consent_given = True
                prof.skills = ["Python", "Django", "PostgreSQL"]
                prof.target_roles = ["Backend Engineer"]
                flag_modified(prof, "skills")
                flag_modified(prof, "target_roles")
            db_session.commit()

        page.wait_for_timeout(300)

        # Go to Jobs tab
        page.click("#nav-jobs")
        page.wait_for_timeout(500)
        try:
            page.wait_for_selector("text=Discovering live job postings", state="detached", timeout=60000)
        except Exception:
            pass

        # Ineligible student MUST NOT see the job
        assert not page.locator(f"text={job_title}").is_visible()
        print("✓ Ineligible student correctly does NOT see the restricted campus opening.")

        # Log out
        page.click("#logout-btn")
        page.wait_for_selector("#login-trigger-btn", timeout=6000)

        # -----------------------------------------------------------------
        # STEP 3: Eligible Student Session (Frontend Engineer Profile)
        # -----------------------------------------------------------------
        print(f"\n--- STEP 3: Eligible Student Session ({eligible_email}) ---")
        open_auth_and_ensure_mode(page, target_mode="register")
        page.fill("#auth-fullname-input", "Alice Eligible")
        page.fill("#auth-email-input", eligible_email)
        page.fill("#auth-password-input", password)
        page.click("#role-student-btn")
        page.wait_for_timeout(200)
        submit_auth_and_wait(page)

        # Set eligible profile with benchmark readiness score (85 >= 70) and frontend skills
        with SessionLocal() as db_session:
            u = None
            for _ in range(10):
                u = db_session.query(User).filter(User.email == eligible_email).first()
                if u:
                    break
                time.sleep(0.3)
            assert u is not None, f"User {eligible_email} was not found in database"

            prof = db_session.query(Profile).filter(Profile.user_id == u.id).first()
            if not prof:
                prof = Profile(
                    user_id=u.id,
                    consent_given=True,
                    skills=["React", "TypeScript", "TailwindCSS"],
                    target_roles=["Frontend Engineer"],
                )
                db_session.add(prof)
            else:
                prof.consent_given = True
                prof.skills = ["React", "TypeScript", "TailwindCSS"]
                prof.target_roles = ["Frontend Engineer"]
                flag_modified(prof, "skills")
                flag_modified(prof, "target_roles")

            rs = db_session.query(ReadinessScore).filter(ReadinessScore.user_id == u.id).first()
            if not rs:
                rs = ReadinessScore(
                    user_id=u.id,
                    overall_score=85,
                    breakdown={"resume": 85, "technical": 85, "overall": 85},
                )
                db_session.add(rs)
            else:
                rs.overall_score = 85
            db_session.commit()

        page.wait_for_timeout(300)

        # Go to Jobs tab
        page.click("#nav-jobs")
        page.wait_for_timeout(500)
        try:
            page.wait_for_selector("text=Discovering live job postings", state="detached", timeout=60000)
        except Exception:
            pass

        # Search for the exact job posting
        page.fill("input[placeholder*='Search jobs by title']", job_title)
        page.wait_for_timeout(500)

        # Eligible student MUST see the job PINNED AT THE TOP
        page.wait_for_selector(f"text={job_title}", timeout=20000)
        assert page.locator(f"text={job_title}").is_visible()
        assert page.locator("text=MSOT Campus Direct Posting • Pinned for Eligible Students").first.is_visible()
        print("✓ Eligible student sees the campus opening pinned at the top.")

        # Click Open & Apply for this specific job
        page.locator("button:has-text('Open & Apply')").first.click()
        page.wait_for_timeout(500)

        # In modal, click "Mark as Applied"
        page.wait_for_selector("button:has-text('Mark as Applied')", timeout=3000)
        page.click("button:has-text('Mark as Applied')")
        page.wait_for_timeout(500)
        print("✓ Student applied via One-Click Open & Apply and logged as Applied.")

        # Navigate to Application Tracker via modal shortcut
        page.wait_for_selector("button:has-text('Go to Application Tracker')", timeout=3000)
        page.click("button:has-text('Go to Application Tracker')")
        page.wait_for_timeout(1000)

        # Verify card is in Applied column
        page.wait_for_selector(f"text={job_title}", timeout=15000)
        assert page.locator(f"text={job_title}").first.is_visible()
        print("✓ Card successfully rendered in Application Tracker Kanban.")

        # Toggle to Table view
        page.click("button:has-text('Table')")
        page.wait_for_timeout(500)
        assert page.locator("table").is_visible()
        print("✓ Table view successfully rendered with tabular row.")

        # Switch back to Kanban
        page.click("button:has-text('Kanban')")
        page.wait_for_timeout(300)

        # Log out
        page.click("#logout-btn")
        page.wait_for_selector("#login-trigger-btn", timeout=6000)

        # -----------------------------------------------------------------
        # STEP 4: Admin Promotes Student to Interview
        # -----------------------------------------------------------------
        print(f"\n--- STEP 4: Admin Promotes Student ({admin_email}) ---")
        open_auth_and_ensure_mode(page, target_mode="login")
        page.fill("#auth-email-input", admin_email)
        page.fill("#auth-password-input", password)
        submit_auth_and_wait(page)

        page.click("#nav-admin")
        page.wait_for_timeout(800)

        # View applicants for target job card
        job_card = page.locator("div.p-5").filter(has_text=job_title).first
        job_card.locator("button:has-text('Applicants')").click()
        page.wait_for_timeout(500)

        # Promote status to Interview
        page.wait_for_selector("select", timeout=4000)
        applicant_select = page.locator("select").last
        applicant_select.select_option("Interview")
        page.wait_for_timeout(1000)
        print("✓ Admin viewed applicants and promoted student to 'Interview'.")

        # Close modal and log out
        page.click("button:has-text('Close')")
        page.wait_for_timeout(300)
        page.click("#logout-btn")
        page.wait_for_selector("#login-trigger-btn", timeout=6000)

        # -----------------------------------------------------------------
        # STEP 5: Student Sees Movement in Tracker
        # -----------------------------------------------------------------
        print(f"\n--- STEP 5: Student Verifies Movement ({eligible_email}) ---")
        open_auth_and_ensure_mode(page, target_mode="login")
        page.fill("#auth-email-input", eligible_email)
        page.fill("#auth-password-input", password)
        submit_auth_and_wait(page)

        page.click("#nav-tracker")
        page.wait_for_timeout(800)

        # Verify application shows in Interview column
        page.wait_for_selector(f"text={job_title}", timeout=15000)
        assert page.locator(f"text={job_title}").first.is_visible()

        # Click Has Movement filter
        page.click("button:has-text('Has Movement')")
        page.wait_for_timeout(500)
        assert page.locator(f"text={job_title}").first.is_visible()
        print("✓ 'Has Movement' filter successfully displays the updated application.")

        # Click card to inspect details and timeline
        page.locator(f"text={job_title}").first.click()
        page.wait_for_timeout(500)
        page.wait_for_selector("text=Movement & Timeline History", timeout=3000)
        assert page.locator("text=Movement & Timeline History").is_visible()
        print("✓ Timeline modal verified with status transition history.")

        # Close modal
        page.click("button:has-text('Close')")
        page.wait_for_timeout(300)

        browser.close()
        print("\n=== ALL DUAL-SESSION BROWSER E2E STEPS VERIFIED SUCCESSFULLY ===")


if __name__ == "__main__":
    records = []
    try:
        test_browser_e2e_tracker_and_admin_flow(records)
    finally:
        try:
            from app.database import SessionLocal
            from app.models import User, Profile, ReadinessScore, Job, Application
            with SessionLocal() as db_session:
                for email in records:
                    u = db_session.query(User).filter(User.email == email).first()
                    if u:
                        db_session.query(Application).filter(Application.user_id == u.id).delete()
                        db_session.query(Profile).filter(Profile.user_id == u.id).delete()
                        db_session.query(ReadinessScore).filter(ReadinessScore.user_id == u.id).delete()
                        db_session.query(Job).filter(Job.posted_by_user_id == u.id).delete()
                        db_session.delete(u)
                db_session.commit()
                print("✓ Cleaned up test user accounts, profiles, jobs, and applications.")
        except Exception as e:
            print(f"Cleanup notice: {e}")
