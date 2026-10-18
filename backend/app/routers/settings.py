from __future__ import annotations
from fastapi import APIRouter, HTTPException, status
from app.schemas import (
    SettingsUpdate,
    SettingsResponse,
    ConnectionTestRequest,
    ConnectionTestResponse,
)
from app.services.settings_service import (
    load_raw_settings,
    save_raw_settings,
    get_public_settings,
)
from app.llm.factory import get_llm_adapter
from app.llm.base import LLMMessage

router = APIRouter(prefix="/api/settings", tags=["Settings"])


@router.get("", response_model=SettingsResponse)
def get_settings():
    """Retrieve sanitized settings - strictly zero API keys are returned."""
    return get_public_settings()


@router.post("", response_model=SettingsResponse)
def update_settings(updates: SettingsUpdate):
    """
    Update local provider configuration and API keys.
    Keys are stored in local JSON, registered for log redacting,
    and NEVER returned in the response payload.
    """
    current = load_raw_settings()

    if updates.provider is not None:
        current["provider"] = updates.provider
    if updates.model is not None:
        current["model"] = updates.model
    if updates.ollama_base_url is not None:
        current["ollama_base_url"] = updates.ollama_base_url
    if updates.openai_api_key is not None:
        current["openai_api_key"] = updates.openai_api_key
    if updates.claude_api_key is not None:
        current["claude_api_key"] = updates.claude_api_key
    if updates.gemini_api_key is not None:
        current["gemini_api_key"] = updates.gemini_api_key

    save_raw_settings(current)
    return get_public_settings()


@router.post("/test-connection", response_model=ConnectionTestResponse)
def test_connection(req: ConnectionTestRequest):
    """Test connectivity to the selected LLM provider and model."""
    provider = req.provider or load_raw_settings().get("provider", "ollama")
    model = req.model

    try:
        adapter = get_llm_adapter(provider=provider, model=model)
        # Test prompt
        test_messages = [LLMMessage(role="user", content="Ping. Respond with 'pong'.")]
        response = adapter.generate(messages=test_messages, temperature=0.0)
        return ConnectionTestResponse(
            success=True,
            provider=provider,
            model=adapter.model,
            message=f"Connection successful! Response: {response.content[:100]}",
        )
    except Exception as exc:
        return ConnectionTestResponse(
            success=False,
            provider=provider,
            model=model or "unknown",
            message=str(exc),
        )
