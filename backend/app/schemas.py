from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict, AliasChoices


# ---------------- Auth Schemas ----------------
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    role: str = Field(default="student", pattern="^(student|admin)$")
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    email: str


# ---------------- Settings Schemas ----------------
class SettingsUpdate(BaseModel):
    provider: Optional[str] = None  # ollama, openai, claude, gemini, mock
    model: Optional[str] = None
    ollama_base_url: Optional[str] = None
    openai_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    concurrency_limits: Optional[Dict[str, int]] = None
    rate_limit_reviews_per_hour: Optional[int] = None


class SettingsResponse(BaseModel):
    provider: str
    model: str
    ollama_base_url: str
    has_openai_key: bool
    has_claude_key: bool
    has_gemini_key: bool
    available_providers: List[str]
    default_models: Dict[str, str]
    enable_mock_interview: bool = False
    concurrency_limits: Dict[str, int] = Field(default_factory=dict)
    rate_limit_reviews_per_hour: int = 10
    env_forced: bool = False
    env_forced_provider: Optional[str] = None


# ---------------- Background Job Schemas ----------------
class BackgroundJobTriggerRequest(BaseModel):
    task_type: str  # resume_review, linkedin_review, github_review, live_link_check, job_match
    payload: Dict[str, Any] = Field(default_factory=dict)
    provider: Optional[str] = None


class BackgroundJobResponse(BaseModel):
    id: str
    user_id: int
    task_type: str
    provider: str
    model: Optional[str] = None
    status: str  # queued, running, done, failed
    queue_position: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class AdminQueueStatusResponse(BaseModel):
    total_queue_length: int
    provider_queues: Dict[str, int]
    provider_limits: Dict[str, int]
    running_jobs_count: int
    running_jobs: List[Dict[str, Any]]
    queued_jobs: List[Dict[str, Any]]
    recent_timings: List[Dict[str, Any]]


class CancelJobResponse(BaseModel):
    id: str
    status: str = "cancelled"
    message: str


class CancelAllJobsResponse(BaseModel):
    cancelled_count: int
    cancelled_job_ids: List[str]
    message: str


class ConnectionTestRequest(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None


class ConnectionTestResponse(BaseModel):
    success: bool
    provider: str
    model: str
    message: str


# ---------------- Job & Admin Schemas ----------------
class JobCreate(BaseModel):
    title: str
    company: str
    description: str
    requirements: Optional[str] = None
    location: Optional[str] = None
    url: Optional[str] = None
    job_type: Optional[str] = "job"  # job or internship
    eligibility_criteria: Optional[Dict[str, Any]] = None
    is_pinned: Optional[bool] = True
    deadline: Optional[str] = None


class JobResponse(BaseModel):
    id: int
    title: str
    company: str
    description: str
    requirements: Optional[str] = None
    location: Optional[str] = None
    url: Optional[str] = None
    job_type: str = "job"
    eligibility_criteria: Dict[str, Any] = {}
    is_pinned: bool = True
    deadline: Optional[str] = None
    is_active: bool
    posted_by: Optional[int] = None
    applicant_count: Optional[int] = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------- Application Tracker Schemas ----------------
class ApplicationCreate(BaseModel):
    job_id: Optional[int] = None
    company: str
    role: str
    link: Optional[str] = None
    status: Optional[str] = "Applied"
    notes: Optional[str] = None
    applied_at: Optional[datetime] = None
    followup_reminder_days: Optional[int] = 7


class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    link: Optional[str] = None
    followup_reminder_days: Optional[int] = None
    applied_at: Optional[datetime] = None


class ApplicationResponse(BaseModel):
    id: int
    user_id: int
    job_id: Optional[int] = None
    company: str
    role: str
    link: Optional[str] = None
    status: str
    notes: Optional[str] = None
    applied_at: Optional[datetime] = None
    last_status_change_at: datetime
    status_history: List[Dict[str, Any]] = []
    followup_reminder_days: Optional[int] = 7
    has_movement: bool = False
    is_reminder_due: bool = False
    days_since_update: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationListResponse(BaseModel):
    applications: List[ApplicationResponse]
    counts_by_status: Dict[str, int]
    total_count: int
    movement_count: int
    reminders_count: int


class FollowupReminderItem(BaseModel):
    application_id: int
    company: str
    role: str
    status: str
    applied_at: Optional[datetime] = None
    last_status_change_at: datetime
    days_inactive: int
    recommended_action: str


class ApplicantItem(BaseModel):
    application_id: int
    student_id: int
    student_name: str
    student_email: str
    readiness_score: Optional[int] = None
    target_roles: List[str] = []
    skills: List[str] = []
    status: str
    applied_at: Optional[datetime] = None
    last_status_change_at: Optional[datetime] = None
    notes: Optional[str] = None
    status_history: List[Dict[str, Any]] = []


class ApplicantStatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None



# ---------------- Chat Schemas ----------------
class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant|system)$")
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str
    provider: str
    model: str


