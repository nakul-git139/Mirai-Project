from __future__ import annotations
import os
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.resume_reviewer import review_resume
from tests.create_fixtures import FIXTURES_DIR, generate_all_fixtures



@pytest.fixture(scope="module", autouse=True)
def ensure_fixtures():
    """Ensure all fixtures are generated before tests run."""
    generate_all_fixtures()


def test_four_resumes_planted_flaws_detected():
    """
    Verification Requirement 1:
    Test 4 test resumes with KNOWN flaws:
    (a) a good one, (b) 2 pages, (c) missing GitHub/LeetCode links and with typos, (d) an image-only PDF.
    Assert each planted flaw is detected and the good resume scores clearly higher.
    """
    good_path = os.path.join(FIXTURES_DIR, "resume_good.pdf")
    p2_path = os.path.join(FIXTURES_DIR, "resume_2page.pdf")
    flawed_path = os.path.join(FIXTURES_DIR, "resume_missing_links_typos.pdf")
    img_path = os.path.join(FIXTURES_DIR, "resume_image_only.pdf")

    with open(good_path, "rb") as f:
        good_bytes = f.read()
    with open(p2_path, "rb") as f:
        p2_bytes = f.read()
    with open(flawed_path, "rb") as f:
        flawed_bytes = f.read()
    with open(img_path, "rb") as f:
        img_bytes = f.read()

    # (a) Review Good Resume
    good_res = review_resume(good_bytes, "resume_good.pdf")
    assert good_res["score"] >= 90, f"Good resume expected score >= 90, got {good_res['score']}"
    checks_by_id = {c["id"]: c for c in good_res["checks"]}
    assert checks_by_id["CHK-PAGE-COUNT"]["pass"] is True
    assert checks_by_id["CHK-PROFILE-LINKS"]["pass"] is True
    assert checks_by_id["CHK-SPELL-GRAMMAR"]["pass"] is True
    assert checks_by_id["CHK-ATS-FRIENDLY"]["pass"] is True
    assert checks_by_id["CHK-ACHIEVEMENTS"]["pass"] is True
    assert checks_by_id["CHK-ACTION-RESULTS"]["pass"] is True

    # (b) Review 2-Page Resume
    p2_res = review_resume(p2_bytes, "resume_2page.pdf")
    p2_checks = {c["id"]: c for c in p2_res["checks"]}
    # Assert planted flaw (page count > 1) is detected
    assert p2_checks["CHK-PAGE-COUNT"]["pass"] is False
    assert "2 pages" in p2_checks["CHK-PAGE-COUNT"]["evidence"]
    assert "Condense" in p2_checks["CHK-PAGE-COUNT"]["fix"]
    assert good_res["score"] > p2_res["score"]

    # (c) Review Missing Links & Typos Resume
    flawed_res = review_resume(flawed_bytes, "resume_missing_links_typos.pdf")
    flawed_checks = {c["id"]: c for c in flawed_res["checks"]}
    # Assert missing LeetCode link detected
    assert flawed_checks["CHK-PROFILE-LINKS"]["pass"] is False
    assert "LeetCode" in flawed_checks["CHK-PROFILE-LINKS"]["evidence"]
    # Assert planted typos detected (managment, expereince, softare)
    assert flawed_checks["CHK-SPELL-GRAMMAR"]["pass"] is False
    assert ("managment" in flawed_checks["CHK-SPELL-GRAMMAR"]["evidence"] or
            "expereince" in flawed_checks["CHK-SPELL-GRAMMAR"]["evidence"] or
            "softare" in flawed_checks["CHK-SPELL-GRAMMAR"]["evidence"])
    # Assert weak bullet points detected
    assert flawed_checks["CHK-ACTION-RESULTS"]["pass"] is False
    assert good_res["score"] > flawed_res["score"]
    assert good_res["score"] - flawed_res["score"] >= 20

    # (d) Review Image-Only PDF
    img_res = review_resume(img_bytes, "resume_image_only.pdf")
    img_checks = {c["id"]: c for c in img_res["checks"]}
    # Assert ATS-friendly failed due to image-only flattening
    assert img_checks["CHK-ATS-FRIENDLY"]["pass"] is False
    assert "image-only" in img_checks["CHK-ATS-FRIENDLY"]["evidence"].lower()
    assert img_res["score"] < 35
    assert good_res["score"] > img_res["score"]


def test_consistency_five_runs(capsys):
    """
    Verification Requirement 2:
    Consistency test: review the same resume 5 times and assert max-min score <= 3.
    Print all 5 scores.
    """
    resume_path = os.path.join(FIXTURES_DIR, "resume_good.pdf")
    with open(resume_path, "rb") as f:
        file_bytes = f.read()

    scores = []
    for run in range(5):
        result = review_resume(file_bytes, "resume_good.pdf")
        scores.append(result["score"])

    # Explicitly print all 5 scores as requested
    print(f"\n[CONSISTENCY TEST] 5 Consecutive Review Scores: {scores}")

    max_score = max(scores)
    min_score = min(scores)
    diff = max_score - min_score
    print(f"[CONSISTENCY TEST] Max Score: {max_score}, Min Score: {min_score}, Diff: {diff}")

    assert diff <= 3, f"Score variance exceeded ±3: max={max_score}, min={min_score}, diff={diff}"
    assert len(scores) == 5


