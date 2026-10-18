#!/usr/bin/env python3
"""
Job Matching Relevance Verification Script:
Validates job discovery relevance, ranking accuracy across student profiles,
deduplication across multiple sources, and explicit match reasons.
Can be run directly (`python tests/test_job_matching.py`) or via pytest (`pytest tests/test_job_matching.py`).
"""
import os
import sys
import pytest

# Ensure backend root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.services.job_discovery.ranker import rank_jobs
from app.services.job_discovery.deduplicator import deduplicate_jobs

MOCK_JOB_CORPUS = [
    {"id": "j1", "title": "Senior Frontend Engineer", "company": "Vercel", "location": "Remote", "description": "React, Next.js, TypeScript architecture"},
    {"id": "j2", "title": "Frontend Developer Intern", "company": "Stripe", "location": "Bangalore", "description": "React, Tailwind CSS, JavaScript UI development"},
    {"id": "j3", "title": "Backend Python Engineer", "company": "Dropbox", "location": "Remote", "description": "Python, Django, FastAPI, PostgreSQL, Redis"},
    {"id": "j4", "title": "Junior Backend Developer", "company": "Razorpay", "location": "Bangalore", "description": "Python microservices, Docker, SQL queries"},
    {"id": "j5", "title": "Machine Learning Intern", "company": "OpenAI", "location": "Remote", "description": "PyTorch, Python, LLM evaluation, Pandas"},
    {"id": "j6", "title": "Data Scientist (NLP)", "company": "Hugging Face", "location": "Remote", "description": "Python, PyTorch, SQL, Transformers data analysis"},
    {"id": "j7", "title": "Corporate Accountant", "company": "KPMG", "location": "New York", "description": "Financial reporting, GAAP auditing"},
    {"id": "j8", "title": "Executive Assistant", "company": "Google", "location": "Mountain View", "description": "Calendar management, travel coordination"},
]


def test_frontend_profile_ranking():
    print("\n[Job Matching] Testing Frontend Profile Ranking...")
    skills = ["React", "Next.js", "TypeScript", "Tailwind CSS"]
    roles = ["Frontend Engineer", "Web Developer"]

    ranked = rank_jobs(jobs=MOCK_JOB_CORPUS, skills=skills, target_roles=roles, readiness_score=85, preferred_locations=["remote"])
    assert len(ranked) == len(MOCK_JOB_CORPUS)

    top_job = ranked[0]
    print(f"  Top Match for Frontend: {top_job['company']} - {top_job['title']} (Score: {top_job['match_score']}%)")
    assert "frontend" in top_job["title"].lower() or "react" in top_job["title"].lower()
    assert top_job["match_score"] > 60
    assert len(top_job["match_reasons"]) > 0
    assert any("skills" in r.lower() or "role" in r.lower() for r in top_job["match_reasons"])
    print("  ✓ Frontend profile ranked relevant UI/React jobs at the top.")


def test_backend_profile_ranking():
    print("\n[Job Matching] Testing Backend Profile Ranking...")
    skills = ["Python", "FastAPI", "PostgreSQL", "Docker"]
    roles = ["Backend Engineer", "Software Engineer"]

    ranked = rank_jobs(jobs=MOCK_JOB_CORPUS, skills=skills, target_roles=roles, readiness_score=78, preferred_locations=["bangalore", "remote"])
    top_job = ranked[0]
    print(f"  Top Match for Backend: {top_job['company']} - {top_job['title']} (Score: {top_job['match_score']}%)")
    assert "backend" in top_job["title"].lower() or "python" in top_job["title"].lower()
    assert "Python" in top_job["matched_skills"]
    print("  ✓ Backend profile ranked relevant Python/FastAPI jobs at the top.")


def test_data_science_profile_ranking():
    print("\n[Job Matching] Testing Data Science Profile Ranking...")
    skills = ["Python", "PyTorch", "SQL", "Pandas"]
    roles = ["Data Scientist", "Machine Learning Intern"]

    ranked = rank_jobs(jobs=MOCK_JOB_CORPUS, skills=skills, target_roles=roles, readiness_score=80, preferred_locations=["remote"])
    top_job = ranked[0]
    print(f"  Top Match for Data Science: {top_job['company']} - {top_job['title']} (Score: {top_job['match_score']}%)")
    assert "machine learning" in top_job["title"].lower() or "data" in top_job["title"].lower()
    assert "PyTorch" in top_job["matched_skills"]
    print("  ✓ Data Science profile ranked ML/Data jobs at the top.")


def test_cross_source_deduplication():
    print("\n[Job Matching] Testing Cross-Source Job Deduplication...")
    duplicate_jobs = [
        {"id": "gh_1", "company": "Stripe", "title": "Software Engineer", "url": "https://stripe.com/jobs/1", "source": "greenhouse"},
        {"id": "rss_2", "company": "Stripe", "title": "Software Engineer", "url": "https://weworkremotely.com/jobs/stripe-se", "source": "rss"},
        {"id": "lv_3", "company": "Vercel", "title": "Frontend Engineer", "url": "https://vercel.com/jobs/fe", "source": "lever"},
    ]
    deduped = deduplicate_jobs(duplicate_jobs)
    assert len(deduped) == 2, f"Expected 2 deduplicated jobs, got {len(deduped)}"
    stripe_job = next(j for j in deduped if j["company"] == "Stripe")
    assert len(stripe_job["sources"]) == 2
    assert "greenhouse" in stripe_job["sources"]
    assert "rss" in stripe_job["sources"]
    print("  ✓ Duplicate postings from Greenhouse and RSS correctly merged into single entry with multiple sources.")


if __name__ == "__main__":
    print("=" * 60)
    print(" Running Job Matching Relevance & Deduplication Verification")
    print("=" * 60)
    test_frontend_profile_ranking()
    test_backend_profile_ranking()
    test_data_science_profile_ranking()
    test_cross_source_deduplication()
    print("\n[SUCCESS] All Job Matching Relevance tests PASSED!")
