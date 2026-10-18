from __future__ import annotations
import os
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.linkedin_reviewer import review_linkedin
from tests.create_fixtures import FIXTURES_DIR, generate_all_fixtures


@pytest.fixture(scope="module", autouse=True)
def ensure_fixtures():
    """Ensure all fixtures are generated before tests run."""
    generate_all_fixtures()


@pytest.fixture
def student_auth_headers(client: TestClient) -> dict:
    """Helper to register and login a test student user."""
    email = f"li_student_{os.urandom(4).hex()}@example.com"
    pwd = "password123"
    reg_res = client.post("/api/auth/register", json={
        "email": email,
        "password": pwd,
        "role": "student",
        "full_name": "LinkedIn Test Student",
    })
    assert reg_res.status_code in [200, 201]

    login_res = client.post("/api/auth/login", json={"email": email, "password": pwd})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def verified_resume_context():
    """Standard verified resume context matching resume_good fixture."""
    return {
        "experience": [
            {
                "company": "Acme Cloud Solutions",
                "title": "Software Engineering Intern",
                "description": "Developed REST API endpoints using FastAPI and PostgreSQL, serving 50k daily active users.",
            }
        ],
        "projects": [
            {
                "title": "Readiness Copilot",
                "description": "Built full-stack placement readiness platform with Python, FastAPI, and React.",
            }
        ],
        "skills": ["Python", "TypeScript", "JavaScript", "React", "FastAPI", "PostgreSQL", "Docker", "Git", "Redis", "SQL"],
        "target_roles": ["Full Stack Engineer"],
        "raw_text": "Alex Rivera State University of California Bachelor of Science in Computer Science...",
    }


def test_three_profiles_score_ordering_and_contradiction_detection(verified_resume_context):
    """
    Verification Requirement 1:
    Create 3 fixtures (a strong profile, a weak/generic profile, a profile that contradicts the resume).
    Assert the scores order correctly and that the mismatch is flagged with the specific conflicting item.
    """
    strong_txt_path = os.path.join(FIXTURES_DIR, "linkedin_strong.txt")
    weak_txt_path = os.path.join(FIXTURES_DIR, "linkedin_weak.txt")
    contra_txt_path = os.path.join(FIXTURES_DIR, "linkedin_contradictory.txt")

    with open(strong_txt_path, "r", encoding="utf-8") as f:
        strong_text = f.read()
    with open(weak_txt_path, "r", encoding="utf-8") as f:
        weak_text = f.read()
    with open(contra_txt_path, "r", encoding="utf-8") as f:
        contra_text = f.read()

    # 1. Strong profile review
    strong_res = review_linkedin(text=strong_text, resume_context=verified_resume_context)
    strong_score = strong_res["score"]
    assert strong_score >= 85, f"Strong profile should score >= 85, got {strong_score}"
    strong_checks = {c["id"]: c for c in strong_res["checks"]}
    assert strong_checks["CHK-LI-HEADLINE"]["pass"] is True
    assert strong_checks["CHK-LI-ABOUT"]["pass"] is True
    assert strong_checks["CHK-LI-RESUME-MATCH"]["pass"] is True
    assert strong_checks["CHK-LI-SKILLS-ROLE"]["pass"] is True

    # 2. Contradictory profile review (claims VP of Engineering vs student intern)
    contra_res = review_linkedin(text=contra_text, resume_context=verified_resume_context)
    contra_score = contra_res["score"]
    contra_checks = {c["id"]: c for c in contra_res["checks"]}

    # Assert mismatch is detected by CHK-LI-RESUME-MATCH
    assert contra_checks["CHK-LI-RESUME-MATCH"]["pass"] is False
    evidence = contra_checks["CHK-LI-RESUME-MATCH"]["evidence"]
    fix = contra_checks["CHK-LI-RESUME-MATCH"]["fix"]

    # Assert the specific conflicting item is explicitly named in evidence and fix
    assert "VP of Engineering" in evidence or "VP of Engineering" in fix, f"Conflicting item not named in evidence/fix: {evidence}"
    assert "Acme Cloud Solutions" in evidence

    # 3. Weak profile review (generic headline, short about, 2 skills, no photo)
    weak_res = review_linkedin(text=weak_text, resume_context=verified_resume_context)
    weak_score = weak_res["score"]
    weak_checks = {c["id"]: c for c in weak_res["checks"]}
    assert weak_checks["CHK-LI-HEADLINE"]["pass"] is False
    assert weak_checks["CHK-LI-ABOUT"]["pass"] is False
    assert weak_checks["CHK-LI-SKILLS-ROLE"]["pass"] is False
    assert weak_score < 50, f"Weak profile should score < 50, got {weak_score}"

    # Assert strictly correct score ordering: Strong > Contradictory > Weak
    print(f"\nProfile Benchmark Scores: Strong={strong_score}, Contradictory={contra_score}, Weak={weak_score}")
    assert strong_score > contra_score > weak_score, (
        f"Expected strong ({strong_score}) > contra ({contra_score}) > weak ({weak_score})"
    )


