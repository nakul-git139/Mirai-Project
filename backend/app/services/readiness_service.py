from __future__ import annotations
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models import ReadinessScore, ReviewResult, InterviewSession, Profile, User
from app.schemas import (
    ComponentBreakdown,
    ActionItem,
    ReadinessResponse,
    ReadinessHistoryItem,
)

logger = logging.getLogger(__name__)

# Canonical Placement Readiness Weights (sum = 100)
WEIGHTS: Dict[str, int] = {
    "resume": 25,
    "projects": 25,
    "mock_interview": 20,
    "github": 10,
    "coding_practice": 10,
    "linkedin": 5,
    "co_curricular": 5,
}

COMPONENT_DISPLAY_NAMES: Dict[str, str] = {
    "resume": "Resume",
    "projects": "Projects",
    "mock_interview": "Mock Interview",
    "github": "GitHub Presence",
    "coding_practice": "Coding Practice",
    "linkedin": "LinkedIn Profile",
    "co_curricular": "Co-curricular Achievements",
}

# Resume rubric check point values (out of 100)
RESUME_CHECK_POINTS: Dict[str, int] = {
    "CHK-PAGE-COUNT": 15,
    "CHK-LAYOUT-CLEAN": 10,
    "CHK-SPELLING-GRAMMAR": 10,
    "CHK-PROJECT-DETAILS": 15,
    "CHK-PROFILE-LINKS": 10,
    "CHK-ACHIEVEMENTS": 10,
    "CHK-ACTION-VERBS": 15,
    "CHK-ATS-FRIENDLY": 15,
}

# LinkedIn rubric check point values (out of 100)
LINKEDIN_CHECK_POINTS: Dict[str, int] = {
    "CHK-LI-HEADLINE": 20,
    "CHK-LI-ABOUT": 20,
    "CHK-LI-SKILLS-ROLE": 20,
    "CHK-LI-RESUME-MATCH": 25,
    "CHK-LI-PHOTO": 15,
}

# GitHub rubric check point values (out of 100)
GITHUB_CHECK_POINTS: Dict[str, int] = {
    "CHK-GH-NO-SECRETS": 15,
    "CHK-GH-REPO-README": 10,
    "CHK-GH-TESTS-PRESENT": 10,
    "CHK-GH-CODE-REVIEW": 10,
    "CHK-GH-COMMIT-ACTIVITY": 10,
    "CHK-GH-PROFILE-README": 5,
    "CHK-GH-PINNED-REPOS": 5,
    "CHK-GH-FOLDER-STRUCTURE": 5,
    "CHK-GH-COMMIT-MESSAGES": 5,
}

# Mock Interview rubric check point values (out of 100)
INTERVIEW_CHECK_POINTS: Dict[str, int] = {
    "CHK-INT-TECH-DEPTH": 35,
    "CHK-INT-CLARITY": 25,
    "CHK-INT-EXPERIENCE": 25,
    "CHK-INT-CRITICAL-THINK": 15,
}



def get_placement_level(score: int) -> str:
    """
    Placement Readiness Levels:
      0 - 49:  Not ready
      50 - 74: Almost ready
      75 - 100: Placement ready
    """
    if score < 50:
        return "Not ready"
    elif score < 75:
        return "Almost ready"
    else:
        return "Placement ready"


