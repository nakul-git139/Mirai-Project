#!/usr/bin/env python3
"""
Privacy, Data Deletion, and Tenant Isolation Verification Script:
Validates mandatory consent gating, physical disk file unlinking on data wipe,
account deletion cascading, and tenant isolation between students.
Can be run directly (`python tests/test_privacy_deletion.py`) or via pytest (`pytest tests/test_privacy_deletion.py`).
"""
import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.main import app

FIXTURES_DIR = os.path.join(BACKEND_DIR, "tests", "fixtures")
UPLOAD_DIR = os.path.join(BACKEND_DIR, "data", "uploads")


def register_student(client: TestClient, email: str, password: str = "password123"):
    res = client.post("/api/auth/register", json={"email": email, "password": password, "full_name": email.split("@")[0], "role": "student"})
    assert res.status_code in [200, 201], f"Register failed: {res.text}"
    login_res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    user_id = login_res.json().get("user_id", res.json().get("id"))
    return token, user_id


def test_privacy_lifecycle_and_tenant_isolation(client: TestClient = None):
    import uuid
    uid = uuid.uuid4().hex[:6]
    standalone = False
    if client is None:
        standalone = True
        client = TestClient(app)

    print("\n[Privacy] 1. Testing Consent Gate Enforcement...")
    token_a, user_a_id = register_student(client, f"alice_privacy_{uid}@test.edu")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Attempt upload without consent -> HTTP 400
    pdf_path = os.path.join(FIXTURES_DIR, "clean_1page_resume.pdf")
    with open(pdf_path, "rb") as f:
        unconsented = client.post("/api/profile/resume", files={"file": ("clean_resume.pdf", f, "application/pdf")}, headers=headers_a)
    assert unconsented.status_code == 400
    assert "consent" in unconsented.text.lower()
    print("  ✓ Resume upload rejected without prior explicit consent (HTTP 400).")

    # Grant consent
    client.post("/api/profile/consent", json={"consent_given": True}, headers=headers_a)

    print("\n[Privacy] 2. Testing File Persistence and Physical Disk Storage...")
    with open(pdf_path, "rb") as f:
        upload_res = client.post("/api/profile/resume", files={"file": ("clean_resume.pdf", f, "application/pdf")}, headers=headers_a)
    assert upload_res.status_code == 200
    assert len(upload_res.json()["uploaded_files"]) >= 1

    # Verify physical file exists on disk
    files_on_disk = [f for f in os.listdir(UPLOAD_DIR) if f.startswith(f"{user_a_id}_")]
    assert len(files_on_disk) >= 1
    disk_file_path = os.path.join(UPLOAD_DIR, files_on_disk[0])
    assert os.path.exists(disk_file_path)
    print(f"  ✓ Uploaded resume verified on physical disk at: {os.path.basename(disk_file_path)}")

    print("\n[Privacy] 3. Testing 'Delete All My Data' Disk Unlinking...")
    del_res = client.delete("/api/profile/data", headers=headers_a)
    assert del_res.status_code == 200

    # DB profile reset
    me = client.get("/api/profile/me", headers=headers_a).json()
    assert me["parsed_resume"] == {}
    assert me["skills"] == []
    assert len(me["uploaded_files"]) == 0

    # Physical file on disk is deleted
    assert not os.path.exists(disk_file_path)
    residual_files = [f for f in os.listdir(UPLOAD_DIR) if f.startswith(f"{user_a_id}_")]
    assert len(residual_files) == 0
    print("  ✓ Physical file permanently removed from disk and database profile reset.")

    print("\n[Privacy] 4. Testing Account Deletion Cascading...")
    del_acc = client.delete("/api/profile/account", headers=headers_a)
    assert del_acc.status_code == 200
    # Authentication token is now invalid
    assert client.get("/api/profile/me", headers=headers_a).status_code in [401, 404]
    print("  ✓ Account deletion successfully invalidated auth and removed user records.")

    print("\n[Privacy] 5. Testing Tenant Isolation (Student A vs. Student B)...")
    token_1, id_1 = register_student(client, f"student_1_{uid}@test.edu")
    token_2, id_2 = register_student(client, f"student_2_{uid}@test.edu")
    headers_1 = {"Authorization": f"Bearer {token_1}"}
    headers_2 = {"Authorization": f"Bearer {token_2}"}

    client.post("/api/profile/consent", json={"consent_given": True}, headers=headers_1)
    client.post("/api/profile/consent", json={"consent_given": True}, headers=headers_2)

    # Student 2 attempts to read Student 1 profile
    cross_read = client.get(f"/api/profile/{id_1}", headers=headers_2)
    assert cross_read.status_code == 403
    print("  ✓ Tenant isolation verified: Student B cannot read Student A data (HTTP 403 Forbidden).")


if __name__ == "__main__":
    print("=" * 60)
    print(" Running Student Privacy, Data Wipe & Tenant Isolation Verification")
    print("=" * 60)
    test_privacy_lifecycle_and_tenant_isolation()
    print("\n[SUCCESS] All Privacy, Deletion, and Isolation tests PASSED!")
