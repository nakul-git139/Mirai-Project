from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Float,
)
from sqlalchemy.orm import relationship
from app.database import Base


class UserRole:
    STUDENT = "student"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default=UserRole.STUDENT, nullable=False)
    full_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    uploaded_files = relationship("UploadedFile", back_populates="user", cascade="all, delete-orphan")
    reviews = relationship("ReviewResult", back_populates="user", cascade="all, delete-orphan")
    interviews = relationship("InterviewSession", back_populates="user", cascade="all, delete-orphan")
    readiness_scores = relationship("ReadinessScore", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")
    posted_jobs = relationship("Job", back_populates="poster", foreign_keys="Job.posted_by")
    background_jobs = relationship("BackgroundJob", back_populates="user", cascade="all, delete-orphan")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    consent_given = Column(Boolean, default=False, nullable=False)
    consent_date = Column(DateTime, nullable=True)
    headline = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    target_roles = Column(JSON, default=list, nullable=False)
    skills = Column(JSON, default=list, nullable=False)
    linkedin_url = Column(String(255), nullable=True)
    github_url = Column(String(255), nullable=True)
    leetcode_url = Column(String(255), nullable=True)
    github_username = Column(String(100), nullable=True)
    leetcode_username = Column(String(100), nullable=True)
    raw_resume_text = Column(Text, nullable=True)
    parsed_resume = Column(JSON, default=dict, nullable=False)
    linkedin_data = Column(JSON, default=dict, nullable=False)
    projects = Column(JSON, default=list, nullable=False)
    achievements = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user = relationship("User", back_populates="profile")


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)  # resume, linkedin, other
    file_size = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="uploaded_files")


class ReviewResult(Base):
    __tablename__ = "review_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    review_type = Column(String(50), nullable=False)  # resume, linkedin, github, leetcode
    score = Column(Integer, nullable=False)  # 0 - 100
    summary = Column(Text, nullable=True)
    # checks: list of {id, label, pass, evidence, fix}
    checks = Column(JSON, default=list, nullable=False)
    # rewrites: { headline: str, about: str } for profile reviews
    rewrites = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="reviews")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_role = Column(String(100), nullable=False)
    duration_minutes = Column(Integer, default=15, nullable=False)
    time_limit_seconds = Column(Integer, default=900, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="in_progress", nullable=False)  # in_progress, completed, abandoned
    current_question_index = Column(Integer, default=0, nullable=False)
    question_plan = Column(JSON, default=list, nullable=False)  # [{id, type, question, context}]
    messages = Column(JSON, default=list, nullable=False)  # [{role, content, timestamp, evaluation}]
    rubric_scores = Column(JSON, default=list, nullable=False)  # [{question_id, score, criteria}]
    feedback = Column(JSON, nullable=True)  # {strengths, weaknesses, tips, rubric_breakdown}
    score = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user = relationship("User", back_populates="interviews")


class ReadinessScore(Base):
    __tablename__ = "readiness_scores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    overall_score = Column(Integer, nullable=False)  # 0 - 100
    breakdown = Column(JSON, default=dict, nullable=False)  # {resume: N, linkedin: N, ...}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="readiness_scores")


class ApplicationStatus:
    SAVED = "Saved"
    APPLIED = "Applied"
    SHORTLISTED = "Shortlisted"
    INTERVIEW = "Interview"
    OFFER = "Offer"
    REJECTED = "Rejected"

    ALL = [SAVED, APPLIED, SHORTLISTED, INTERVIEW, OFFER, REJECTED]

    @classmethod
    def normalize(cls, status: str) -> str:
        s = (status or "").strip().lower()
        mapping = {
            "saved": cls.SAVED,
            "applied": cls.APPLIED,
            "shortlisted": cls.SHORTLISTED,
            "interview": cls.INTERVIEW,
            "interviewing": cls.INTERVIEW,
            "offer": cls.OFFER,
            "rejected": cls.REJECTED,
        }
        return mapping.get(s, cls.SAVED)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    url = Column(String(500), nullable=True)
    job_type = Column(String(50), default="job", nullable=False)  # job, internship
    eligibility_criteria = Column(JSON, default=dict, nullable=False)  # {min_readiness_score, required_skills, target_roles}
    is_pinned = Column(Boolean, default=True, nullable=False)
    deadline = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    posted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    poster = relationship("User", back_populates="posted_jobs", foreign_keys=[posted_by])
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    company = Column(String(255), nullable=True)
    role = Column(String(255), nullable=True)
    link = Column(String(500), nullable=True)
    status = Column(String(50), default=ApplicationStatus.SAVED, nullable=False)  # Saved, Applied, Shortlisted, Interview, Offer, Rejected
    notes = Column(Text, nullable=True)
    applied_at = Column(DateTime, nullable=True)
    last_status_change_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status_history = Column(JSON, default=list, nullable=False)  # [{from_status, to_status, changed_at, note}]
    followup_reminder_days = Column(Integer, default=7, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="applications")


class LLMTimingLog(Base):
    __tablename__ = "llm_timing_logs"

    id = Column(Integer, primary_key=True, index=True)
    feature = Column(String(100), nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    duration_seconds = Column(Float, nullable=False)
    status = Column(String(50), default="success", nullable=False)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id = Column(String(50), primary_key=True, index=True)  # UUID hex or string
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    task_type = Column(String(50), nullable=False, index=True)  # resume_review, linkedin_review, github_review, live_link_check, job_match
    provider = Column(String(50), nullable=False)  # ollama, openai, claude, gemini, mock
    status = Column(String(50), default="queued", nullable=False, index=True)  # queued, running, done, failed
    payload = Column(JSON, default=dict, nullable=False)
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="background_jobs")