# ---------------- Structured Output & Review Schemas ----------------
class ReviewCheck(BaseModel):
    id: str
    label: str
    passed: bool = Field(..., serialization_alias="pass", validation_alias=AliasChoices("pass", "passed"))
    evidence: str
    fix: str

    model_config = ConfigDict(populate_by_name=True)

    @property
    def pass_(self) -> bool:
        return self.passed


class BenchmarkReview(BaseModel):
    score: int = Field(ge=0, le=100)
    summary: str
    checks: List[ReviewCheck]
    reviewed_with: Optional[str] = None
    code_only_checks: Optional[List[int]] = None


class ResumeReviewResponse(BaseModel):
    id: Optional[int] = None
    user_id: Optional[int] = None
    review_type: str = "resume"
    score: int = Field(ge=0, le=100)
    summary: str
    checks: List[ReviewCheck]
    reviewed_with: Optional[str] = None
    code_only_checks: Optional[List[int]] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class LinkedInReviewTextRequest(BaseModel):
    text: str = Field(min_length=1, description="Pasted LinkedIn profile text")


class LinkedInRewrites(BaseModel):
    headline: str = Field(description="Ready-to-paste LinkedIn headline, max 220 chars")
    about: str = Field(description="Ready-to-paste LinkedIn About summary")


class LinkedInReviewResponse(BaseModel):
    id: Optional[int] = None
    user_id: Optional[int] = None
    review_type: str = "linkedin"
    score: int = Field(ge=0, le=100)
    summary: str
    checks: List[ReviewCheck]
    rewrites: Dict[str, str] = Field(default_factory=dict)
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ---------------- GitHub & Live Link Review Schemas ----------------
class GitHubReviewRequest(BaseModel):
    username: Optional[str] = None
    repo_url: Optional[str] = None
    live_url: Optional[str] = None
    project_title: Optional[str] = None


class LiveLinkCheckRequest(BaseModel):
    url: str
    project_title: Optional[str] = None
    expected_keywords: List[str] = Field(default_factory=list)


class GitHubReviewResponse(BaseModel):
    id: Optional[int] = None
    user_id: Optional[int] = None
    review_type: str = "github"
    score: int = Field(ge=0, le=100)
    summary: str
    checks: List[ReviewCheck]
    repo_details: Dict[str, Any] = Field(default_factory=dict)
    live_link_results: Optional[Dict[str, Any]] = None
    screenshots: Dict[str, Optional[str]] = Field(default_factory=dict)
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)




# ---------------- Profile Intake Schemas ----------------
class ConsentUpdate(BaseModel):
    consent_given: bool


class ProjectItem(BaseModel):
    id: Optional[str] = None
    title: str
    repo_url: Optional[str] = None
    live_url: Optional[str] = None
    description: Optional[str] = None
    tech_stack: List[str] = []


class AchievementItem(BaseModel):
    id: Optional[str] = None
    type: str = "hackathon"  # hackathon, certification, club, award
    title: str
    issuer: Optional[str] = None
    date: Optional[str] = None
    description: Optional[str] = None


class ProfileUpdate(BaseModel):
    headline: Optional[str] = None
    bio: Optional[str] = None
    target_roles: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    leetcode_url: Optional[str] = None
    github_username: Optional[str] = None
    leetcode_username: Optional[str] = None
    projects: Optional[List[ProjectItem]] = None
    achievements: Optional[List[AchievementItem]] = None


class LinkedInPasteRequest(BaseModel):
    text: str = Field(min_length=1)


class ChatIntakeRequest(BaseModel):
    message: str = Field(min_length=1)