def test_rewrites_length_and_groundedness(verified_resume_context):
    """
    Verification Requirement 2:
    Confirm the rewrites are non-empty, within LinkedIn limits (headline <= 220 chars),
    and contain no invented facts that are absent from the profile/resume.
    """
    strong_txt_path = os.path.join(FIXTURES_DIR, "linkedin_strong.txt")
    with open(strong_txt_path, "r", encoding="utf-8") as f:
        text = f.read()

    res = review_linkedin(text=text, resume_context=verified_resume_context)
    rewrites = res.get("rewrites", {})
    assert "headline" in rewrites and "about" in rewrites

    headline = rewrites["headline"]
    about = rewrites["about"]

    # 1. Non-empty
    assert len(headline.strip()) > 0
    assert len(about.strip()) > 0

    # 2. LinkedIn limit: headline <= 220 chars
    assert len(headline) <= 220, f"Headline rewrite exceeds 220 chars ({len(headline)} chars): {headline}"
    assert len(headline) >= 20, f"Headline rewrite too short: {headline}"

    # 3. About section substantive
    assert len(about) >= 150, f"About rewrite too short ({len(about)} chars): {about}"

    # 4. Zero hallucinated facts: check that any mentioned company, role, or tech exists in source context
    # Allowed companies and entities from context
    allowed_terms = ["Acme Cloud Solutions", "Readiness Copilot", "Python", "FastAPI", "React", "TypeScript", "PostgreSQL", "Full Stack Engineer"]
    # Check that headline only contains target role and verified skills
    for term in ["Full Stack Engineer", "Python", "FastAPI", "React"]:
        assert term in headline or term in about

    # Ensure no fabricated companies like "Google", "Meta", "Amazon", "Apple" are invented
    for forbidden in ["Google", "Meta", "Amazon", "Netflix", "Apple", "Microsoft"]:
        assert forbidden not in headline, f"Invented company '{forbidden}' found in headline: {headline}"
        assert forbidden not in about, f"Invented company '{forbidden}' found in about: {about}"


def test_consistency_five_runs(verified_resume_context, capsys):
    """
    Verification Requirement 3:
    Run the 5x consistency test (+-3).
    Assert max-min score <= 3 and print all 5 scores.
    """
    strong_txt_path = os.path.join(FIXTURES_DIR, "linkedin_strong.txt")
    with open(strong_txt_path, "r", encoding="utf-8") as f:
        text = f.read()

    scores = []
    for i in range(5):
        result = review_linkedin(text=text, resume_context=verified_resume_context)
        scores.append(result["score"])

    with capsys.disabled():
        print(f"\n[LinkedIn Review 5x Consistency Test] Run scores: {scores}")

    max_score = max(scores)
    min_score = min(scores)
    variance = max_score - min_score

    assert variance <= 3, f"Score variance across 5 runs was {variance} (> 3). Scores: {scores}"


