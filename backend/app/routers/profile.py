from __future__ import annotations
import os
import re
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Profile, UploadedFile
from app.schemas import (
    ProfileResponse,
    ProfileUpdate,
    ConsentUpdate,
    LinkedInPasteRequest,
    ChatIntakeRequest,
    ProjectItem,
    AchievementItem,
)
from app.auth import get_current_user
from app.services.profile_parser import (
    parse_resume_file,
    parse_linkedin_text,
    parse_linkedin_pdf,
    extract_profile_data_from_chat_text,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["Profile Intake"])

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)


def sanitize_filename(name: str) -> str:
    """Sanitize filename to prevent directory traversal or invalid characters."""
    base = os.path.basename(name)
    clean = re.sub(r"[^a-zA-Z0-9_.-]", "_", base)
    return clean or f"file_{uuid.uuid4().hex[:8]}"


def get_or_create_profile(user: User, db: Session) -> Profile:
    """Ensures the user has an initialized profile record."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        profile = Profile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def build_profile_response(user: User, profile: Profile, db: Session) -> ProfileResponse:
    """Constructs the comprehensive ProfileResponse object."""
    files = db.query(UploadedFile).filter(UploadedFile.user_id == user.id).all()
    return ProfileResponse(
        id=profile.id,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        consent_given=profile.consent_given,
        consent_date=profile.consent_date,
        headline=profile.headline,
        bio=profile.bio,
        target_roles=profile.target_roles or [],
        skills=profile.skills or [],
        linkedin_url=profile.linkedin_url,
        github_url=profile.github_url,
        leetcode_url=profile.leetcode_url,
        github_username=profile.github_username,
        leetcode_username=profile.leetcode_username,
        parsed_resume=profile.parsed_resume or {},
        linkedin_data=profile.linkedin_data or {},
        projects=profile.projects or [],
        achievements=profile.achievements or [],
        uploaded_files=files,
        updated_at=profile.updated_at,
    )


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve the authenticated student's full profile, parsed data, and files."""
    profile = get_or_create_profile(current_user, db)
    return build_profile_response(current_user, profile, db)


@router.post("/consent", response_model=ProfileResponse)
def update_consent(
    payload: ConsentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Grant or revoke user consent for profile intake and benchmark analysis."""
    profile = get_or_create_profile(current_user, db)
    profile.consent_given = payload.consent_given
    profile.consent_date = datetime.utcnow() if payload.consent_given else None
    db.commit()
    db.refresh(profile)
    return build_profile_response(current_user, profile, db)


@router.put("/me", response_model=ProfileResponse)
def update_my_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update profile fields (headline, bio, skills, target roles, URLs, projects, achievements).
    Enforces consent requirement.
    """
    profile = get_or_create_profile(current_user, db)
    if not profile.consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent is required before submitting or updating profile data. Please grant consent first.",
        )

    if payload.headline is not None:
        profile.headline = payload.headline
    if payload.bio is not None:
        profile.bio = payload.bio
    if payload.target_roles is not None:
        profile.target_roles = payload.target_roles
    if payload.skills is not None:
        profile.skills = sorted(list(set(payload.skills)))
    if payload.linkedin_url is not None:
        profile.linkedin_url = payload.linkedin_url
    if payload.github_url is not None:
        profile.github_url = payload.github_url
        # Auto-extract username if URL is provided
        match = re.search(r"github\.com/([a-zA-Z0-9_-]+)", payload.github_url)
        if match:
            profile.github_username = match.group(1)
    if payload.leetcode_url is not None:
        profile.leetcode_url = payload.leetcode_url
        match = re.search(r"leetcode\.com/(?:u/)?([a-zA-Z0-9_-]+)", payload.leetcode_url)
        if match:
            profile.leetcode_username = match.group(1)
    if payload.github_username is not None:
        profile.github_username = payload.github_username
        if not profile.github_url:
            profile.github_url = f"https://github.com/{payload.github_username}"
    if payload.leetcode_username is not None:
        profile.leetcode_username = payload.leetcode_username
        if not profile.leetcode_url:
            profile.leetcode_url = f"https://leetcode.com/u/{payload.leetcode_username}/"

    if payload.projects is not None:
        projects_data = []
        for p in payload.projects:
            p_dict = p.model_dump()
            if not p_dict.get("id"):
                p_dict["id"] = f"proj-{uuid.uuid4().hex[:6]}"
            projects_data.append(p_dict)
        profile.projects = projects_data

    if payload.achievements is not None:
        achievements_data = []
        for a in payload.achievements:
            a_dict = a.model_dump()
            if not a_dict.get("id"):
                a_dict["id"] = f"ach-{uuid.uuid4().hex[:6]}"
            achievements_data.append(a_dict)
        profile.achievements = achievements_data

    db.commit()
    db.refresh(profile)
    return build_profile_response(current_user, profile, db)


