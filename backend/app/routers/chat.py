from __future__ import annotations
import shutil
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR
from app.database import get_db
from app.models import User
from app.auth import get_current_user
from app.schemas import ChatRequest, ChatResponse
from app.llm.factory import get_llm_adapter
from app.llm.base import LLMMessage

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
def send_chat_message(
    req: ChatRequest,
    current_user: Optional[User] = Depends(get_current_user),
):
    """Chat endpoint communicating with the active LLM adapter."""
    adapter = get_llm_adapter()

    messages = [
        LLMMessage(
            role="system",
            content=(
                "You are the Placement Readiness Copilot for MSOT students. "
                "Help students benchmark and improve their resumes, LinkedIn, GitHub, "
                "LeetCode practice, and prepare for interviews with specific, actionable advice."
            ),
        )
    ]

    for hist in req.conversation_history:
        messages.append(LLMMessage(role=hist.role, content=hist.content))

    messages.append(LLMMessage(role="user", content=req.message))

    try:
        response = adapter.generate(messages=messages, temperature=0.2)
        return ChatResponse(
            reply=response.content,
            provider=adapter.__class__.__name__,
            model=adapter.model,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: Optional[User] = Depends(get_current_user),
):
    """File upload endpoint for resumes and project documents."""
    filename = Path(file.filename).name
    destination = UPLOAD_DIR / filename

    with open(destination, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "status": "success",
        "filename": filename,
        "size_bytes": destination.stat().st_size,
        "message": f"Successfully received {filename}",
    }
