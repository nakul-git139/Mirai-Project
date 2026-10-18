from __future__ import annotations
import os
import io
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.profile_parser import (
    parse_resume_file,
    parse_linkedin_text,
    extract_profile_data_from_chat_text,
)
from tests.create_fixtures import generate_all_fixtures

FIXTURES = generate_all_fixtures()


# ---------------- 1. Fixture Parsing Unit Tests ----------------
def test_clean_1page_pdf_parsing():
    """Assert page count is 1, sections are parsed, links and skills extracted."""
    with open(FIXTURES["clean_pdf"], "rb") as f:
        data = f.read()
    parsed = parse_resume_file(data, "clean_1page_resume.pdf")

    assert parsed["page_count"] == 1
    assert "skills" in parsed["sections"]
    assert "experience" in parsed["sections"]
    assert "projects" in parsed["sections"]
    assert "education" in parsed["sections"]

    # Assert expected skills found
    skills = [s.lower() for s in parsed["skills"]]
    assert "python" in skills
    assert "fastapi" in skills
    assert "react" in skills
    assert "docker" in skills
    assert "sql" in skills

    # Assert links extracted
    links = parsed["links"]
    assert any("github.com/alexrivera" in l for l in links)
    assert any("linkedin.com/in/alexrivera" in l for l in links)

    # Assert projects extracted
    assert len(parsed["projects"]) >= 1


def test_messy_multipage_pdf_parsing():
    """Assert page count is 3, multi-page sections, skills, and links extracted."""
    with open(FIXTURES["multipage_pdf"], "rb") as f:
        data = f.read()
    parsed = parse_resume_file(data, "messy_multipage_resume.pdf")

    assert parsed["page_count"] == 3
    assert "experience" in parsed["sections"]
    assert "projects" in parsed["sections"]

    skills = [s.lower() for s in parsed["skills"]]
    assert "python" in skills
    assert "go" in skills
    assert "kubernetes" in skills
    assert "kafka" in skills

    links = parsed["links"]
    assert any("github.com/jordansmith" in l for l in links)


def test_sample_docx_parsing():
    """Assert DOCX parsed page count >= 1, skills, and links extracted."""
    with open(FIXTURES["docx"], "rb") as f:
        data = f.read()
    parsed = parse_resume_file(data, "sample_resume.docx")

    assert parsed["page_count"] >= 1
    assert "experience" in parsed["sections"]
    assert "projects" in parsed["sections"]

    skills = [s.lower() for s in parsed["skills"]]
    assert "java" in skills
    assert "spring boot" in skills
    assert "mysql" in skills

    links = parsed["links"]
    assert any("github.com/taylormorgan" in l for l in links)


def test_corrupt_file_raises_clean_value_error():
    """Assert corrupt file raises clean ValueError rather than unhandled exception."""
    with open(FIXTURES["corrupt"], "rb") as f:
        data = f.read()

    with pytest.raises(ValueError) as excinfo:
        parse_resume_file(data, "corrupt_resume.pdf")

    assert "Invalid or corrupt" in str(excinfo.value) or "PDF" in str(excinfo.value)


def register_and_login(client: TestClient, email: str, password: str = "password123") -> tuple[str, int]:
    reg = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "role": "student"},
    )
    assert reg.status_code == 201
    user_id = reg.json()["id"]

    login = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return token, user_id


