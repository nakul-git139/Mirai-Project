from __future__ import annotations
import re
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


COMMON_TECH_SKILLS = [
    "react", "next.js", "vue", "angular", "javascript", "typescript", "html", "css", "tailwind",
    "python", "fastapi", "django", "flask", "node.js", "express", "go", "golang", "java", "spring",
    "c++", "c#", "rust", "sql", "postgresql", "mysql", "mongodb", "redis", "docker", "kubernetes",
    "aws", "gcp", "azure", "git", "linux", "graphql", "rest", "pandas", "numpy", "pytorch",
    "tensorflow", "machine learning", "data science"
]


def clean_text_for_search(text: str) -> str:
    """Lowercase text and clean non-alphanumeric chars for token searching."""
    if not text:
        return ""
    return re.sub(r"[^\w\s\.\+\#\-]", " ", text.lower())


def score_job_match(
    job: Dict[str, Any],
    skills: List[str],
    target_roles: List[str],
    readiness_score: Optional[int] = None,
    preferred_locations: Optional[List[str]] = None,
) -> Tuple[int, List[str], List[str], List[str]]:
    """
    Computes a match score (0-100) and why-it-matched reasons.
    Returns: (match_score, match_reasons, matched_skills, missing_skills)
    """
    job_title = job.get("title", "")
    job_desc = job.get("description", "")
    job_loc = job.get("location", "")
    full_text = clean_text_for_search(f"{job_title} {job_desc} {job_loc}")
    title_text = clean_text_for_search(job_title)

    reasons: List[str] = []
    matched_skills: List[str] = []
    missing_skills: List[str] = []

    # 1. Skill Overlap (0 - 50 points)
    skill_points = 0
    clean_student_skills = [s.strip() for s in skills if s.strip()]
    for s in clean_student_skills:
        pattern = rf"\b{re.escape(s.lower())}\b"
        if re.search(pattern, title_text):
            matched_skills.append(s)
            skill_points += 15
        elif re.search(pattern, full_text):
            matched_skills.append(s)
            skill_points += 10

    # Clamp skill score
    skill_points = min(50, skill_points)
    if matched_skills:
        reasons.append(
            f"Matched {len(matched_skills)} verified profile skill(s): {', '.join(matched_skills[:4])}"
        )

    # Detect skills in job description that student doesn't have
    student_skills_lower = {s.lower() for s in clean_student_skills}
    for tech in COMMON_TECH_SKILLS:
        if tech not in student_skills_lower:
            pattern = rf"\b{re.escape(tech)}\b"
            if re.search(pattern, full_text):
                missing_skills.append(tech.title())
                if len(missing_skills) >= 4:
                    break

    # 2. Target Role & Title Alignment (0 - 30 points)
    role_points = 0
    clean_target_roles = [r.strip() for r in target_roles if r.strip()]
    role_matched = False

    for role in clean_target_roles:
        role_lower = role.lower()
        if role_lower in title_text or all(tok in title_text for tok in role_lower.split()):
            role_points = 30
            role_matched = True
            reasons.append(f"Job title aligns directly with your target role '{role}'")
            break
        else:
            # Partial token overlap
            role_tokens = [tok for tok in role_lower.split() if len(tok) > 2]
            common_tokens = [tok for tok in role_tokens if tok in title_text]
            if common_tokens:
                role_points = max(role_points, 18)
                reasons.append(f"Shares role domain tokens: {', '.join(common_tokens)}")
                break

    if not clean_target_roles:
        # Default points if student hasn't selected target roles
        role_points = 15

    # 3. Placement Readiness Alignment (0 - 15 points)
    readiness_points = 0
    if readiness_score is not None:
        if readiness_score >= 75:
            readiness_points = 15
            reasons.append(
                f"Your readiness score ({readiness_score}/100 - Placement Ready) satisfies benchmark"
            )
        elif readiness_score >= 50:
            readiness_points = 10
            reasons.append(
                f"Your readiness score ({readiness_score}/100 - Almost Ready) is in range for this opening"
            )
        else:
            readiness_points = 5
            reasons.append(
                f"Readiness score ({readiness_score}/100) - completing pending reviews will boost chances"
            )
    else:
        readiness_points = 10

    # 4. Location / Remote Preference (0 - 5 points)
    loc_points = 0
    loc_lower = job_loc.lower()
    pref_locs = [l.lower() for l in (preferred_locations or ["remote", "bangalore"])]

    if any(pl in loc_lower for pl in pref_locs) or "remote" in loc_lower or "anywhere" in loc_lower:
        loc_points = 5
        reasons.append(f"Location ({job_loc}) matches preferred work flexibility")

    # Final composite match calculation
    total_score = min(100, skill_points + role_points + readiness_points + loc_points)

    if not reasons:
        reasons.append("General technology opportunity matching entry-level qualifications")

    return total_score, reasons, matched_skills, missing_skills[:4]