def test_failed_checks_have_specific_non_generic_fixes():
    """
    Verification Requirement 3:
    Check that every failed check has a non-empty, specific fix
    (assert it is not a generic phrase like 'improve your resume').
    """
    flawed_path = os.path.join(FIXTURES_DIR, "resume_missing_links_typos.pdf")
    p2_path = os.path.join(FIXTURES_DIR, "resume_2page.pdf")
    img_path = os.path.join(FIXTURES_DIR, "resume_image_only.pdf")

    flawed_files = [
        (flawed_path, "resume_missing_links_typos.pdf"),
        (p2_path, "resume_2page.pdf"),
        (img_path, "resume_image_only.pdf"),
    ]

    generic_forbidden_phrases = [
        "improve your resume",
        "fix your resume",
        "make it better",
        "improve resume",
        "fix errors",
        "update resume",
    ]

    total_failed_checks_inspected = 0

    for path, filename in flawed_files:
        with open(path, "rb") as f:
            b = f.read()
        res = review_resume(b, filename)
        for check in res["checks"]:
            if not check["pass"]:
                total_failed_checks_inspected += 1
                fix = check["fix"].strip()
                # Must not be empty
                assert fix, f"Fix was empty for failed check {check['id']}"
                # Must have substance (> 15 chars)
                assert len(fix) >= 15, f"Fix was too short ({len(fix)} chars) for check {check['id']}: '{fix}'"
                # Must not contain any forbidden generic phrase
                fix_lower = fix.lower()
                for generic in generic_forbidden_phrases:
                    assert generic not in fix_lower, f"Generic fix phrase '{generic}' detected in check {check['id']}: '{fix}'"

    assert total_failed_checks_inspected >= 5, "Expected at least 5 failed checks across flawed test resumes"


def test_resume_review_api_endpoints(client: TestClient):
    """
    End-to-end API test: registration, consent, resume upload, trigger review,
    fetch latest review, and fetch rendered PNG preview.
    """
    # Register student
    reg_res = client.post(
        "/api/auth/register",
        json={"email": "reviewer_student@mirai.dev", "password": "password123", "role": "student"},
    )
    assert reg_res.status_code in [200, 201]

    # Login to obtain access token
    login_res = client.post(
        "/api/auth/login",
        json={"email": "reviewer_student@mirai.dev", "password": "password123"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Grant consent
    consent_res = client.post("/api/profile/consent", json={"consent_given": True}, headers=headers)
    assert consent_res.status_code == 200

    # Upload resume
    good_path = os.path.join(FIXTURES_DIR, "resume_good.pdf")
    with open(good_path, "rb") as f:
        upload_res = client.post(
            "/api/profile/resume",
            files={"file": ("resume_good.pdf", f, "application/pdf")},
            headers=headers,
        )
    assert upload_res.status_code == 200

    # Trigger review via API
    review_res = client.post("/api/reviews/resume", headers=headers)
    assert review_res.status_code == 200
    data = review_res.json()
    assert "score" in data
    assert data["score"] >= 90
    assert "summary" in data
    assert "checks" in data
    assert len(data["checks"]) == 8

    # Each check must return {id, label, pass, evidence, fix}
    for chk in data["checks"]:
        assert "id" in chk
        assert "label" in chk
        assert "pass" in chk
        assert "evidence" in chk
        assert "fix" in chk

    # Fetch latest review via GET
    latest_res = client.get("/api/reviews/resume/latest", headers=headers)
    assert latest_res.status_code == 200
    latest_data = latest_res.json()
    assert latest_data["id"] == data["id"]
    assert latest_data["score"] == data["score"]

    # Fetch preview image
    preview_res = client.get("/api/reviews/resume/preview-image", headers=headers)
    assert preview_res.status_code == 200
    assert preview_res.headers["content-type"] == "image/png"
    assert len(preview_res.content) > 1000  # Valid PNG bytes


def test_resume_review_consent_enforcement(client: TestClient):
    """
    Verify that an attempt to trigger a resume review without consent returns 400 Bad Request.
    """
    reg_res = client.post(
        "/api/auth/register",
        json={"email": "noconsent_review@mirai.dev", "password": "password123", "role": "student"},
    )
    assert reg_res.status_code in [200, 201]

    login_res = client.post(
        "/api/auth/login",
        json={"email": "noconsent_review@mirai.dev", "password": "password123"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to trigger review without consent
    res = client.post("/api/reviews/resume", headers=headers)
    assert res.status_code == 400
    assert "consent is required" in res.json()["detail"].lower()
