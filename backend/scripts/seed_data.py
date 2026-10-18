#!/usr/bin/env python3
"""
Seed Script: Populates database with demo users, admin, and 5 diverse sample student reports.
Provides realistic profiles across all three placement readiness tiers:
1. Placement Ready (75 - 100): Ananya Sharma (88), Rohan Patel (78)
2. Almost Ready (50 - 74): Priya Nair (68), Vikram Verma (58)
3. Not Ready (0 - 49): Sneha Reddy (38)
Includes pre-computed reviews, mock interview transcripts, readiness snapshots, applications, and MSOT jobs.
"""
import os
import sys
from datetime import datetime, timedelta

# Ensure backend root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.database import engine, SessionLocal, Base
from app.models import (
    User,
    UserRole,
    Profile,
    ReviewResult,
    InterviewSession,
    ReadinessScore,
    Job,
    Application,
    ApplicationStatus,
)
from app.auth import hash_password


def _get_or_create_job(db, company, role, link=None, admin_id=None):
    job = db.query(Job).filter(Job.company == company, Job.title == role).first()
    if not job:
        job = Job(
            company=company,
            title=role,
            description=f"{role} position at {company}.",
            url=link or f"https://careers.{company.lower().replace(' ', '')}.com",
            location="Remote / Hybrid",
            job_type="job",
            is_pinned=False,
            posted_by=admin_id,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
    return job


def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        print("=" * 65)
        print(" Seeding Placement Readiness Copilot Demo & Benchmark Accounts")
        print("=" * 65)

        # ---------------------------------------------------------
        # 1. Admin Account
        # ---------------------------------------------------------
        admin_email = "admin@msot.edu"
        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            admin = User(
                email=admin_email,
                hashed_password=hash_password("admin123"),
                role=UserRole.ADMIN,
                full_name="Prof. David Vance (MSOT Placement Director)",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"  [+] Created Admin: {admin.email} (Password: admin123)")
        else:
            print(f"  [·] Admin exists: {admin.email}")

        # ---------------------------------------------------------
        # 2. Institutional MSOT Campus Jobs
        # ---------------------------------------------------------
        existing_jobs = db.query(Job).filter(Job.posted_by == admin.id).all()
        if not existing_jobs:
            jobs_data = [
                {
                    "title": "Campus Frontend Associate",
                    "company": "MSOT Strategic Partner Corp",
                    "description": "Fellowship program for high-readiness frontend candidates. Build high-scale React & Next.js systems.",
                    "requirements": "React & TypeScript proficiency, component design, state management.",
                    "location": "Bangalore / Hybrid",
                    "url": "https://careers.partnercorp.dev/campus-2026",
                    "job_type": "job",
                    "is_pinned": True,
                    "eligibility_criteria": {
                        "min_readiness_score": 75,
                        "required_skills": ["React", "TypeScript"],
                        "target_roles": ["Frontend Engineer", "Full Stack Developer"],
                    },
                },
                {
                    "title": "Cloud Systems Apprentice",
                    "company": "Nexus Cloud Labs",
                    "description": "Distributed infrastructure engineering fellowship working on Kubernetes, microservices, and observability.",
                    "requirements": "Hands-on Python or Go, Docker containers, REST/gRPC API experience.",
                    "location": "Remote / Hyderabad",
                    "url": "https://nexuscloud.dev/careers/apprentice",
                    "job_type": "job",
                    "is_pinned": True,
                    "eligibility_criteria": {
                        "min_readiness_score": 70,
                        "required_skills": ["Python", "Docker"],
                        "target_roles": ["Backend Engineer", "Cloud Engineer", "DevOps Engineer"],
                    },
                },
                {
                    "title": "Junior Software Engineer",
                    "company": "FinTech Global Solutions",
                    "description": "Campus recruitment for software engineers. Open to high-potential candidates across tech stacks.",
                    "requirements": "Solid algorithmic foundations, OOP concepts, collaborative communication.",
                    "location": "Mumbai / Onsite",
                    "url": "https://fintechglobal.com/careers/junior-se",
                    "job_type": "job",
                    "is_pinned": False,
                    "eligibility_criteria": {
                        "min_readiness_score": 50,
                        "required_skills": ["Python", "SQL"],
                        "target_roles": ["Software Engineer", "Junior Developer"],
                    },
                },
            ]
            created_jobs = []
            for jd in jobs_data:
                j = Job(posted_by=admin.id, **jd)
                db.add(j)
                created_jobs.append(j)
            db.commit()
            print(f"  [+] Created {len(created_jobs)} MSOT campus job postings with eligibility gating.")

        # ---------------------------------------------------------
        # 3. Main Demo Student
        # ---------------------------------------------------------
        demo_student_email = "student@msot.edu"
        demo_student = db.query(User).filter(User.email == demo_student_email).first()
        if demo_student:
            demo_student.hashed_password = hash_password("student123")
            db.commit()
            print(f"  [·] Demo Student password updated to student123: {demo_student.email}")
        if not demo_student:
            demo_student = User(
                email=demo_student_email,
                hashed_password=hash_password("student123"),
                role=UserRole.STUDENT,
                full_name="Alex Rivera",
                is_active=True,
            )
            db.add(demo_student)
            db.commit()
            db.refresh(demo_student)

            profile = Profile(
                user_id=demo_student.id,
                consent_given=True,
                consent_date=datetime.utcnow() - timedelta(days=14),
                headline="Full Stack Engineer | React, FastAPI & Cloud Microservices",
                bio="MSOT Computer Science student focused on distributed web architectures, high-performance APIs, and clean code.",
                target_roles=["Full Stack Developer", "Backend Engineer", "Software Engineer"],
                skills=["React", "FastAPI", "Python", "TypeScript", "PostgreSQL", "Docker", "Tailwind CSS"],
                linkedin_url="https://linkedin.com/in/alex-rivera-msot",
                github_url="https://github.com/alexrivera-dev",
                leetcode_url="https://leetcode.com/u/alex_algos",
                github_username="alexrivera-dev",
                leetcode_username="alex_algos",
                projects=[
                    {
                        "name": "Placement Readiness Copilot",
                        "title": "Placement Readiness Copilot",
                        "description": "Deterministic benchmark review engine and mock interview copilot for students.",
                        "tech_stack": ["FastAPI", "React", "SQLite", "Playwright"],
                        "github_url": "https://github.com/alexrivera-dev/placement-copilot",
                        "live_url": "https://placement-copilot.demo.dev",
                    },
                    {
                        "name": "Distributed Task Queue",
                        "title": "Distributed Task Queue",
                        "description": "High-throughput asynchronous task orchestrator with Redis and FastAPI.",
                        "tech_stack": ["Python", "Redis", "Docker"],
                        "github_url": "https://github.com/alexrivera-dev/task-queue",
                        "live_url": "https://task-queue.demo.dev",
                    },
                ],
                achievements=[
                    {"title": "1st Place - Smart Campus Hackathon 2025", "category": "hackathon"},
                    {"title": "AWS Certified Cloud Practitioner", "category": "certification"},
                ],
            )
            db.add(profile)

            # Reviews
            db.add(ReviewResult(
                user_id=demo_student.id,
                review_type="resume",
                score=85,
                summary="Strong 1-page resume with quantified impact and clear technical skill layout.",
                checks=[
                    {"id": "CHK-PAGE-COUNT", "label": "Single-Page Format", "pass": True, "evidence": "1 page", "fix": ""},
                    {"id": "CHK-ATS-FRIENDLY", "label": "ATS-Friendly Layout", "pass": True, "evidence": "Standard headings found", "fix": ""},
                    {"id": "CHK-ACTION-RESULTS", "label": "Action-Result Bullets", "pass": True, "evidence": "Bullets include action verbs and metrics", "fix": ""},
                ],
            ))
            db.add(ReviewResult(
                user_id=demo_student.id,
                review_type="linkedin",
                score=80,
                summary="Recruiter-ready LinkedIn profile with matching technical experience and clear target role focus.",
                checks=[
                    {"id": "CHK-LI-HEADLINE", "label": "Specific Headline", "pass": True, "evidence": "Within 220 chars", "fix": ""},
                    {"id": "CHK-LI-ABOUT", "label": "Substantive About", "pass": True, "evidence": "180 words", "fix": ""},
                ],
            ))
            db.add(ReviewResult(
                user_id=demo_student.id,
                review_type="github",
                score=80,
                summary="Active public repository with clear README instructions, zero secret leaks, and verified live link.",
                checks=[
                    {"id": "CHK-GH-NO-SECRETS", "label": "Zero Leaked Secrets", "pass": True, "evidence": "0 findings", "fix": ""},
                    {"id": "CHK-LIVE-LOAD-STATUS", "label": "Live Link Loaded", "pass": True, "evidence": "HTTP 200", "fix": ""},
                ],
            ))

            # Interview session
            db.add(InterviewSession(
                user_id=demo_student.id,
                target_role="Full Stack Developer",
                duration_minutes=15,
                time_limit_seconds=900,
                status="completed",
                score=78,
                feedback={
                    "strengths": ["Clear communication", "Solid architectural trade-off discussion"],
                    "weaknesses": ["Could elaborate more on edge case database failures"],
                    "tips": ["Practice explaining CAP theorem trade-offs concisely"],
                },
                messages=[
                    {"role": "interviewer", "content": "Tell me about your distributed task queue project."},
                    {"role": "student", "content": "I built it to process background image conversion jobs using Redis queues and Python workers..."},
                ],
            ))

            # Progression history
            now = datetime.utcnow()
            snapshots = [
                (now - timedelta(days=12), 48, "Initial profile setup"),
                (now - timedelta(days=8), 62, "Resume & LinkedIn reviews completed"),
                (now - timedelta(days=4), 71, "GitHub live link verified"),
                (now - timedelta(days=1), 78, "Mock interview completed"),
            ]
            for ts, score_val, reason in snapshots:
                db.add(ReadinessScore(
                    user_id=demo_student.id,
                    overall_score=score_val,
                    breakdown={
                        "resume": min(100, score_val + 5),
                        "projects": score_val,
                        "mock_interview": 78 if score_val >= 78 else 0,
                        "github": 80 if score_val >= 70 else 0,
                        "coding_practice": 70,
                        "linkedin": 80,
                        "cocurricular": 70,
                    },
                    created_at=ts,
                ))

            # Tracked applications
            j1 = _get_or_create_job(db, "MSOT Strategic Partner Corp", "Campus Frontend Associate", "https://careers.partnercorp.dev/campus-2026", admin.id)
            j2 = _get_or_create_job(db, "Nexus Cloud Labs", "Cloud Systems Apprentice", "https://nexuscloud.dev/careers/apprentice", admin.id)
            db.add(Application(
                user_id=demo_student.id,
                job_id=j1.id,
                company="MSOT Strategic Partner Corp",
                role="Campus Frontend Associate",
                link="https://careers.partnercorp.dev/campus-2026",
                status="Interview",
                notes="Passed initial resume screen. Technical round scheduled for Thursday.",
                last_status_change_at=now - timedelta(days=2),
                status_history=[
                    {"status": "Applied", "changed_at": (now - timedelta(days=5)).isoformat(), "note": "Applied via MSOT portal"},
                    {"status": "Interview", "changed_at": (now - timedelta(days=2)).isoformat(), "note": "Invited for Technical Round 1"},
                ],
            ))
            db.add(Application(
                user_id=demo_student.id,
                job_id=j2.id,
                company="Nexus Cloud Labs",
                role="Cloud Systems Apprentice",
                link="https://nexuscloud.dev/careers/apprentice",
                status="Applied",
                notes="Submitted portfolio project links and system architecture writeup.",
                last_status_change_at=now - timedelta(days=3),
                status_history=[
                    {"status": "Applied", "changed_at": (now - timedelta(days=3)).isoformat(), "note": "Direct application submitted"},
                ],
            ))
            db.commit()
            print(f"  [+] Created Demo Student: {demo_student.email} (Password: student123, Score: 78 - Placement Ready)")
        else:
            print(f"  [·] Demo Student exists: {demo_student.email}")

        # ---------------------------------------------------------
        # 4. Five Diverse Sample Students (Tiers 1, 2, 3)
        # ---------------------------------------------------------
        sample_students_data = [
            # --- Tier 1: Placement Ready ---
            {
                "email": "ananya.sharma@msot.edu",
                "name": "Ananya Sharma",
                "tier": "Placement ready",
                "score": 88,
                "headline": "Cloud & Distributed Systems Specialist | Python, Go & Kubernetes",
                "target_roles": ["Backend Engineer", "Cloud Infrastructure Engineer"],
                "skills": ["Python", "Go", "Kubernetes", "Docker", "PostgreSQL", "FastAPI", "Redis"],
                "resume_score": 95,
                "linkedin_score": 90,
                "github_score": 85,
                "interview_score": 85,
                "projects": [
                    {"title": "High-Throughput API Gateway", "tech_stack": ["Go", "Redis", "Docker"], "live_url": "https://gateway.demo.io"},
                    {"title": "K8s Microservices Monitor", "tech_stack": ["Python", "Prometheus", "FastAPI"], "live_url": "https://monitor.demo.io"},
                ],
                "apps": [("Stripe", "Backend Engineer", "Interview"), ("Cloudflare", "Systems Engineer", "Applied")],
            },
            {
                "email": "rohan.patel@msot.edu",
                "name": "Rohan Patel",
                "tier": "Placement ready",
                "score": 78,
                "headline": "Frontend Engineer | React, Next.js & Modern UI Architectures",
                "target_roles": ["Frontend Engineer", "Web Developer"],
                "skills": ["React", "Next.js", "TypeScript", "Tailwind CSS", "Redux", "Jest"],
                "resume_score": 85,
                "linkedin_score": 75,
                "github_score": 80,
                "interview_score": 75,
                "projects": [
                    {"title": "Collaborative Design Canvas", "tech_stack": ["React", "HTML5 Canvas", "WebSockets"], "live_url": "https://canvas.demo.io"},
                    {"title": "E-Commerce Checkout Flow", "tech_stack": ["Next.js", "Stripe API", "Tailwind"], "live_url": "https://checkout.demo.io"},
                ],
                "apps": [("Vercel", "Frontend Developer", "Shortlisted"), ("Figma", "UI Engineer", "Saved")],
            },
            # --- Tier 2: Almost Ready ---
            {
                "email": "priya.nair@msot.edu",
                "name": "Priya Nair",
                "tier": "Almost ready",
                "score": 68,
                "headline": "Aspiring Data Scientist & ML Engineer | Python, PyTorch & SQL",
                "target_roles": ["Data Scientist", "Machine Learning Intern"],
                "skills": ["Python", "PyTorch", "Pandas", "Scikit-Learn", "SQL", "FastAPI"],
                "resume_score": 75,
                "linkedin_score": 60,
                "github_score": 70,
                "interview_score": 65,
                "projects": [
                    {"title": "Customer Churn Prediction", "tech_stack": ["Python", "Scikit-Learn", "FastAPI"], "live_url": "https://churn.demo.io"},
                    {"title": "NLP Sentiment Classifier", "tech_stack": ["PyTorch", "HuggingFace"], "live_url": "https://sentiment.demo.io"},
                ],
                "apps": [("OpenAI", "ML Intern", "Applied"), ("Hugging Face", "Data Science Fellow", "Saved")],
            },
            {
                "email": "vikram.verma@msot.edu",
                "name": "Vikram Verma",
                "tier": "Almost ready",
                "score": 58,
                "headline": "DevOps & Infrastructure Engineer | Linux, Terraform & CI/CD",
                "target_roles": ["DevOps Engineer", "Site Reliability Engineer"],
                "skills": ["Linux", "Docker", "Terraform", "GitHub Actions", "Python", "Bash"],
                "resume_score": 65,
                "linkedin_score": 50,
                "github_score": 85,
                "interview_score": None,  # Missing Mock Interview! Unlocks +20 pts!
                "projects": [
                    {"title": "Automated Multi-Cloud Deployer", "tech_stack": ["Terraform", "GitHub Actions"], "live_url": "https://deployer.demo.io"},
                ],
                "apps": [("Datadog", "SRE Intern", "Applied")],
            },
            # --- Tier 3: Not Ready ---
            {
                "email": "sneha.reddy@msot.edu",
                "name": "Sneha Reddy",
                "tier": "Not ready",
                "score": 38,
                "headline": "Student at MSOT | Interested in Web Development",
                "target_roles": ["Software Engineer Intern"],
                "skills": ["HTML", "CSS", "JavaScript", "Python"],
                "resume_score": 45,  # 2-page resume flaw, missing metrics
                "linkedin_score": 35,  # short about, generic headline
                "github_score": 40,  # 1 repo, missing README
                "interview_score": None,  # Missing
                "projects": [
                    {"title": "Personal Portfolio", "tech_stack": ["HTML", "CSS"], "live_url": "https://portfolio.demo.io"},
                ],
                "apps": [("TechStart Solutions", "Software Intern", "Saved")],
            },
        ]

        print("\n  Seeding 5 Diverse Sample Student Profiles Across Placement Tiers:")
        print("  " + "-" * 60)
        for sdata in sample_students_data:
            existing_user = db.query(User).filter(User.email == sdata["email"]).first()
            if existing_user:
                print(f"  [·] Sample student exists: {sdata['email']}")
                continue

            user = User(
                email=sdata["email"],
                hashed_password=hash_password("student123"),
                role=UserRole.STUDENT,
                full_name=sdata["name"],
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            prof = Profile(
                user_id=user.id,
                consent_given=True,
                consent_date=datetime.utcnow() - timedelta(days=20),
                headline=sdata["headline"],
                bio=f"Placement candidate at MSOT targeting {', '.join(sdata['target_roles'])}.",
                target_roles=sdata["target_roles"],
                skills=sdata["skills"],
                linkedin_url=f"https://linkedin.com/in/{sdata['name'].lower().replace(' ', '-')}",
                github_url=f"https://github.com/{sdata['name'].lower().replace(' ', '')}",
                leetcode_url=f"https://leetcode.com/u/{sdata['name'].lower().replace(' ', '_')}",
                github_username=sdata["name"].lower().replace(' ', ''),
                leetcode_username=sdata["name"].lower().replace(' ', '_'),
                projects=sdata["projects"],
            )
            db.add(prof)

            # Add Reviews
            if sdata.get("resume_score") is not None:
                db.add(ReviewResult(
                    user_id=user.id,
                    review_type="resume",
                    score=sdata["resume_score"],
                    summary=f"Automated resume review for {sdata['name']}.",
                    checks=[
                        {"id": "CHK-PAGE-COUNT", "label": "Page Count", "pass": sdata["resume_score"] > 60, "evidence": "Evaluated", "fix": ""},
                        {"id": "CHK-ACTION-RESULTS", "label": "Action-Result Bullets", "pass": sdata["resume_score"] > 70, "evidence": "Metrics checked", "fix": ""},
                    ],
                ))

            if sdata.get("linkedin_score") is not None:
                db.add(ReviewResult(
                    user_id=user.id,
                    review_type="linkedin",
                    score=sdata["linkedin_score"],
                    summary=f"Automated LinkedIn profile audit for {sdata['name']}.",
                    checks=[{"id": "CHK-LI-HEADLINE", "label": "Headline", "pass": sdata["linkedin_score"] > 50, "evidence": "Checked", "fix": ""}],
                ))

            if sdata.get("github_score") is not None:
                db.add(ReviewResult(
                    user_id=user.id,
                    review_type="github",
                    score=sdata["github_score"],
                    summary=f"Automated GitHub & live link audit for {sdata['name']}.",
                    checks=[{"id": "CHK-GH-NO-SECRETS", "label": "Secrets", "pass": True, "evidence": "No secrets found", "fix": ""}],
                ))

            if sdata.get("interview_score") is not None:
                db.add(InterviewSession(
                    user_id=user.id,
                    target_role=sdata["target_roles"][0],
                    duration_minutes=15,
                    time_limit_seconds=900,
                    status="completed",
                    score=sdata["interview_score"],
                    feedback={"strengths": ["Consistent answers"], "weaknesses": ["Pacing"], "tips": ["Keep practice up"]},
                    messages=[{"role": "interviewer", "content": "Welcome to your mock interview."}],
                ))

            # Readiness Score Snapshots
            now = datetime.utcnow()
            score_val = sdata["score"]
            db.add(ReadinessScore(
                user_id=user.id,
                overall_score=score_val,
                breakdown={
                    "resume": sdata.get("resume_score", 0),
                    "projects": min(100, score_val + 2),
                    "mock_interview": sdata.get("interview_score", 0),
                    "github": sdata.get("github_score", 0),
                    "coding_practice": min(100, score_val - 5),
                    "linkedin": sdata.get("linkedin_score", 0),
                    "cocurricular": 60,
                },
                created_at=now,
            ))

            # Applications
            for company, role, status in sdata["apps"]:
                j = _get_or_create_job(db, company, role, admin_id=admin.id)
                db.add(Application(
                    user_id=user.id,
                    job_id=j.id,
                    company=company,
                    role=role,
                    link=j.url,
                    status=status,
                    notes=f"Tracked opportunity for {sdata['name']}.",
                    last_status_change_at=now - timedelta(days=1),
                    status_history=[{"status": status, "changed_at": now.isoformat(), "note": "Initial application"}],
                ))

            db.commit()
            print(f"  [+] {sdata['name']:<16} | Tier: {sdata['tier']:<16} | Score: {sdata['score']:<3}/100 | Email: {sdata['email']}")

        print("  " + "-" * 60)
        print("\n[SUCCESS] Database seeded successfully!")
        print("Demo Credentials:")
        print("  • Admin:   admin@msot.edu   / admin123")
        print("  • Student: student@msot.edu / student123")
        print("=" * 65 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