@router.post("/resume", response_model=ProfileResponse)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload and parse a PDF or DOCX resume.
    Enforces consent requirement.
    Returns clean 400 on corrupt or non-resume files without 500 errors.
    """
    profile = get_or_create_profile(current_user, db)
    if not profile.consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent is required before uploading or parsing your resume. Please grant consent first.",
        )

    clean_name = sanitize_filename(file.filename or "resume.pdf")
    ext = os.path.splitext(clean_name)[1].lower()
    if ext not in [".pdf", ".docx", ".doc"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed formats are PDF (.pdf) and Word (.docx).",
        )

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    try:
        parsed_data = parse_resume_file(file_bytes, clean_name)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        logger.error(f"Error parsing resume: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not parse resume file: {str(e)}",
        )

    # Save to disk under backend/data/uploads/
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    disk_filename = f"{current_user.id}_{timestamp}_{clean_name}"
    disk_path = os.path.join(UPLOAD_DIR, disk_filename)

    with open(disk_path, "wb") as f:
        f.write(file_bytes)

    # Record uploaded file in DB
    uploaded_file = UploadedFile(
        user_id=current_user.id,
        filename=clean_name,
        file_path=disk_path,
        file_type="resume",
        file_size=len(file_bytes),
    )
    db.add(uploaded_file)

    # Update profile fields
    profile.raw_resume_text = parsed_data.get("raw_text", "")
    profile.parsed_resume = parsed_data

    # Merge skills
    existing_skills = set(profile.skills or [])
    new_skills = set(parsed_data.get("skills", []))
    profile.skills = sorted(list(existing_skills.union(new_skills)))

    # If profile has no projects yet, populate with parsed projects
    if not profile.projects and parsed_data.get("projects"):
        profile.projects = parsed_data["projects"]

    db.commit()
    db.refresh(profile)
    return build_profile_response(current_user, profile, db)


@router.post("/linkedin/upload", response_model=ProfileResponse)
async def upload_linkedin_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload and parse a LinkedIn PDF export.
    Enforces consent requirement.
    """
    profile = get_or_create_profile(current_user, db)
    if not profile.consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent is required before uploading your LinkedIn profile. Please grant consent first.",
        )

    clean_name = sanitize_filename(file.filename or "linkedin_profile.pdf")
    if not clean_name.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LinkedIn export must be a PDF file.",
        )

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded LinkedIn PDF is empty.",
        )

    try:
        parsed_data = parse_linkedin_pdf(file_bytes)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not parse LinkedIn PDF: {str(e)}")

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    disk_filename = f"{current_user.id}_{timestamp}_linkedin_{clean_name}"
    disk_path = os.path.join(UPLOAD_DIR, disk_filename)

    with open(disk_path, "wb") as f:
        f.write(file_bytes)

    uploaded_file = UploadedFile(
        user_id=current_user.id,
        filename=clean_name,
        file_path=disk_path,
        file_type="linkedin",
        file_size=len(file_bytes),
    )
    db.add(uploaded_file)

    profile.linkedin_data = parsed_data
    if parsed_data.get("headline") and not profile.headline:
        profile.headline = parsed_data["headline"]
    if parsed_data.get("about") and not profile.bio:
        profile.bio = parsed_data["about"]

    existing_skills = set(profile.skills or [])
    new_skills = set(parsed_data.get("skills", []))
    profile.skills = sorted(list(existing_skills.union(new_skills)))

    db.commit()
    db.refresh(profile)
    return build_profile_response(current_user, profile, db)


