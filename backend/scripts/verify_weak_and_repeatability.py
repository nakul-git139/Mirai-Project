from __future__ import annotations
import os
import sys

# Ensure backend root in path
sys.path.insert(0, os.path.abspath("backend"))

from tests.create_fixtures import FIXTURES_DIR, generate_all_fixtures
from app.services.resume_reviewer import review_resume
from app.services.linkedin_reviewer import review_linkedin

def run_verification():
    generate_all_fixtures()

    # ==========================================
    # 1. RESUME BENCHMARK REVIEW (Strong vs Weak)
    # ==========================================
    good_path = os.path.join(FIXTURES_DIR, "resume_good.pdf")
    weak_path = os.path.join(FIXTURES_DIR, "resume_missing_links_typos.pdf")

    with open(good_path, "rb") as f:
        good_bytes = f.read()
    with open(weak_path, "rb") as f:
        weak_bytes = f.read()

    print("\n" + "=" * 70)
    print("1. RESUME REVIEW: STRONG VS WEAK (Typos, Missing Links, Weak Bullets)")
    print("=" * 70)

    # Single inspection of checks
    good_initial = review_resume(good_bytes, "resume_good.pdf")
    weak_initial = review_resume(weak_bytes, "resume_missing_links_typos.pdf")

    print(f"\nStrong Resume Initial Score: {good_initial['score']}/100")
    print("Strong Resume Checks:")
    for c in good_initial["checks"]:
        print(f"  [{c['id']}] {'PASS' if c['pass'] else 'FAIL'}: {c['label']} -> {c['evidence'][:70]}...")

    print(f"\nWeak Resume Initial Score: {weak_initial['score']}/100 (Difference: {weak_initial['score'] - good_initial['score']} pts)")
    print("Weak Resume Detected Planted Flaws:")
    for c in weak_initial["checks"]:
        if not c["pass"]:
            print(f"  FAIL [{c['id']}]: {c['label']}")
            print(f"       Evidence: {c['evidence']}")
            print(f"       Fix:      {c['fix']}")

    # 5 runs repeatability check
    good_resume_scores = []
    weak_resume_scores = []
    print("\nRunning 5 sequential evaluations on Strong Resume:")
    for i in range(1, 6):
        res = review_resume(good_bytes, "resume_good.pdf")
        good_resume_scores.append(res["score"])
        print(f"  Run {i}: Score = {res['score']}/100")

    print("\nRunning 5 sequential evaluations on Weak Resume:")
    for i in range(1, 6):
        res = review_resume(weak_bytes, "resume_missing_links_typos.pdf")
        weak_resume_scores.append(res["score"])
        print(f"  Run {i}: Score = {res['score']}/100")

    print(f"\nSummary Resume Scores: Strong={good_resume_scores}, Weak={weak_resume_scores}")
    assert all(s == good_resume_scores[0] for s in good_resume_scores), "Strong resume scores must be consistent"
    assert all(s == weak_resume_scores[0] for s in weak_resume_scores), "Weak resume scores must be consistent"
    assert good_resume_scores[0] > weak_resume_scores[0], "Strong resume must score clearly higher than weak resume"

    # ==========================================
    # 2. LINKEDIN BENCHMARK REVIEW (Strong vs Weak)
    # ==========================================
    strong_txt_path = os.path.join(FIXTURES_DIR, "linkedin_strong.txt")
    weak_txt_path = os.path.join(FIXTURES_DIR, "linkedin_weak.txt")

    with open(strong_txt_path, "r", encoding="utf-8") as f:
        strong_li_text = f.read()
    with open(weak_txt_path, "r", encoding="utf-8") as f:
        weak_li_text = f.read()

    verified_context = {
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

    print("\n" + "=" * 70)
    print("2. LINKEDIN REVIEW: STRONG VS WEAK (Generic Headline, Short About, 2 Skills)")
    print("=" * 70)

    strong_li_initial = review_linkedin(text=strong_li_text, resume_context=verified_context)
    weak_li_initial = review_linkedin(text=weak_li_text, resume_context=verified_context)

    print(f"\nStrong LinkedIn Initial Score: {strong_li_initial['score']}/100")
    print("Strong LinkedIn Checks:")
    for c in strong_li_initial["checks"]:
        print(f"  [{c['id']}] {'PASS' if c['pass'] else 'FAIL'}: {c['label']}")

    print(f"\nWeak LinkedIn Initial Score: {weak_li_initial['score']}/100 (Difference: {weak_li_initial['score'] - strong_li_initial['score']} pts)")
    print("Weak LinkedIn Detected Flaws:")
    for c in weak_li_initial["checks"]:
        if not c["pass"]:
            print(f"  FAIL [{c['id']}]: {c['label']}")
            print(f"       Evidence: {c['evidence']}")
            print(f"       Fix:      {c['fix']}")

    # 5 runs repeatability check
    strong_li_scores = []
    weak_li_scores = []
    print("\nRunning 5 sequential evaluations on Strong LinkedIn Profile:")
    for i in range(1, 6):
        res = review_linkedin(text=strong_li_text, resume_context=verified_context)
        strong_li_scores.append(res["score"])
        print(f"  Run {i}: Score = {res['score']}/100")

    print("\nRunning 5 sequential evaluations on Weak LinkedIn Profile:")
    for i in range(1, 6):
        res = review_linkedin(text=weak_li_text, resume_context=verified_context)
        weak_li_scores.append(res["score"])
        print(f"  Run {i}: Score = {res['score']}/100")

    print(f"\nSummary LinkedIn Scores: Strong={strong_li_scores}, Weak={weak_li_scores}")
    assert all(s == strong_li_scores[0] for s in strong_li_scores), "Strong LinkedIn scores must be consistent"
    assert all(s == weak_li_scores[0] for s in weak_li_scores), "Weak LinkedIn scores must be consistent"
    assert strong_li_scores[0] > weak_li_scores[0], "Strong LinkedIn must score clearly higher than weak profile"

if __name__ == "__main__":
    run_verification()