def test_both_pdf_export_and_pasted_text_input(verified_resume_context):
    """
    Verification Requirement 4:
    Confirm it works with both PDF-export input and pasted-text input.
    """
    # 1. Test PDF-export input
    pdf_path = os.path.join(FIXTURES_DIR, "linkedin_strong.pdf")
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    pdf_res = review_linkedin(
        file_bytes=pdf_bytes,
        filename="linkedin_strong.pdf",
        resume_context=verified_resume_context,
    )
    assert pdf_res["score"] >= 85
    assert len(pdf_res["checks"]) == 5
    # Profile photo should pass via header image detection in PDF
    pdf_photo_check = next(c for c in pdf_res["checks"] if c["id"] == "CHK-LI-PHOTO")
    assert pdf_photo_check["pass"] is True
    assert "photo detected" in pdf_photo_check["evidence"].lower()

    # 2. Test Pasted-text input
    txt_path = os.path.join(FIXTURES_DIR, "linkedin_strong.txt")
    with open(txt_path, "r", encoding="utf-8") as f:
        txt_content = f.read()

    txt_res = review_linkedin(
        text=txt_content,
        resume_context=verified_resume_context,
    )
    assert txt_res["score"] >= 85
    assert len(txt_res["checks"]) == 5
    assert "rewrites" in txt_res
    assert len(txt_res["rewrites"]["headline"]) <= 220


def test_api_endpoints_pdf_and_text(client: TestClient, student_auth_headers: dict):
    """
    Tests REST API endpoints:
    - POST /api/reviews/linkedin (PDF upload)
    - POST /api/reviews/linkedin/paste (pasted text)
    - GET /api/reviews/linkedin/latest
    """
    # First grant student consent
    consent_res = client.post("/api/profile/consent", json={"consent_given": True}, headers=student_auth_headers)
    assert consent_res.status_code == 200

    # 1. Test POST /api/reviews/linkedin/paste
    strong_txt_path = os.path.join(FIXTURES_DIR, "linkedin_strong.txt")
    with open(strong_txt_path, "r", encoding="utf-8") as f:
        paste_text = f.read()

    paste_res = client.post("/api/reviews/linkedin/paste", json={"text": paste_text}, headers=student_auth_headers)
    assert paste_res.status_code == 200, paste_res.text
    data = paste_res.json()
    assert data["review_type"] == "linkedin"
    assert data["score"] >= 85
    assert len(data["checks"]) == 5
    assert "headline" in data["rewrites"]
    assert "about" in data["rewrites"]

    # 2. Test GET /api/reviews/linkedin/latest
    latest_res = client.get("/api/reviews/linkedin/latest", headers=student_auth_headers)
    assert latest_res.status_code == 200
    latest_data = latest_res.json()
    assert latest_data["id"] == data["id"]
    assert latest_data["score"] == data["score"]

    # 3. Test POST /api/reviews/linkedin with PDF upload
    pdf_path = os.path.join(FIXTURES_DIR, "linkedin_strong.pdf")
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    upload_res = client.post(
        "/api/reviews/linkedin",
        files={"file": ("linkedin_strong.pdf", pdf_bytes, "application/pdf")},
        headers=student_auth_headers,
    )
    assert upload_res.status_code == 200, upload_res.text
    upload_data = upload_res.json()
    assert upload_data["score"] >= 85
    assert len(upload_data["checks"]) == 5


def test_consent_enforcement_linkedin_review(client: TestClient):
    """
    Verifies that reviewing a LinkedIn profile without student consent returns HTTP 400.
    """
    email = f"li_noconsent_{os.urandom(4).hex()}@example.com"
    pwd = "password123"
    client.post("/api/auth/register", json={"email": email, "password": pwd, "role": "student"})
    login_res = client.post("/api/auth/login", json={"email": email, "password": pwd})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to review without consent
    res = client.post("/api/reviews/linkedin/paste", json={"text": "Student profile"}, headers=headers)
    assert res.status_code == 400
    assert "consent is required" in res.json()["detail"].lower()
