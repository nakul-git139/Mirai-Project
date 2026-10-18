from __future__ import annotations
import pytest
from fastapi.testclient import TestClient
from app.models import UserRole


def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "Placement Readiness Copilot" in data["app"]


def test_student_registration_and_login(client: TestClient):
    # Register student
    reg_payload = {
        "email": "new_student@mirai.dev",
        "password": "strongpassword123",
        "role": "student",
        "full_name": "New Student",
    }
    reg_res = client.post("/api/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    user_data = reg_res.json()
    assert user_data["email"] == "new_student@mirai.dev"
    assert user_data["role"] == "student"

    # Login
    login_payload = {
        "email": "new_student@mirai.dev",
        "password": "strongpassword123",
    }
    login_res = client.post("/api/auth/login", json=login_payload)
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["role"] == "student"


def test_admin_registration_and_login(client: TestClient):
    reg_payload = {
        "email": "staff_admin@mirai.dev",
        "password": "adminpassword123",
        "role": "admin",
        "full_name": "MSOT Staff",
    }
    reg_res = client.post("/api/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    assert reg_res.json()["role"] == "admin"

    login_res = client.post(
        "/api/auth/login",
        json={"email": "staff_admin@mirai.dev", "password": "adminpassword123"},
    )
    assert login_res.status_code == 200
    assert login_res.json()["role"] == "admin"


def test_duplicate_registration_fails(client: TestClient):
    payload = {
        "email": "duplicate@mirai.dev",
        "password": "password123",
        "role": "student",
    }
    res1 = client.post("/api/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


def test_student_token_rejected_on_admin_route(
    client: TestClient,
    student_auth_headers: dict,
    admin_auth_headers: dict,
):
    """
    CRITICAL VERIFICATION:
    Confirm a student token is rejected on an admin-only route with 403 Forbidden.
    """
    # Student attempts to access admin jobs
    res_student = client.get("/api/admin/jobs", headers=student_auth_headers)
    assert res_student.status_code == 403
    assert "Admin privileges required" in res_student.json()["detail"]

    # Admin attempts to access admin jobs -> succeeds
    res_admin = client.get("/api/admin/jobs", headers=admin_auth_headers)
    assert res_admin.status_code == 200
    assert isinstance(res_admin.json(), list)


def test_admin_can_post_job(
    client: TestClient,
    student_auth_headers: dict,
    admin_auth_headers: dict,
):
    job_payload = {
        "title": "Junior Full Stack Engineer",
        "company": "Mirai Tech",
        "description": "Exciting role for MSOT graduates",
        "requirements": "React, FastAPI, SQL",
        "location": "Remote",
    }

    # Student cannot post job
    res_student = client.post("/api/admin/jobs", json=job_payload, headers=student_auth_headers)
    assert res_student.status_code == 403

    # Admin posts job
    res_admin = client.post("/api/admin/jobs", json=job_payload, headers=admin_auth_headers)
    assert res_admin.status_code == 201
    data = res_admin.json()
    assert data["title"] == "Junior Full Stack Engineer"
    assert data["company"] == "Mirai Tech"