# ---------------- 2. Consent Rule & API Tests ----------------
def test_consent_rule_enforcement(client: TestClient):
    """Submitting GitHub username or uploading without consent must be rejected with HTTP 400."""
    token, user_id = register_and_login(client, "student_consent@test.edu")
    headers = {"Authorization": f"Bearer {token}"}

    # Verify initial consent is false
    me = client.get("/api/profile/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["consent_given"] is False

    # Attempt to update profile with GitHub username without consent -> Expect 400
    res_update = client.put(
        "/api/profile/me",
        json={"github_username": "student_no_consent"},
        headers=headers,
    )
    assert res_update.status_code == 400
    assert "Consent is required" in res_update.json()["detail"]

    # Attempt to upload resume without consent -> Expect 400
    with open(FIXTURES["clean_pdf"], "rb") as f:
        res_upload = client.post(
            "/api/profile/resume",
            files={"file": ("clean_1page_resume.pdf", f, "application/pdf")},
            headers=headers,
        )
    assert res_upload.status_code == 400
    assert "Consent is required" in res_upload.json()["detail"]

    # Now grant consent
    grant = client.post(
        "/api/profile/consent",
        json={"consent_given": True},
        headers=headers,
    )
    assert grant.status_code == 200
    assert grant.json()["consent_given"] is True

    # Now submitting GitHub username succeeds
    res_update_ok = client.put(
        "/api/profile/me",
        json={"github_username": "student_with_consent"},
        headers=headers,
    )
    assert res_update_ok.status_code == 200
    assert res_update_ok.json()["github_username"] == "student_with_consent"


def test_corrupt_file_api_returns_clean_400_not_500(client: TestClient):
    """Uploading corrupt file returns clean 400 without 500 error."""
    token, _ = register_and_login(client, "student_corrupt@test.edu")
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/api/profile/consent", json={"consent_given": True}, headers=headers)

    with open(FIXTURES["corrupt"], "rb") as f:
        res = client.post(
            "/api/profile/resume",
            files={"file": ("corrupt_resume.pdf", f, "application/pdf")},
            headers=headers,
        )

    assert res.status_code == 400
    assert "corrupt" in res.json()["detail"].lower() or "invalid" in res.json()["detail"].lower()


# ---------------- 3. Upload -> Parsed Data -> Edit -> Persist ----------------
def test_upload_parse_edit_persist_flow(client: TestClient):
    """Test full flow: upload resume -> parsed data appears -> edit field -> refresh -> edit persists."""
    token, _ = register_and_login(client, "student_flow@test.edu")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Grant consent
    client.post("/api/profile/consent", json={"consent_given": True}, headers=headers)

    # 2. Upload clean resume
    with open(FIXTURES["clean_pdf"], "rb") as f:
        upload_res = client.post(
            "/api/profile/resume",
            files={"file": ("clean_1page_resume.pdf", f, "application/pdf")},
            headers=headers,
        )
    assert upload_res.status_code == 200
    data = upload_res.json()
    assert data["parsed_resume"]["page_count"] == 1
    assert "Python" in data["skills"]

    # 3. Edit field (add a target role and modify bio)
    edit_res = client.put(
        "/api/profile/me",
        json={
            "headline": "Aspiring Cloud Backend Engineer",
            "bio": "Passionate about high-throughput microservices and distributed databases.",
            "target_roles": ["Backend Engineer", "Cloud Infrastructure Intern"],
            "skills": data["skills"] + ["GraphQL"],
        },
        headers=headers,
    )
    assert edit_res.status_code == 200
    assert edit_res.json()["headline"] == "Aspiring Cloud Backend Engineer"
    assert "GraphQL" in edit_res.json()["skills"]

    # 4. Refresh (GET /api/profile/me) -> Assert edits persisted
    get_res = client.get("/api/profile/me", headers=headers)
    assert get_res.status_code == 200
    profile_data = get_res.json()
    assert profile_data["headline"] == "Aspiring Cloud Backend Engineer"
    assert "GraphQL" in profile_data["skills"]
    assert "Backend Engineer" in profile_data["target_roles"]
    assert profile_data["parsed_resume"]["page_count"] == 1


# ---------------- 4. LinkedIn Intake Tests ----------------
def test_linkedin_pasted_and_pdf_intake(client: TestClient):
    """Test LinkedIn pasted text intake and skill extraction."""
    token, _ = register_and_login(client, "student_linkedin@test.edu")
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/api/profile/consent", json={"consent_given": True}, headers=headers)

    sample_linkedin_text = """Sarah Jenkins
Full Stack Software Engineer | React, Node.js & AWS Enthusiast

About
Driven software developer with experience delivering customer-facing web apps.
Specializing in React, TypeScript, and FastAPI.

Experience
Frontend Developer at WebCorp
Jan 2022 - Present
Built responsive components and enhanced performance metrics.

Skills
React, TypeScript, Python, FastAPI, Docker, AWS
"""
    res = client.post(
        "/api/profile/linkedin/paste",
        json={"text": sample_linkedin_text},
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert "React" in body["skills"]
    assert "Full Stack Software Engineer" in body["headline"]
    assert "Driven software developer" in body["bio"]
    assert body["linkedin_data"]["source"] == "pasted"


# ---------------- 5. Chat Intake Tests ----------------
def test_chat_intake(client: TestClient):
    """Test extracting GitHub and LeetCode links from chat messages."""
    token, _ = register_and_login(client, "student_chat@test.edu")
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/api/profile/consent", json={"consent_given": True}, headers=headers)

    res = client.post(
        "/api/profile/chat-intake",
        json={"message": "Hey copilot, check out my github https://github.com/coder-alice and my leetcode is leetcode.com/u/alice_algos!"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["success"] is True

    # Check that profile now has handles
    me = client.get("/api/profile/me", headers=headers)
    assert me.json()["github_username"] == "coder-alice"
    assert me.json()["leetcode_username"] == "alice_algos"


# ---------------- 6. Deletion Tests (Disk & DB Rows) ----------------
def test_delete_profile_data_and_account_removes_disk_files(client: TestClient):
    """
    Test deletion:
    After 'delete all my data', DB rows reset AND uploaded files on disk are removed.
    """
    token, user_id = register_and_login(client, "student_delete@test.edu")
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/api/profile/consent", json={"consent_given": True}, headers=headers)

    # Upload resume
    with open(FIXTURES["clean_pdf"], "rb") as f:
        up_res = client.post(
            "/api/profile/resume",
            files={"file": ("clean_1page_resume.pdf", f, "application/pdf")},
            headers=headers,
        )
    assert up_res.status_code == 200
    uploaded_files = up_res.json()["uploaded_files"]
    assert len(uploaded_files) >= 1

    # Inspect disk upload folder - verify file exists
    upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "uploads"))
    files_on_disk_before = [f for f in os.listdir(upload_dir) if f.startswith(f"{user_id}_")]
    assert len(files_on_disk_before) >= 1
    disk_path = os.path.join(upload_dir, files_on_disk_before[0])
    assert os.path.exists(disk_path)

    # Call DELETE /api/profile/data
    del_res = client.delete("/api/profile/data", headers=headers)
    assert del_res.status_code == 200

    # Verify DB rows are reset
    me_after = client.get("/api/profile/me", headers=headers)
    assert me_after.json()["parsed_resume"] == {}
    assert me_after.json()["skills"] == []
    assert len(me_after.json()["uploaded_files"]) == 0

    # Verify physical file on disk is DELETED
    assert not os.path.exists(disk_path)
    files_on_disk_after = [f for f in os.listdir(upload_dir) if f.startswith(f"{user_id}_")]
    assert len(files_on_disk_after) == 0

    # Upload again, then test complete account deletion
    with open(FIXTURES["clean_pdf"], "rb") as f:
        client.post(
            "/api/profile/resume",
            files={"file": ("clean_1page_resume.pdf", f, "application/pdf")},
            headers=headers,
        )
    files_reuploaded = [f for f in os.listdir(upload_dir) if f.startswith(f"{user_id}_")]
    assert len(files_reuploaded) >= 1

    del_account_res = client.delete("/api/profile/account", headers=headers)
    assert del_account_res.status_code == 200

    # Verify all disk files are unlinked
    files_after_account_del = [f for f in os.listdir(upload_dir) if f.startswith(f"{user_id}_")]
    assert len(files_after_account_del) == 0

    # Verify token is now invalid / user no longer exists
    assert client.get("/api/profile/me", headers=headers).status_code in [401, 404]


# ---------------- 7. Tenant Isolation Tests ----------------
def test_student_cannot_read_other_student_data(client: TestClient):
    """Student A cannot read Student B's data (expect 403 Forbidden)."""
    # Register Student A
    token_a, user_a_id = register_and_login(client, "student_a@test.edu")

    # Register Student B
    token_b, user_b_id = register_and_login(client, "student_b@test.edu")

    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Student A attempts to access Student B's profile directly
    res = client.get(f"/api/profile/{user_b_id}", headers=headers_a)
    assert res.status_code == 403
    assert "forbidden" in res.json()["detail"].lower()

    # Student A accessing their own profile by ID is permitted
    res_own = client.get(f"/api/profile/{user_a_id}", headers=headers_a)
    assert res_own.status_code == 200
    assert res_own.json()["user_id"] == user_a_id