@router.post("/linkedin/paste", response_model=ProfileResponse)
def paste_linkedin_text(
    payload: LinkedInPasteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Accept pasted LinkedIn text and extract headline, about, experience, and skills.
    Enforces consent requirement.
    """
    profile = get_or_create_profile(current_user, db)
    if not profile.consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent is required before processing LinkedIn data. Please grant consent first.",
        )

    try:
        parsed_data = parse_linkedin_text(payload.text)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    profile.linkedin_data = parsed_data
    if parsed_data.get("headline") and not profile.headline:
        profile.headline = parsed_data["headline"]
    if parsed_data.get("about") and not profile.bio:
        profile.bio = parsed_data["about"]

    existing_skills = set(profile.skills or [])
    new_skills = set(parsed_data.get("skills", []))
    profile.skills = sorted(list(existing_skills.union(new_skills)))

    db.commit()
    db.refresh(profile)
    return build_profile_response(current_user, profile, db)


@router.post("/chat-intake")
def intake_from_chat(
    payload: ChatIntakeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Extracts GitHub/LeetCode handles or projects from chat conversations and updates profile.
    Enforces consent requirement.
    """
    profile = get_or_create_profile(current_user, db)
    if not profile.consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent is required before submitting profile details. Please grant consent first.",
        )

    extracted = extract_profile_data_from_chat_text(payload.message)
    applied = []

    if "github_username" in extracted:
        profile.github_username = extracted["github_username"]
        profile.github_url = extracted.get("github_url", f"https://github.com/{profile.github_username}")
        applied.append(f"GitHub: {profile.github_username}")

    if "leetcode_username" in extracted:
        profile.leetcode_username = extracted["leetcode_username"]
        profile.leetcode_url = extracted.get("leetcode_url", f"https://leetcode.com/u/{profile.leetcode_username}/")
        applied.append(f"LeetCode: {profile.leetcode_username}")

    if "project" in extracted:
        p = extracted["project"]
        p["id"] = f"proj-{uuid.uuid4().hex[:6]}"
        current_projects = list(profile.projects or [])
        current_projects.append(p)
        profile.projects = current_projects
        applied.append(f"Project: {p['title']}")

    if applied:
        db.commit()
        db.refresh(profile)
        return {
            "success": True,
            "message": f"Successfully linked to your profile: {', '.join(applied)}.",
            "profile": build_profile_response(current_user, profile, db),
        }
    else:
        return {
            "success": False,
            "message": "No profile links (GitHub, LeetCode, or Project) detected in your message.",
        }


@router.delete("/data")
def delete_my_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    'Delete all my profile data':
    - Permanently deletes all uploaded physical files from disk.
    - Clears all parsed resume, LinkedIn data, projects, achievements, and skills from DB.
    """
    # 1. Physically delete all files on disk tracked in DB
    files = db.query(UploadedFile).filter(UploadedFile.user_id == current_user.id).all()
    deleted_files_count = 0
    for uf in files:
        if os.path.exists(uf.file_path):
            try:
                os.remove(uf.file_path)
                deleted_files_count += 1
            except Exception as e:
                logger.error(f"Could not remove file {uf.file_path}: {e}")
        db.delete(uf)

    # Clean any files on disk starting with {user_id}_
    prefix = f"{current_user.id}_"
    if os.path.exists(UPLOAD_DIR):
        for fname in os.listdir(UPLOAD_DIR):
            if fname.startswith(prefix):
                try:
                    os.remove(os.path.join(UPLOAD_DIR, fname))
                    deleted_files_count += 1
                except Exception:
                    pass

    # 2. Reset Profile in DB
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if profile:
        profile.headline = None
        profile.bio = None
        profile.target_roles = []
        profile.skills = []
        profile.linkedin_url = None
        profile.github_url = None
        profile.leetcode_url = None
        profile.github_username = None
        profile.leetcode_username = None
        profile.raw_resume_text = None
        profile.parsed_resume = {}
        profile.linkedin_data = {}
        profile.projects = []
        profile.achievements = []

    db.commit()
    return {
        "success": True,
        "message": f"All profile data reset and {deleted_files_count} uploaded file(s) removed from disk.",
    }


@router.delete("/account")
def delete_my_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    'Delete my account and all data':
    - Permanently deletes all uploaded physical files from disk.
    - Cascades deletion of User row and all associated DB rows (Profile, Applications, Reviews, etc.).
    """
    # 1. Remove all files from disk
    files = db.query(UploadedFile).filter(UploadedFile.user_id == current_user.id).all()
    deleted_files_count = 0
    for uf in files:
        if os.path.exists(uf.file_path):
            try:
                os.remove(uf.file_path)
                deleted_files_count += 1
            except Exception as e:
                logger.error(f"Could not remove file {uf.file_path}: {e}")

    prefix = f"{current_user.id}_"
    if os.path.exists(UPLOAD_DIR):
        for fname in os.listdir(UPLOAD_DIR):
            if fname.startswith(prefix):
                try:
                    os.remove(os.path.join(UPLOAD_DIR, fname))
                    deleted_files_count += 1
                except Exception:
                    pass

    # 2. Delete user (cascade removes Profile, UploadedFiles, ReviewResults, etc.)
    user_id = current_user.id
    db.delete(current_user)
    db.commit()

    return {
        "success": True,
        "message": f"Account {user_id} and all associated data and {deleted_files_count} file(s) permanently deleted.",
    }


@router.get("/{user_id}", response_model=ProfileResponse)
def get_user_profile_by_id(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Enforces privacy and tenant isolation:
    Student A cannot read Student B's data (expect 403 Forbidden).
    Admins are permitted.
    """
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You cannot view another student's profile data.",
        )

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    profile = get_or_create_profile(target_user, db)
    return build_profile_response(target_user, profile, db)