def rank_jobs(
    jobs: List[Dict[str, Any]],
    skills: List[str],
    target_roles: List[str],
    readiness_score: Optional[int] = None,
    preferred_locations: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Ranks a list of jobs based on student profile and readiness score.
    Decorates each job with match_score, match_reasons, matched_skills, missing_skills.
    """
    ranked: List[Dict[str, Any]] = []

    for job in jobs:
        score, reasons, matched_sk, missing_sk = score_job_match(
            job=job,
            skills=skills,
            target_roles=target_roles,
            readiness_score=readiness_score,
            preferred_locations=preferred_locations,
        )

        job_item = job.copy()
        job_item["match_score"] = score
        job_item["match_reasons"] = reasons
        job_item["matched_skills"] = matched_sk
        job_item["missing_skills"] = missing_sk
        ranked.append(job_item)

    # Sort descending by match_score, then stable title order
    ranked.sort(key=lambda j: (-j["match_score"], j.get("title", "")))
    return ranked


def generate_job_match_explanation(
    job_title: str,
    job_skills: List[str],
    candidate_skills: List[str],
    score: int,
    adapter: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Generates structured job match explanation with strengths and action items.
    Uses LLM if available with small num_predict (120) or deterministic rule fallback.
    """
    if adapter is None:
        try:
            from app.llm.factory import get_llm_adapter
            adapter = get_llm_adapter()
        except Exception:
            adapter = None

    class JobMatchExplanationSchema(BaseModel):
        match_summary: str = Field(description="1-sentence summary of candidate fit")
        key_strengths: List[str] = Field(default_factory=list, description="Overlapping core skills")
        missing_skills: List[str] = Field(default_factory=list, description="Key gaps to bridge")
        suggested_action: str = Field(description="Actionable suggestion for application")

    if adapter is not None:
        try:
            from app.llm.structured import generate_structured_output
            prompt = (
                f"Role: {job_title}\n"
                f"Required Skills: {', '.join(job_skills[:6])}\n"
                f"Candidate Skills: {', '.join(candidate_skills[:6])}\n"
                f"Computed Match Score: {score}/100"
            )
            res: JobMatchExplanationSchema = generate_structured_output(
                adapter=adapter,
                prompt=f"Explain job match:\n{prompt}",
                schema=JobMatchExplanationSchema,
                system_prompt="You are a Placement Career Strategist. Return compact JSON with brief bullet phrases.",
                max_retries=2,
                temperature=0.0,
                feature="job_matching_explanation",
                num_predict=120,
            )
            return {
                "match_summary": res.match_summary,
                "key_strengths": res.key_strengths,
                "missing_skills": res.missing_skills,
                "suggested_action": res.suggested_action,
            }
        except Exception as e:
            logger.debug(f"LLM job match explanation fallback: {e}")

    # Fallback
    matched = [s for s in job_skills if s in candidate_skills]
    missing = [s for s in job_skills if s not in candidate_skills]
    return {
        "match_summary": f"Strong alignment for {job_title} with {score}% skill overlap.",
        "key_strengths": matched[:3],
        "missing_skills": missing[:3],
        "suggested_action": f"Highlight {matched[0] if matched else 'core coursework'} in cover letter.",
    }
