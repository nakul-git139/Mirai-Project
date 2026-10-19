from __future__ import annotations
from typing import Optional, Dict, Any

from app.llm.base import BaseLLMAdapter
from app.llm.adapters.ollama_adapter import OllamaAdapter
from app.llm.adapters.openai_adapter import OpenAIAdapter
from app.llm.adapters.claude_adapter import ClaudeAdapter
from app.llm.adapters.gemini_adapter import GeminiAdapter
from app.llm.adapters.mock_adapter import MockLLMAdapter
from app.services.settings_service import load_raw_settings, DEFAULT_MODELS


def get_llm_adapter(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    settings_override: Optional[Dict[str, Any]] = None,
) -> BaseLLMAdapter:
    """
    Factory function to instantiate the selected LLM provider adapter.
    Uses settings from data/settings.json unless overridden.
    """
    settings = load_raw_settings()
    if settings_override:
        settings.update(settings_override)

    active_provider = (provider or settings.get("provider") or "ollama").lower()
    saved_provider = settings.get("provider", "").lower()

    if model:
        active_model = model
    elif provider and provider.lower() != saved_provider:
        active_model = DEFAULT_MODELS.get(active_provider, "")
    else:
        active_model = settings.get("model") or DEFAULT_MODELS.get(active_provider, "")

    # Safety check: if provider is ollama and active_model is an openai/claude/gemini model, fallback to default ollama model
    if active_provider == "ollama" and ("gpt" in active_model.lower() or "claude" in active_model.lower() or "gemini" in active_model.lower()):
        active_model = DEFAULT_MODELS.get("ollama", "qwen2.5:3b")

    if active_provider == "ollama":
        base_url = settings.get("ollama_base_url", "http://localhost:11434")
        return OllamaAdapter(model=active_model, base_url=base_url)

    elif active_provider == "openai":
        api_key = settings.get("openai_api_key", "")
        return OpenAIAdapter(model=active_model, api_key=api_key)

    elif active_provider == "claude":
        api_key = settings.get("claude_api_key", "")
        return ClaudeAdapter(model=active_model, api_key=api_key)

    elif active_provider == "gemini":
        api_key = settings.get("gemini_api_key", "")
        return GeminiAdapter(model=active_model, api_key=api_key)

    elif active_provider == "mock":
        return MockLLMAdapter(model=active_model or "mock-model")

    else:
        raise ValueError(
            f"Unsupported LLM provider '{active_provider}'. Supported: ollama, openai, claude, gemini, mock"
        )