def calculate_readiness_formula(
    component_inputs: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Pure deterministic formula calculator:
    Overall Score = round( sum( score_i * (weight_i / 100) ) )
    Handles missing components explicitly (score=None -> 0 earned points, status='missing').
    Generates and sorts Top 5 Action items by points gained in the overall score.
    """
    breakdown: Dict[str, ComponentBreakdown] = {}
    missing_components: List[str] = []
    completed_components: List[str] = []
    all_actions: List[ActionItem] = []

    raw_total = 0.0

    for key, weight in WEIGHTS.items():
        data = component_inputs.get(key, {})
        name = COMPONENT_DISPLAY_NAMES.get(key, key.capitalize())
        raw_score = data.get("score")
        summary = data.get("summary", "")
        checks = data.get("checks", [])

        if raw_score is None:
            # Explicit missing component handling
            missing_components.append(key)
            breakdown[key] = ComponentBreakdown(
                name=name,
                weight=weight,
                score=None,
                weighted_points=0.0,
                status="missing",
                failed_checks_count=0,
                summary=summary or f"{name} not completed or linked yet.",
            )

            # Create an action item for this missing component
            missing_action = _generate_missing_component_action(key, weight)
            if missing_action:
                all_actions.append(missing_action)
        else:
            completed_components.append(key)
            score_clamped = max(0.0, min(100.0, float(raw_score)))
            weighted_pts = round(score_clamped * (weight / 100.0), 2)
            raw_total += weighted_pts

            failed_checks = [c for c in checks if not c.get("pass", c.get("passed", True))]

            breakdown[key] = ComponentBreakdown(
                name=name,
                weight=weight,
                score=round(score_clamped, 1),
                weighted_points=weighted_pts,
                status="scored",
                failed_checks_count=len(failed_checks),
                summary=summary or f"{len(checks) - len(failed_checks)} of {len(checks)} checks passed.",
            )

            # Generate actionable items for each failed check
            for fc in failed_checks:
                action = _generate_check_action(key, weight, fc)
                if action:
                    all_actions.append(action)

    overall_score = max(0, min(100, int(round(raw_total))))
    level = get_placement_level(overall_score)

    # Sort actions descending by points_gained, break ties deterministically by ID
    all_actions.sort(key=lambda a: (a.points_gained, a.id), reverse=True)
    top_actions = all_actions[:5]

    return {
        "overall_score": overall_score,
        "raw_score": round(raw_total, 2),
        "level": level,
        "breakdown": breakdown,
        "missing_components": missing_components,
        "completed_components": completed_components,
        "top_actions": top_actions,
    }


def _generate_missing_component_action(component_key: str, weight: int) -> ActionItem:
    """Creates a high-priority action when an entire component is missing."""
    if component_key == "mock_interview":
        return ActionItem(
            id="ACT-MISSING-MOCK-INTERVIEW",
            component="Mock Interview",
            title="Complete your first technical mock interview session",
            evidence="No completed mock interview session found on file.",
            fix="Take an interactive technical & behavioral mock interview to establish your interview score and unlock up to 20 readiness points.",
            points_gained=float(weight),
            status="open",
        )
    elif component_key == "projects":
        return ActionItem(
            id="ACT-MISSING-PROJECTS",
            component="Projects",
            title="Add portfolio showcase projects with live links and repos",
            evidence="No technical projects found in profile or resume.",
            fix="Add at least 2 technical projects with public GitHub repositories, deployed live URLs, and declared tech stacks.",
            points_gained=float(weight),
            status="open",
        )
    elif component_key == "coding_practice":
        return ActionItem(
            id="ACT-MISSING-CODING-PRACTICE",
            component="Coding Practice",
            title="Link your LeetCode profile handle",
            evidence="LeetCode profile link not detected in contact header or profile.",
            fix="Add your LeetCode profile URL (e.g., https://leetcode.com/u/yourhandle) in Profile & My Data to verify problem-solving consistency.",
            points_gained=float(weight),
            status="open",
        )
    elif component_key == "linkedin":
        return ActionItem(
            id="ACT-MISSING-LINKEDIN",
            component="LinkedIn Profile",
            title="Run benchmark review on your LinkedIn profile",
            evidence="LinkedIn profile has not been reviewed yet.",
            fix="Paste your LinkedIn profile text or upload your profile PDF in Benchmark Reviews to evaluate recruiter visibility.",
            points_gained=float(weight),
            status="open",
        )
    elif component_key == "co_curricular":
        return ActionItem(
            id="ACT-MISSING-CO-CURRICULAR",
            component="Co-curricular Achievements",
            title="Add hackathons, certifications, or technical leadership",
            evidence="No co-curricular activities recorded in profile or resume.",
            fix="Add at least 1-2 hackathon projects, cloud certifications (AWS/GCP), or student club leadership roles to your profile.",
            points_gained=float(weight),
            status="open",
        )
    elif component_key == "github":
        return ActionItem(
            id="ACT-MISSING-GITHUB",
            component="GitHub Presence",
            title="Run automated review on your GitHub repository",
            evidence="GitHub repository review has not been completed yet.",
            fix="Provide your GitHub username and target repository in Benchmark Reviews to verify code cleanliness and live deployment.",
            points_gained=float(weight),
            status="open",
        )
    elif component_key == "resume":
        return ActionItem(
            id="ACT-MISSING-RESUME",
            component="Resume",
            title="Upload and review your 1-page technical resume",
            evidence="Resume has not been uploaded or reviewed yet.",
            fix="Upload your PDF or DOCX resume in Benchmark Reviews to evaluate against MSOT placement standards.",
            points_gained=float(weight),
            status="open",
        )
    return ActionItem(
        id=f"ACT-MISSING-{component_key.upper()}",
        component=COMPONENT_DISPLAY_NAMES.get(component_key, component_key),
        title=f"Complete {COMPONENT_DISPLAY_NAMES.get(component_key, component_key)} benchmark",
        evidence=f"{component_key} is unscored.",
        fix=f"Complete the {component_key} evaluation to gain up to {weight} points.",
        points_gained=float(weight),
        status="open",
    )


def _generate_check_action(
    component_key: str, weight: int, check_dict: Dict[str, Any]
) -> Optional[ActionItem]:
    """
    Computes exact points gained in overall score:
      points_gained = check_points_in_rubric * (weight / 100)
    """
    check_id = check_dict.get("id", "CHK-UNKNOWN")
    label = check_dict.get("label", check_id)
    fix = check_dict.get("fix", "Address this benchmark check to improve your score.")
    evidence = check_dict.get("evidence", "Check failed.")

    # Determine rubric points for this specific check
    rubric_points = 10  # default fallback
    if component_key == "resume":
        rubric_points = RESUME_CHECK_POINTS.get(check_id, 10)
    elif component_key == "linkedin":
        rubric_points = LINKEDIN_CHECK_POINTS.get(check_id, 20)
    elif component_key == "github":
        rubric_points = GITHUB_CHECK_POINTS.get(check_id, 10)
    elif component_key == "mock_interview":
        rubric_points = INTERVIEW_CHECK_POINTS.get(check_id, 25)
    elif component_key == "projects":
        rubric_points = 20

    # Overall score delta = rubric_points * (weight / 100)
    points_gained = round(rubric_points * (weight / 100.0), 2)

    return ActionItem(
        id=f"ACT-{check_id}",
        component=COMPONENT_DISPLAY_NAMES.get(component_key, component_key),
        title=f"Fix {label}",
        evidence=evidence,
        fix=fix,
        points_gained=points_gained,
        status="open",
    )


def evaluate_projects_component(profile: Optional[Profile]) -> Tuple[Optional[float], List[Dict[str, Any]], str]:
    """
    Evaluates student projects based on portfolio completeness.
    Rubric (5 checks, 20 pts each = 100 pts total):
      1. CHK-PROJ-COUNT: At least 2 projects (20 pts)
      2. CHK-PROJ-DESCRIPTION: Detailed descriptions for all projects (20 pts)
      3. CHK-PROJ-TECHSTACK: Tech stacks declared (20 pts)
      4. CHK-PROJ-LIVE-DEMO: Live deployment URLs present (20 pts)
      5. CHK-PROJ-REPO: GitHub repo links present (20 pts)
    """
    if not profile:
        return None, [], "Profile not found."

    projects = profile.projects or []
    if not projects and profile.parsed_resume:
        projects = profile.parsed_resume.get("projects", [])

    if not projects:
        return None, [], "No projects added to profile or resume yet."

    checks = []
    score = 0

    # 1. Count
    has_two = len(projects) >= 2
    if has_two:
        score += 20
        checks.append({
            "id": "CHK-PROJ-COUNT",
            "label": "Showcase Project Count",
            "pass": True,
            "evidence": f"Found {len(projects)} technical portfolio projects (minimum 2 required).",
            "fix": "Maintain at least 2 distinct showcase projects highlighting full-stack depth.",
        })
    else:
        checks.append({
            "id": "CHK-PROJ-COUNT",
            "label": "Showcase Project Count",
            "pass": False,
            "evidence": f"Only found {len(projects)} project. MSOT placement benchmark requires at least 2.",
            "fix": "Add a second technical project to your profile or resume with repository and live links.",
        })

    # 2. Descriptions
    all_have_desc = all(len(p.get("description", "").strip()) >= 25 for p in projects)
    if all_have_desc:
        score += 20
        checks.append({
            "id": "CHK-PROJ-DESCRIPTION",
            "label": "Substantive Descriptions",
            "pass": True,
            "evidence": "All projects include substantive descriptions exceeding 25 characters.",
            "fix": "Continue highlighting the specific problem solved and architecture in project descriptions.",
        })
    else:
        checks.append({
            "id": "CHK-PROJ-DESCRIPTION",
            "label": "Substantive Descriptions",
            "pass": False,
            "evidence": "One or more projects lack a detailed description (minimum 25 characters required).",
            "fix": "Expand project descriptions to explain the architectural challenge, stack, and measurable impact.",
        })

    # 3. Tech stack
    all_have_stack = all(
        (isinstance(p.get("tech_stack"), list) and len(p.get("tech_stack")) >= 2)
        or ("built with" in p.get("description", "").lower() or "tech stack" in p.get("description", "").lower())
        for p in projects
    )
    if all_have_stack:
        score += 20
        checks.append({
            "id": "CHK-PROJ-TECHSTACK",
            "label": "Declared Tech Stack",
            "pass": True,
            "evidence": "All projects specify their underlying technologies and frameworks.",
            "fix": "Keep tech stack lists up to date with modern libraries and databases.",
        })
    else:
        checks.append({
            "id": "CHK-PROJ-TECHSTACK",
            "label": "Declared Tech Stack",
            "pass": False,
            "evidence": "One or more projects do not declare their tech stack.",
            "fix": "Specify the exact technologies (e.g. React, FastAPI, PostgreSQL) used in each project.",
        })

    # 4. Live demo URL
    all_have_live = all(bool(p.get("live_url")) for p in projects)
    if all_have_live:
        score += 20
        checks.append({
            "id": "CHK-PROJ-LIVE-DEMO",
            "label": "Live Production Deployments",
            "pass": True,
            "evidence": "All portfolio projects include live deployment URLs.",
            "fix": "Ensure live URLs remain hosted and operational on Vercel, Netlify, or cloud platforms.",
        })
    else:
        checks.append({
            "id": "CHK-PROJ-LIVE-DEMO",
            "label": "Live Production Deployments",
            "pass": False,
            "evidence": "One or more projects are missing a deployed live demo URL.",
            "fix": "Deploy your projects to a free hosting tier (e.g., Vercel, Render) and add the live URL.",
        })

    # 5. Repo URL
    all_have_repo = all(bool(p.get("repo_url")) for p in projects)
    if all_have_repo:
        score += 20
        checks.append({
            "id": "CHK-PROJ-REPO",
            "label": "Public Code Repositories",
            "pass": True,
            "evidence": "All projects include public GitHub repository links.",
            "fix": "Maintain public access and clean commit histories on project repositories.",
        })
    else:
        checks.append({
            "id": "CHK-PROJ-REPO",
            "label": "Public Code Repositories",
            "pass": False,
            "evidence": "One or more projects do not link to a public repository.",
            "fix": "Add public GitHub repository URLs for all projects so recruiters can inspect your code.",
        })

    summary = f"{len([c for c in checks if c['pass']])} of 5 project quality benchmarks satisfied."
    return float(score), checks, summary


def evaluate_coding_practice_component(profile: Optional[Profile], db: Session) -> Tuple[Optional[float], List[Dict[str, Any]], str]:
    """
    Evaluates coding practice consistency:
    Looks for LeetCode reviews or stored LeetCode profile handle.
    """
    if not profile:
        return None, [], "Profile not found."

    # First check if there is an explicit review
    review = (
        db.query(ReviewResult)
        .filter(ReviewResult.user_id == profile.user_id, ReviewResult.review_type.in_(["leetcode", "coding"]))
        .order_by(ReviewResult.id.desc())
        .first()
    )
    if review:
        return float(review.score), review.checks or [], review.summary or "Coding practice review."

    # If profile has LeetCode username or URL
    has_handle = bool(profile.leetcode_username or profile.leetcode_url)
    if not has_handle:
        return None, [], "LeetCode profile handle not linked in profile or resume."

    # Linked handle grants baseline 80/100 points
    checks = [
        {
            "id": "CHK-LC-LINKED",
            "label": "Active LeetCode Profile",
            "pass": True,
            "evidence": f"Found linked LeetCode profile (@{profile.leetcode_username or 'user'}).",
            "fix": "Maintain regular problem-solving cadence (3-5 problems/week).",
        },
        {
            "id": "CHK-LC-PROBLEMS-TIER",
            "label": "100+ Solved Problems Target",
            "pass": False,
            "evidence": "Targeting 100+ solved problems across Medium and Hard data structures topics.",
            "fix": "Solve at least 50 LeetCode problems (30 Medium, 15 Easy, 5 Hard) to reach top placement tier.",
        }
    ]
    return 70.0, checks, f"LeetCode handle (@{profile.leetcode_username or 'user'}) verified."


def evaluate_cocurricular_component(profile: Optional[Profile], db: Session) -> Tuple[Optional[float], List[Dict[str, Any]], str]:
    """
    Evaluates co-curricular achievements, hackathons, and certifications.
    """
    if not profile:
        return None, [], "Profile not found."

    # Check for direct review
    review = (
        db.query(ReviewResult)
        .filter(ReviewResult.user_id == profile.user_id, ReviewResult.review_type == "achievements")
        .order_by(ReviewResult.id.desc())
        .first()
    )
    if review:
        return float(review.score), review.checks or [], review.summary or "Co-curricular review."

    achievements = profile.achievements or []
    if not achievements and profile.parsed_resume:
        achievements = profile.parsed_resume.get("certifications", [])

    if not achievements:
        return None, [], "No hackathons, certifications, or club leadership entries recorded."

    # Evaluate count and variety
    count = len(achievements)
    score = min(100.0, 50.0 + (count * 25.0))
    checks = [
        {
            "id": "CHK-ACH-RECORDED",
            "label": "Co-curricular Technical Engagement",
            "pass": True,
            "evidence": f"Recorded {count} co-curricular item(s) (hackathons, certifications, leadership).",
            "fix": "Highlight specific placements or leadership achievements in technical communities.",
        }
    ]
    if count < 2:
        checks.append({
            "id": "CHK-ACH-EXPAND",
            "label": "Multiple Co-curricular Initiatives",
            "pass": False,
            "evidence": "Only 1 co-curricular achievement on file. Recommended: 2+.",
            "fix": "Add a hackathon project, cloud certification, or student club leadership role.",
        })
    return score, checks, f"{count} co-curricular achievement(s) verified."


def gather_component_data(db: Session, user_id: int) -> Dict[str, Dict[str, Any]]:
    """Gathers raw score inputs for all 7 components from database records."""
    user = db.query(User).filter(User.id == user_id).first()
    profile = db.query(Profile).filter(Profile.user_id == user_id).first() if user else None

    # 1. Resume Review
    resume_review = (
        db.query(ReviewResult)
        .filter(ReviewResult.user_id == user_id, ReviewResult.review_type == "resume")
        .order_by(ReviewResult.id.desc())
        .first()
    )
    resume_data = {
        "score": float(resume_review.score) if resume_review else None,
        "checks": resume_review.checks if resume_review else [],
        "summary": resume_review.summary if resume_review else "Resume review not completed yet.",
    }

    # 2. Projects
    proj_review = (
        db.query(ReviewResult)
        .filter(ReviewResult.user_id == user_id, ReviewResult.review_type == "projects")
        .order_by(ReviewResult.id.desc())
        .first()
    )
    if proj_review:
        projects_data = {
            "score": float(proj_review.score),
            "checks": proj_review.checks or [],
            "summary": proj_review.summary or "Projects review.",
        }
    else:
        score_val, checks_list, summ = evaluate_projects_component(profile)
        projects_data = {
            "score": score_val,
            "checks": checks_list,
            "summary": summ,
        }

    # 3. Mock Interview
    interview_session = (
        db.query(InterviewSession)
        .filter(
            InterviewSession.user_id == user_id,
            InterviewSession.status == "completed",
            InterviewSession.score.isnot(None),
        )
        .order_by(InterviewSession.id.desc())
        .first()
    )
    if interview_session:
        int_checks = []
        fb = interview_session.feedback or {}
        rub_avg = fb.get("rubric_averages", {})
        
        td_score = rub_avg.get("CRIT-TECH-DEPTH", 0.0)
        td_pass = td_score >= 25.0
        int_checks.append({
            "id": "CHK-INT-TECH-DEPTH",
            "label": "Technical Accuracy & Depth",
            "pass": td_pass,
            "evidence": f"Technical depth evaluated ({td_score:.1f}/35.0 pts)." if rub_avg else f"Session score: {interview_session.score}/100.",
            "fix": "Deepen technical precision with specific architectures, frameworks, and mechanisms.",
        })
        
        cl_score = rub_avg.get("CRIT-CLARITY-COMM", 0.0)
        cl_pass = cl_score >= 18.0
        int_checks.append({
            "id": "CHK-INT-CLARITY",
            "label": "Communication & Structure",
            "pass": cl_pass,
            "evidence": f"Communication clarity evaluated ({cl_score:.1f}/25.0 pts)." if rub_avg else "Communication evaluated.",
            "fix": "Structure answers using the STAR method for behavioral and direct logic for technical questions.",
        })
        
        ge_score = rub_avg.get("CRIT-GROUNDED-EXP", 0.0)
        ge_pass = ge_score >= 18.0
        int_checks.append({
            "id": "CHK-INT-EXPERIENCE",
            "label": "Grounded Experience & Relevance",
            "pass": ge_pass,
            "evidence": f"Grounded experience evaluated ({ge_score:.1f}/25.0 pts)." if rub_avg else "Grounded experience evaluated.",
            "fix": "Reference concrete repository code, deployed tools, and quantifiable metrics from your projects.",
        })
        
        ct_score = rub_avg.get("CRIT-CRITICAL-THINK", 0.0)
        ct_pass = ct_score >= 10.0
        int_checks.append({
            "id": "CHK-INT-CRITICAL-THINK",
            "label": "Problem-Solving & Trade-offs",
            "pass": ct_pass,
            "evidence": f"Critical thinking evaluated ({ct_score:.1f}/15.0 pts)." if rub_avg else "Critical thinking evaluated.",
            "fix": "Proactively discuss trade-offs, rejected alternatives, and why you selected specific solutions.",
        })
        
        interview_data = {
            "score": float(interview_session.score),
            "checks": int_checks,
            "summary": f"Completed mock interview score: {interview_session.score}/100 ({sum(1 for c in int_checks if c['pass'])} of 4 criteria passed).",
        }
    else:
        interview_data = {
            "score": None,
            "checks": [],
            "summary": "Technical mock interview not taken yet.",
        }

    # 4. GitHub Review
    github_review = (
        db.query(ReviewResult)
        .filter(ReviewResult.user_id == user_id, ReviewResult.review_type == "github")
        .order_by(ReviewResult.id.desc())
        .first()
    )
    github_data = {
        "score": float(github_review.score) if github_review else None,
        "checks": github_review.checks if github_review else [],
        "summary": github_review.summary if github_review else "GitHub repository review not completed yet.",
    }

    # 5. Coding Practice (LeetCode)
    lc_score, lc_checks, lc_summary = evaluate_coding_practice_component(profile, db)
    coding_data = {
        "score": lc_score,
        "checks": lc_checks,
        "summary": lc_summary,
    }

    # 6. LinkedIn Review
    linkedin_review = (
        db.query(ReviewResult)
        .filter(ReviewResult.user_id == user_id, ReviewResult.review_type == "linkedin")
        .order_by(ReviewResult.id.desc())
        .first()
    )
    linkedin_data = {
        "score": float(linkedin_review.score) if linkedin_review else None,
        "checks": linkedin_review.checks if linkedin_review else [],
        "summary": linkedin_review.summary if linkedin_review else "LinkedIn profile review not completed yet.",
    }

    # 7. Co-curricular Achievements
    ach_score, ach_checks, ach_summary = evaluate_cocurricular_component(profile, db)
    cocurricular_data = {
        "score": ach_score,
        "checks": ach_checks,
        "summary": ach_summary,
    }

    return {
        "resume": resume_data,
        "projects": projects_data,
        "mock_interview": interview_data,
        "github": github_data,
        "coding_practice": coding_data,
        "linkedin": linkedin_data,
        "co_curricular": cocurricular_data,
    }


def compute_and_save_readiness_score(db: Session, user_id: int) -> ReadinessResponse:
    """
    Gathers all 7 components, computes the readiness score,
    persists a snapshot into SQLite models.ReadinessScore, and returns the response schema.
    """
    component_inputs = gather_component_data(db, user_id)
    result = calculate_readiness_formula(component_inputs)

    # Convert ComponentBreakdown and ActionItem objects to JSON-serializable dictionaries for SQLite
    serializable_breakdown = {}
    for k, v in result["breakdown"].items():
        serializable_breakdown[k] = v.model_dump()

    top_actions_dump = [a.model_dump() for a in result["top_actions"]]

    snapshot_payload = {
        "level": result["level"],
        "raw_score": result["raw_score"],
        "components": serializable_breakdown,
        "missing_components": result["missing_components"],
        "completed_components": result["completed_components"],
        "top_actions": top_actions_dump,
    }

    record = ReadinessScore(
        user_id=user_id,
        overall_score=result["overall_score"],
        breakdown=snapshot_payload,
        created_at=datetime.utcnow(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info(
        f"[ReadinessScore] Saved snapshot for user_id={user_id}: score={result['overall_score']} ({result['level']})"
    )

    return ReadinessResponse(
        id=record.id,
        user_id=user_id,
        overall_score=result["overall_score"],
        raw_score=result["raw_score"],
        level=result["level"],
        breakdown=result["breakdown"],
        missing_components=result["missing_components"],
        completed_components=result["completed_components"],
        top_actions=result["top_actions"],
        created_at=record.created_at,
    )


def get_current_readiness_score(db: Session, user_id: int) -> ReadinessResponse:
    """
    Fetches the latest snapshot or calculates and stores one if none exists.
    """
    latest = (
        db.query(ReadinessScore)
        .filter(ReadinessScore.user_id == user_id)
        .order_by(ReadinessScore.id.desc())
        .first()
    )
    if not latest:
        return compute_and_save_readiness_score(db, user_id)

    payload = latest.breakdown or {}
    components_dict = {}
    for k, v in payload.get("components", {}).items():
        components_dict[k] = ComponentBreakdown(**v)

    top_actions = [ActionItem(**a) for a in payload.get("top_actions", [])]

    return ReadinessResponse(
        id=latest.id,
        user_id=user_id,
        overall_score=latest.overall_score,
        raw_score=float(payload.get("raw_score", latest.overall_score)),
        level=payload.get("level", get_placement_level(latest.overall_score)),
        breakdown=components_dict,
        missing_components=payload.get("missing_components", []),
        completed_components=payload.get("completed_components", []),
        top_actions=top_actions,
        created_at=latest.created_at,
    )


def get_readiness_history(db: Session, user_id: int) -> List[ReadinessHistoryItem]:
    """
    Returns full chronological history of readiness scores for the user (for chart rendering).
    """
    records = (
        db.query(ReadinessScore)
        .filter(ReadinessScore.user_id == user_id)
        .order_by(ReadinessScore.created_at.asc(), ReadinessScore.id.asc())
        .all()
    )
    history = []
    for r in records:
        payload = r.breakdown or {}
        level = payload.get("level", get_placement_level(r.overall_score))
        history.append(
            ReadinessHistoryItem(
                id=r.id,
                overall_score=r.overall_score,
                level=level,
                breakdown=payload,
                created_at=r.created_at,
            )
        )
    return history
