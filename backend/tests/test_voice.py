from __future__ import annotations
import io
import os
import subprocess
import wave
from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, Profile, InterviewSession
from app.services.voice_service import (
    transcribe_audio_bytes,
    compute_transcription_accuracy,
)


@pytest.fixture(autouse=True)
def enable_interview_flag(monkeypatch):
    """Enables interview flag by default for voice tests calling interview endpoints."""
    monkeypatch.setattr("app.config.ENABLE_MOCK_INTERVIEW", True)


def _generate_test_speech_audio(text: str, filename: str) -> str:
    """Generates a real 16kHz WAV audio file with spoken speech using macOS say tool."""
    os.makedirs("backend/data", exist_ok=True)
    wav_path = os.path.join("backend/data", filename)
    try:
        subprocess.run(
            [
                "say",
                "--file-format=WAVE",
                "--data-format=LEI16@16000",
                "-o",
                wav_path,
                text,
            ],
            check=True,
            capture_output=True,
        )
    except Exception as e:
        # Fallback to wave generator if say is unavailable
        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00\x00" * 16000)
    return wav_path


def _generate_silent_audio() -> bytes:
    """Generates 1 second of silent 16kHz WAV audio bytes."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * 16000)
    return buf.getvalue()


# ---------------- 1. Voice Service STT Accuracy Test ----------------
def test_voice_service_transcription_accuracy():
    """
    Speaks a test sentence, transcribes it with faster-whisper,
    and measures transcription accuracy and Word Error Rate.
    Asserts accuracy >= 90%.
    """
    test_sentence = "I have built distributed systems with Python and React for three years."
    wav_path = _generate_test_speech_audio(test_sentence, "test_spoken_sentence.wav")

    with open(wav_path, "rb") as f:
        audio_bytes = f.read()

    transcription = transcribe_audio_bytes(audio_bytes, filename="test_spoken_sentence.wav")
    print(f"\n[STT Test] Reference: '{test_sentence}'")
    print(f"[STT Test] Transcribed: '{transcription}'")

    acc = compute_transcription_accuracy(test_sentence, transcription)
    print(f"[STT Test] Measured Accuracy: {acc['accuracy_pct']}% (WER: {acc['word_error_rate']})")

    assert acc["accuracy_pct"] >= 90.0, f"Transcription accuracy was {acc['accuracy_pct']}% (< 90%)"
    assert acc["word_error_rate"] <= 0.10


# ---------------- 2. Transcribe API Endpoint Test ----------------
def test_transcribe_api_endpoint(client: TestClient, student_user: User, student_auth_headers: dict):
    """
    Asserts:
      - POST /api/interview/transcribe returns 200 with transcription and word_count.
      - Rejects empty audio files with HTTP 400.
    """
    test_sentence = "I have built distributed systems with Python and React for three years."
    wav_path = _generate_test_speech_audio(test_sentence, "test_api_speech.wav")

    with open(wav_path, "rb") as f:
        audio_bytes = f.read()

    # 1. Successful transcription
    files = {"file": ("test_api_speech.wav", audio_bytes, "audio/wav")}
    resp = client.post("/api/interview/transcribe", files=files, headers=student_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "transcription" in data
    assert data["word_count"] >= 10
    assert "distributed systems" in data["transcription"].lower()

    # 2. Empty audio rejected
    empty_files = {"file": ("empty.wav", b"", "audio/wav")}
    empty_resp = client.post("/api/interview/transcribe", files=empty_files, headers=student_auth_headers)
    assert empty_resp.status_code == 400
    assert "empty" in empty_resp.json()["detail"].lower()


# ---------------- 3. Voice Message Interview Flow Test ----------------
def test_voice_message_interview_flow(
    client: TestClient,
    student_user: User,
    student_auth_headers: dict,
    db_session: Session,
):
    """
    Tests end-to-end voice interview turn:
      1. Student starts an interview simulation.
      2. Student speaks an answer via POST /api/interview/{id}/voice-message.
      3. Server transcribes audio using faster-whisper.
      4. Answer is graded against 4-dimension rubric.
      5. Interviewer replies with follow-up question.
      6. Transcription is preserved in session response.
    """
    profile = Profile(
        user_id=student_user.id,
        consent_given=True,
        target_roles=["Full Stack Software Engineer"],
        skills=["Python", "FastAPI", "React", "Docker"],
        projects=[{"title": "Readiness Copilot", "description": "Platform."}],
    )
    db_session.add(profile)
    db_session.commit()

    # Start session
    start_resp = client.post(
        "/api/interview/start",
        json={"duration_minutes": 15},
        headers=student_auth_headers,
    )
    assert start_resp.status_code == 200
    session_id = start_resp.json()["id"]

    # Synthesize spoken response
    answer_sentence = "I have built distributed systems with Python and React for three years."
    wav_path = _generate_test_speech_audio(answer_sentence, "student_answer_speech.wav")
    with open(wav_path, "rb") as f:
        audio_bytes = f.read()

    # Submit voice message
    files = {"file": ("student_answer.wav", audio_bytes, "audio/wav")}
    msg_resp = client.post(
        f"/api/interview/{session_id}/voice-message",
        files=files,
        headers=student_auth_headers,
    )
    assert msg_resp.status_code == 200
    res_data = msg_resp.json()

    # Verify transcription returned
    assert res_data["transcription"] is not None
    assert "distributed systems" in res_data["transcription"].lower()

    # Verify messages list contains the voice answer with evaluation
    messages = res_data["messages"]
    student_msgs = [m for m in messages if m["role"] == "student"]
    assert len(student_msgs) >= 1
    assert "evaluation" in student_msgs[0]
    assert student_msgs[0]["evaluation"]["score"] > 0
    assert len(student_msgs[0]["evaluation"]["criteria"]) == 4

    # Verify interviewer follow-up was generated
    interviewer_msgs = [m for m in messages if m["role"] == "interviewer"]
    assert len(interviewer_msgs) >= 2


# ---------------- 4. Silent / No-Speech Audio Handling Test ----------------
def test_voice_message_silent_audio_returns_clean_error(
    client: TestClient,
    student_user: User,
    student_auth_headers: dict,
    db_session: Session,
):
    """
    Asserts that uploading silent or inaudible audio returns a clean 400 error
    prompting the student to speak clearly or switch to text mode.
    """
    profile = Profile(
        user_id=student_user.id,
        consent_given=True,
        target_roles=["Full Stack Software Engineer"],
    )
    db_session.add(profile)
    db_session.commit()

    start_resp = client.post(
        "/api/interview/start",
        json={"duration_minutes": 15},
        headers=student_auth_headers,
    )
    session_id = start_resp.json()["id"]

    silent_bytes = _generate_silent_audio()
    files = {"file": ("silence.wav", silent_bytes, "audio/wav")}
    resp = client.post(
        f"/api/interview/{session_id}/voice-message",
        files=files,
        headers=student_auth_headers,
    )
    assert resp.status_code == 400
    assert "no speech could be detected" in resp.json()["detail"].lower()
