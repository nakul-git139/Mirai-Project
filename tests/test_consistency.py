#!/usr/bin/env python3
"""
Consistency Test Script:
Runs 5-iteration benchmark reviews on Resume and LinkedIn fixtures.
Verifies that score variation across repeated runs is within ±3 points (target: 0 variance).
Can be run directly (`python tests/test_consistency.py`) or with pytest (`pytest tests/test_consistency.py`).
"""
import os
import sys

# Ensure backend root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.services.resume_reviewer import review_resume
from app.services.linkedin_reviewer import review_linkedin

FIXTURES_DIR = os.path.join(BACKEND_DIR, "tests", "fixtures")


def run_resume_consistency(iterations=5):
    resume_path = os.path.join(FIXTURES_DIR, "resume_good.pdf")
    if not os.path.exists(resume_path):
        resume_path = os.path.join(FIXTURES_DIR, "clean_1page_resume.pdf")

    with open(resume_path, "rb") as f:
        file_bytes = f.read()

    filename = os.path.basename(resume_path)
    scores = []
    print(f"\n[Consistency] Evaluating {filename} across {iterations} runs...")
    for i in range(1, iterations + 1):
        res = review_resume(file_bytes, filename)
        score = res["score"]
        scores.append(score)
        print(f"  Run {i}/{iterations}: Score = {score}/100")

    min_s, max_s = min(scores), max(scores)
    delta = max_s - min_s
    print(f"[Consistency] Resume Scores: {scores} (Min: {min_s}, Max: {max_s}, Delta: {delta})")
    assert delta <= 3, f"Resume score delta {delta} exceeds ±3 benchmark limit!"
    return scores, delta


def run_linkedin_consistency(iterations=5):
    txt_path = os.path.join(FIXTURES_DIR, "linkedin_strong.txt")
    with open(txt_path, "r", encoding="utf-8") as f:
        text_content = f.read()

    resume_context = {
        "skills": ["Python", "FastAPI", "React", "TypeScript", "PostgreSQL", "Docker"],
        "experience": [{"title": "Full Stack Engineer", "company": "Acme Cloud Solutions"}],
        "projects": [{"name": "Readiness Copilot"}],
        "target_roles": ["Software Engineer", "Full Stack Engineer"],
    }
    scores = []
    print(f"\n[Consistency] Evaluating linkedin_strong across {iterations} runs...")
    for i in range(1, iterations + 1):
        res = review_linkedin(text=text_content, resume_context=resume_context)
        score = res["score"]
        scores.append(score)
        print(f"  Run {i}/{iterations}: Score = {score}/100")

    min_s, max_s = min(scores), max(scores)
    delta = max_s - min_s
    print(f"[Consistency] LinkedIn Scores: {scores} (Min: {min_s}, Max: {max_s}, Delta: {delta})")
    assert delta <= 3, f"LinkedIn score delta {delta} exceeds ±3 benchmark limit!"
    return scores, delta


def test_resume_consistency_5_runs():
    scores, delta = run_resume_consistency(5)
    assert delta <= 3


def test_linkedin_consistency_5_runs():
    scores, delta = run_linkedin_consistency(5)
    assert delta <= 3


if __name__ == "__main__":
    print("=" * 60)
    print(" Running Benchmark Consistency Verification (±3 Points Limit)")
    print("=" * 60)
    run_resume_consistency(5)
    run_linkedin_consistency(5)
    print("\n[SUCCESS] All consistency checks PASSED with delta <= 3 points!")
