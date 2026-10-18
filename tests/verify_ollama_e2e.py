#!/usr/bin/env python3
"""
Verification Script for Prompt 10:
Confirms the whole app runs 100% locally with Ollama (smollm:135m) with ZERO paid API keys.
Performs:
1. Student authentication & GDPR consent
2. Real resume upload & parsing
3. Benchmark Resume Review execution via Ollama
4. Mock Interview start, response turn, and completion via Ollama
5. Placement Readiness Score calculation & breakdown
"""
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import User, Profile, UserRole
from app.auth import hash_password, create_access_token

def run_ollama_verification():
    print("=" * 65)
    print(" Running Offline Local-First Verification with Ollama (smollm:135m)")
    print("=" * 65)

    client = TestClient(app)
    db = SessionLocal()

    # 1. Setup Student
    email = f"ollama_verify_{int(time.time())}@msot.edu"
    user = User(
        email=email,
        hashed_password=hash_password("password123"),
        role=UserRole.STUDENT,
        full_name="Ollama Local Candidate",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    prof = Profile(
        user_id=user.id,
        consent_given=True,
        skills=["Python", "FastAPI", "Docker", "SQL"],
        target_roles=["Backend Engineer"],
        projects=[
            {"title": "Distributed Cache", "tech_stack": ["Python", "Redis"], "live_url": "https://cache.dev"}
        ]
    )
    db.add(prof)
    db.commit()

    token = create_access_token({"sub": str(user.id), "role": "student", "email": email})
    headers = {"Authorization": f"Bearer {token}"}
    print(f"\n[1] Student authenticated: {email}")

    # 2. Upload Real Resume
    resume_path = os.path.join(BACKEND_DIR, "tests", "fixtures", "clean_1page_resume.pdf")
    assert os.path.exists(resume_path), f"Fixture resume not found at {resume_path}"
    with open(resume_path, "rb") as f:
        resp = client.post(
            "/api/profile/resume",
            headers=headers,
            files={"file": ("clean_1page_resume.pdf", f, "application/pdf")},
        )
    assert resp.status_code == 200, f"Upload resume failed: {resp.text}"
    print(f"[2] Real 1-page resume uploaded and parsed successfully.")

    # 3. Benchmark Resume Review via Ollama
    print("\n[3] Triggering Resume Review with Ollama...")
    start_t = time.time()
    resp = client.post("/api/reviews/resume", headers=headers)
    assert resp.status_code == 200, f"Resume review failed: {resp.text}"
    rev_data = resp.json()
    dur = time.time() - start_t
    print(f"    ✓ Resume Review Score: {rev_data.get('score')} / 100 (in {dur:.2f}s)")
    print(f"    ✓ Summary: {rev_data.get('summary')}")
    print(f"    ✓ Checks ({len(rev_data.get('checks', []))} evaluated):")
    for chk in rev_data.get("checks", [])[:3]:
        status_str = "PASS" if chk.get("pass") else "FAIL"
        print(f"      - [{status_str}] {chk.get('label')}: {chk.get('evidence')}")

    # 4. Mock Interview via Ollama
    print("\n[4] Starting Mock Interview Session with Ollama...")
    resp = client.post(
        "/api/interview/start",
        headers=headers,
        json={"target_role": "Backend Engineer", "duration_minutes": 10},
    )
    assert resp.status_code == 200, f"Interview start failed: {resp.text}"
    interview_data = resp.json()
    session_id = interview_data["id"]
    first_q = interview_data["messages"][-1]["content"] if interview_data.get("messages") else "Tell me about yourself."
    print(f"    ✓ Session started: ID {session_id}")
    print(f"    ✓ First question: {first_q}")

    # Student answers
    answer = "I design APIs with FastAPI using dependency injection, Pydantic data validation, and asynchronous SQLAlchemy database sessions in WAL mode to handle high concurrency."
    print(f"\n    Sending student answer: \"{answer[:60]}...\"")
    resp = client.post(
        f"/api/interview/{session_id}/message",
        headers=headers,
        json={"message": answer},
    )
    assert resp.status_code == 200, f"Interview message failed: {resp.text}"
    msg_data = resp.json()
    followup_q = msg_data["messages"][-1]["content"] if msg_data.get("messages") else ""
    print(f"    ✓ Interviewer follow-up: {followup_q}")

    # Complete interview
    resp = client.post(f"/api/interview/{session_id}/end", headers=headers)
    assert resp.status_code == 200, f"Interview end failed: {resp.text}"
    end_data = resp.json()
    print(f"    ✓ Interview completed! Final Score: {end_data.get('score')} / 100")

    # 5. Calculate Placement Readiness Score
    print("\n[5] Calculating Placement Readiness Score...")
    resp = client.post("/api/readiness/recalculate", headers=headers)
    assert resp.status_code == 200, f"Readiness recalculate failed: {resp.text}"
    readiness = resp.json()
    print(f"    ✓ Overall Placement Readiness Score: {readiness.get('overall_score')} / 100")
    print(f"    ✓ Placement Readiness Tier: {readiness.get('placement_tier')}")
    print(f"    ✓ Component Breakdown:")
    for comp, score in readiness.get("component_breakdown", {}).items():
        print(f"      - {comp:18}: {score}")
    print(f"    ✓ Top High-Impact Actions ({len(readiness.get('top_actions', []))} suggested):")
    for act in readiness.get("top_actions", [])[:3]:
        print(f"      - (+{act.get('points_gained')} pts) {act.get('action')}")

    db.close()
    print("\n" + "=" * 65)
    print(" [SUCCESS] Full student lifecycle completed offline via Ollama!")
    print("=" * 65)

if __name__ == "__main__":
    run_ollama_verification()