class UploadedFileSummary(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProfileResponse(BaseModel):
    id: int
    user_id: int
    email: Optional[str] = None
    full_name: Optional[str] = None
    consent_given: bool
    consent_date: Optional[datetime] = None
    headline: Optional[str] = None
    bio: Optional[str] = None
    target_roles: List[str] = []
    skills: List[str] = []
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    leetcode_url: Optional[str] = None
    github_username: Optional[str] = None
    leetcode_username: Optional[str] = None
    parsed_resume: Dict[str, Any] = {}
    linkedin_data: Dict[str, Any] = {}
    projects: List[Dict[str, Any]] = []
    achievements: List[Dict[str, Any]] = []
    uploaded_files: List[UploadedFileSummary] = []
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------- Readiness Score Schemas ----------------
class ComponentBreakdown(BaseModel):
    name: str
    weight: float
    score: Optional[float] = None
    weighted_points: float = 0.0
    status: str = "scored"  # "scored" | "missing"
    failed_checks_count: int = 0
    summary: str = ""


class ActionItem(BaseModel):
    id: str
    component: str
    title: str
    evidence: str
    fix: str
    points_gained: float
    status: str = "open"


class ReadinessResponse(BaseModel):
    id: Optional[int] = None
    user_id: Optional[int] = None
    overall_score: int = Field(ge=0, le=100)
    raw_score: float = Field(ge=0.0, le=100.0)
    level: str  # "Not ready" | "Almost ready" | "Placement ready"
    note: Optional[str] = None
    breakdown: Dict[str, ComponentBreakdown] = Field(default_factory=dict)
    missing_components: List[str] = Field(default_factory=list)
    completed_components: List[str] = Field(default_factory=list)
    top_actions: List[ActionItem] = Field(default_factory=list)
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ReadinessHistoryItem(BaseModel):
    id: int
    overall_score: int
    level: str
    breakdown: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------- Mock Interview Schemas ----------------
class InterviewStartRequest(BaseModel):
    duration_minutes: int = Field(default=15, ge=1, le=60)
    time_limit_seconds: Optional[int] = Field(default=None, ge=1)
    target_role: Optional[str] = None


class InterviewMessageRequest(BaseModel):
    message: str = Field(min_length=1, description="Student's answer to the current question")


class RubricCriterionGrade(BaseModel):
    criterion_id: str
    name: str
    score: float
    max_score: float
    feedback: str


class AnswerEvaluation(BaseModel):
    score: int = Field(ge=0, le=100)
    criteria: List[RubricCriterionGrade]
    summary: str
    adaptive_followup: Optional[str] = None


class InterviewSessionResponse(BaseModel):
    id: int
    user_id: int
    target_role: str
    duration_minutes: int
    time_limit_seconds: int
    status: str  # in_progress, completed, abandoned
    started_at: datetime
    expires_at: Optional[datetime]
    time_remaining_seconds: int
    current_question_index: int
    total_questions: int
    messages: List[Dict[str, Any]]
    score: Optional[int] = None
    feedback: Optional[Dict[str, Any]] = None
    transcription: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TranscribeResponse(BaseModel):
    transcription: str
    word_count: int
    duration_seconds: Optional[float] = None


class InterviewSummaryItem(BaseModel):
    id: int
    target_role: str
    duration_minutes: int
    status: str
    score: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterviewReplayResponse(BaseModel):
    id: int
    user_id: int
    target_role: str
    duration_minutes: int
    status: str
    score: Optional[int]
    question_plan: List[Dict[str, Any]]
    messages: List[Dict[str, Any]]
    rubric_scores: List[Dict[str, Any]]
    feedback: Optional[Dict[str, Any]]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------- Job Discovery Schemas ----------------
class OpenSearchLinks(BaseModel):
    linkedin: str
    naukri: str
    internshala: str
    google: str


class DiscoveredJobResponse(BaseModel):
    id: str
    title: str
    company: str
    location: str
    url: str
    description: Optional[str] = ""
    source: Optional[str] = ""
    sources: List[str] = []
    alternate_urls: List[str] = []
    match_score: int
    match_reasons: List[str] = []
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    is_pinned: bool = False
    db_job_id: Optional[int] = None
    updated_at: Optional[Any] = None
    metadata: Dict[str, Any] = {}



class JobDiscoveryResponse(BaseModel):
    total_raw: int
    total_unique: int
    source_counts: Dict[str, int]
    boolean_query: str
    open_search_links: OpenSearchLinks
    jobs: List[DiscoveredJobResponse]


class BooleanQueryRequest(BaseModel):
    skills: List[str] = []
    target_roles: List[str] = []
    locations: Optional[List[str]] = None
    job_types: Optional[List[str]] = None


class BooleanQueryResponse(BaseModel):
    boolean_query: str
    open_search_links: OpenSearchLinks


class SourcesConfigRequest(BaseModel):
    greenhouse_slugs: Optional[List[str]] = None
    lever_slugs: Optional[List[str]] = None


