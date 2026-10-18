from __future__ import annotations
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Profile, InterviewSession
from app.auth import get_current_user
from app.schemas import (
    InterviewStartRequest,
    InterviewMessageRequest,
    InterviewSessionResponse,
    InterviewSummaryItem,
    InterviewReplayResponse,
    TranscribeResponse,
)
from app.services.interview_service import (
    start_interview_session,
    process_student_message,
    end_interview_session,
    get_active_session_for_user,
)
from app.services.voice_service import transcribe_audio_bytes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/interview", tags=["Mock Interview"])


def _to_session_response(session: InterviewSession, transcription: Optional[str] = None) -> InterviewSessionResponse:
    now = datetime.utcnow()
    remaining = 0
    if session.expires_at and session.status == "in_progress":
        remaining = max(0, int((session.expires_at - now).total_seconds()))

    plan = session.question_plan or []
    return InterviewSessionResponse(
        id=session.id,
        user_id=session.user_id,
        target_role=session.target_role,
        duration_minutes=session.duration_minutes,
        time_limit_seconds=session.time_limit_seconds,
        status=session.status,
        started_at=session.created_at,
        expires_at=session.expires_at,
        time_remaining_seconds=remaining,
        current_question_index=session.current_question_index or 0,
        total_questions=len(plan),
        messages=session.messages or [],
        score=session.score,
        feedback=session.feedback,
        transcription=transcription,
    )


@router.post("/start", response_model=InterviewSessionResponse)
def start_interview(
    payload: InterviewStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Starts a new technical mock interview session:
      - Validates student privacy consent
      - Generates personalized questions grounded in student's resume & projects
      - Sets countdown timer boundaries
      - Seeds the first interviewer question
    """
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile or not profile.consent_given:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student consent is required before starting a mock interview simulation. Please grant consent in Profile & My Data.",
        )

    try:
        session = start_interview_session(
            db=db,
            user=current_user,
            duration_minutes=payload.duration_minutes,
            time_limit_seconds=payload.time_limit_seconds,
            target_role=payload.target_role,
        )
        return _to_session_response(session)
    except Exception as e:
        logger.error(f"Error starting interview session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start interview simulation: {str(e)}",
        )


@router.get("/active", response_model=Optional[InterviewSessionResponse])
def get_active_interview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves the currently in-progress interview session for the authenticated user,
    or null if no active session exists. Gracefully handles page refreshes and timer expiry.
    """
    session = get_active_session_for_user(db, current_user.id)
    if not session or session.status != "in_progress":
        return None
    return _to_session_response(session)


@router.get("/history", response_model=List[InterviewSummaryItem])
def get_interview_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns a list of all historical mock interview sessions completed by the student.
    """
    sessions = (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == current_user.id)
        .order_by(InterviewSession.id.desc())
        .all()
    )
    return [
        InterviewSummaryItem(
            id=s.id,
            target_role=s.target_role,
            duration_minutes=s.duration_minutes,
            status=s.status,
            score=s.score,
            created_at=s.created_at,
        )
        for s in sessions
    ]


@router.get("/{session_id}", response_model=InterviewSessionResponse)
def get_interview_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves the details and message history of a specific interview session.
    """
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session #{session_id} not found.",
        )
    if session.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this interview session.",
        )

    # Check for expiration if still in progress
    if session.status == "in_progress" and session.expires_at and datetime.utcnow() >= session.expires_at:
        session = end_interview_session(db, session, reason="timer_expired")

    return _to_session_response(session)


@router.post("/{session_id}/message", response_model=InterviewSessionResponse)
def send_interview_message(
    session_id: int,
    payload: InterviewMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submits a student answer to the current question:
      - Validates answer content (rejects empty / whitespace-only)
      - Evaluates answer against fixed rubric criteria (0-100 pts)
      - Produces adaptive follow-up or next structured question
      - Enforces session countdown timer
    """
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session #{session_id} not found.",
        )
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to interact with this interview session.",
        )
    if session.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot send messages to a session with status '{session.status}'.",
        )

    clean_message = payload.message.strip()
    if not clean_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Answer cannot be empty. Please provide a substantive response.",
        )

    session, _ = process_student_message(db, session, clean_message)
    return _to_session_response(session)


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Transcribes an uploaded audio file using faster-whisper.
    Returns the transcription and detected word count.
    """
    audio_bytes = await file.read()
    if not audio_bytes or len(audio_bytes.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty.",
        )

    try:
        text = transcribe_audio_bytes(audio_bytes, filename=file.filename or "audio.webm")
    except Exception as e:
        logger.error(f"Error in transcribe endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Speech transcription failed: {str(e)}",
        )

    words = text.split()
    return TranscribeResponse(
        transcription=text,
        word_count=len(words),
    )


@router.post("/{session_id}/voice-message", response_model=InterviewSessionResponse)
async def send_interview_voice_message(
    session_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Accepts spoken audio from the student, transcribes it via faster-whisper,
    evaluates the transcribed answer against the fixed 4-dimension rubric,
    and returns the updated interview session state with the interviewer's reply.
    """
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session #{session_id} not found.",
        )
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to interact with this interview session.",
        )
    if session.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot send messages to a session with status '{session.status}'.",
        )

    audio_bytes = await file.read()
    if not audio_bytes or len(audio_bytes.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio recording was empty. Please check your microphone and speak again.",
        )

    try:
        transcription = transcribe_audio_bytes(audio_bytes, filename=file.filename or "audio.webm")
    except Exception as e:
        logger.error(f"Failed to transcribe interview voice message: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Speech-to-text processing failed: {str(e)}",
        )

    clean_text = transcription.strip()
    if not clean_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No speech could be detected in the recording. Please speak clearly or switch to text mode.",
        )

    session, _ = process_student_message(db, session, clean_text)
    return _to_session_response(session, transcription=clean_text)


@router.post("/{session_id}/end", response_model=InterviewSessionResponse)
def end_interview(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Terminates an interview session early (e.g. student ends session or timer expires):
      - Grades all completed answers
      - Synthesizes strengths, weak areas, and actionable tips
      - Auto-updates the student's placement readiness score
    """
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session #{session_id} not found.",
        )
    if session.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this interview session.",
        )

    session = end_interview_session(db, session, reason="user_terminated")
    return _to_session_response(session)


@router.get("/{session_id}/replay", response_model=InterviewReplayResponse)
def get_interview_replay(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves full replay data for a completed interview:
      - Turn-by-turn transcript
      - Per-question rubric grades and feedback
      - Strengths and actionable improvement tips
    """
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session #{session_id} not found.",
        )
    if session.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this interview transcript.",
        )

    return InterviewReplayResponse(
        id=session.id,
        user_id=session.user_id,
        target_role=session.target_role,
        duration_minutes=session.duration_minutes,
        status=session.status,
        score=session.score,
        question_plan=session.question_plan or [],
        messages=session.messages or [],
        rubric_scores=session.rubric_scores or [],
        feedback=session.feedback,
        created_at=session.created_at,
    )
