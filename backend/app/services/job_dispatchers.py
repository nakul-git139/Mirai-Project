from __future__ import annotations
import os
import io
import base64
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from app.database import SessionLocal
from app.models import User, Profile, UploadedFile, ReviewResult
from app.services.resume_reviewer import review_resume
from app.services.linkedin_reviewer import review_linkedin
from app.services.github_reviewer import evaluate_github_and_live
from app.services.live_link_checker import check_live_link
from app.services.job_discovery.ranker import generate_job_match_explanation
from app.services.readiness_service import compute_and_save_readiness_score
from app.llm.factory import get_llm_adapter

logger = logging.getLogger(__name__)


def run_resume_review(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Execute resume benchmark review task."""
    user_id = payload.get("user_id")
    file_bytes = b""
    filename = payload.get("filename") or "resume.pdf"

    if "file_b64" in payload and payload["file_b64"]:
        file_bytes = base64.b64decode(payload["file_b64"])
    elif "file_path" in payload and payload["file_path"] and os.path.exists(payload["file_path"]):
        with open(payload["file_path"], "rb") as f:
            file_bytes = f.read()

    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()
        profile = db.query(Profile).filter(Profile.user_id == user_id).first()
        profile_context = {
            "github_url": profile.github_url if profile else None,
            "leetcode_url": profile.leetcode_url if profile else None,
            "target_roles": profile.target_roles if profile else [],
        }

        if not file_bytes:
            # Check latest uploaded resume
            latest_file = (
                db.query(UploadedFile)
                .filter(UploadedFile.user_id == user_id, UploadedFile.file_type == "resume")
                .order_by(UploadedFile.created_at.desc())
                .first()
            )
            if latest_file and os.path.exists(latest_file.file_path):
                filename = latest_file.filename
                with open(latest_file.file_path, "rb") as f:
                    file_bytes = f.read()

        if not file_bytes:
            raise ValueError("No resume content found to review.")

        provider = payload.get("provider")
        adapter = None
        if provider:
            try:
                adapter = get_llm_adapter(provider=provider)
            except Exception:
                adapter = None

        review_data = review_resume(
            file_bytes=file_bytes,
            filename=filename,
            profile_data=profile_context,
            adapter=adapter,
        )

        if adapter is not None:
            try:
                from app.llm.structured import generate_structured_output
                from pydantic import BaseModel, Field

                class ResumeLLMSummary(BaseModel):
                    executive_takeaway: str = Field(description="1-sentence placement readiness summary")

                llm_res: ResumeLLMSummary = generate_structured_output(
                    adapter=adapter,
                    prompt=f"Resume score is {review_data['score']}/100. Target roles: {profile_context.get('target_roles', [])}. Summarize student placement readiness in 1 concise sentence.",
                    schema=ResumeLLMSummary,
                    system_prompt="You are a placement director. Keep the takeaway under 25 words.",
                    temperature=0.0,
                    feature="resume_review_takeaway",
                    num_predict=80,
                )
                if llm_res and llm_res.executive_takeaway:
                    review_data["summary"] = f"{review_data['summary']} Placement Note: {llm_res.executive_takeaway}"
            except Exception as e:
                logger.warning(f"Could not generate LLM resume takeaway: {e}")

        review_record = ReviewResult(
            user_id=user_id,
            review_type="resume",
            score=review_data["score"],
            summary=review_data["summary"],
            checks=review_data["checks"],
            created_at=datetime.utcnow(),
        )
        db.add(review_record)
        db.commit()
        db.refresh(review_record)

        try:
            compute_and_save_readiness_score(db, user_id)
        except Exception as re:
            logger.warning(f"Readiness score update warning: {re}")

        return {
            "id": review_record.id,
            "user_id": user_id,
            "review_type": "resume",
            "score": review_record.score,
            "summary": review_record.summary,
            "checks": review_record.checks,
            "created_at": review_record.created_at.isoformat(),
        }


def run_linkedin_review(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Execute LinkedIn benchmark review task."""
    user_id = payload.get("user_id")
    file_bytes = b""
    text_content = payload.get("text")
    filename = payload.get("filename") or "linkedin_profile.pdf"

    if "file_b64" in payload and payload["file_b64"]:
        file_bytes = base64.b64decode(payload["file_b64"])

    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()
        profile = db.query(Profile).filter(Profile.user_id == user_id).first()

        from app.routers.linkedin_review import get_student_resume_context
        resume_context = get_student_resume_context(user, profile, db) if user and profile else {}

        if not file_bytes and not text_content and profile:
            li_data = profile.linkedin_data or {}
            parts = []
            if li_data.get("headline"):
                parts.append(li_data["headline"])
            if li_data.get("about"):
                parts.append(f"About\n{li_data['about']}")
            if li_data.get("experience"):
                parts.append("Experience\n" + "\n".join(f"{exp.get('title','')} at {exp.get('company','')}" for exp in li_data["experience"]))
            if li_data.get("skills"):
                parts.append("Skills\n" + ", ".join(li_data["skills"]))
            text_content = "\n\n".join(parts)

        review_data = review_linkedin(
            file_bytes=file_bytes,
            text=text_content,
            filename=filename,
            resume_context=resume_context,
        )

        review_record = ReviewResult(
            user_id=user_id,
            review_type="linkedin",
            score=review_data["score"],
            summary=review_data["summary"],
            checks=review_data["checks"],
            rewrites=review_data.get("rewrites", {}),
            created_at=datetime.utcnow(),
        )
        db.add(review_record)
        db.commit()
        db.refresh(review_record)

        try:
            compute_and_save_readiness_score(db, user_id)
        except Exception as re:
            logger.warning(f"Readiness score update warning: {re}")

        return {
            "id": review_record.id,
            "user_id": user_id,
            "review_type": "linkedin",
            "score": review_record.score,
            "summary": review_record.summary,
            "checks": review_record.checks,
            "rewrites": review_record.rewrites,
            "created_at": review_record.created_at.isoformat(),
        }


def run_github_review(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Execute GitHub and codebase benchmark review task."""
    user_id = payload.get("user_id")
    username = payload.get("username")
    repo_url = payload.get("repo_url")
    live_url = payload.get("live_url")
    project_title = payload.get("project_title")

    with SessionLocal() as db:
        profile = db.query(Profile).filter(Profile.user_id == user_id).first()

        review_data = evaluate_github_and_live(
            username=username,
            repo_url=repo_url,
            live_url=live_url,
            project_title=project_title,
        )

        review_row = ReviewResult(
            user_id=user_id,
            review_type="github",
            score=review_data["score"],
            summary=review_data["summary"],
            checks=review_data["checks"],
            rewrites={
                "repo_details": review_data.get("repo_details", {}),
                "live_link_results": review_data.get("live_link_results"),
                "screenshots": review_data.get("screenshots", {}),
            },
        )
        db.add(review_row)
        db.commit()
        db.refresh(review_row)

        try:
            compute_and_save_readiness_score(db, user_id)
        except Exception as re:
            logger.warning(f"Readiness score update warning: {re}")

        return {
            "id": review_row.id,
            "user_id": user_id,
            "review_type": "github",
            "score": review_row.score,
            "summary": review_row.summary,
            "checks": review_row.checks,
            "repo_details": review_data.get("repo_details", {}),
            "live_link_results": review_data.get("live_link_results"),
            "screenshots": review_data.get("screenshots", {}),
            "created_at": review_row.created_at.isoformat(),
        }


def run_live_link_check(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Execute live deployment link verification task."""
    url = payload.get("url")
    project_title = payload.get("project_title")
    return check_live_link(url, project_title=project_title)


def run_job_match(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Execute job match explanation task."""
    job_title = payload.get("job_title", "Software Engineer")
    job_skills = payload.get("job_skills", [])
    candidate_skills = payload.get("candidate_skills", [])
    score = payload.get("score", 70)
    provider = payload.get("provider")

    adapter = None
    if provider:
        try:
            adapter = get_llm_adapter(provider=provider)
        except Exception:
            adapter = None

    return generate_job_match_explanation(
        job_title=job_title,
        job_skills=job_skills,
        candidate_skills=candidate_skills,
        score=score,
        adapter=adapter,
    )


DISPATCH_MAP = {
    "resume_review": run_resume_review,
    "linkedin_review": run_linkedin_review,
    "github_review": run_github_review,
    "live_link_check": run_live_link_check,
    "job_match": run_job_match,
}
