from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, Optional

from app.config import SETTINGS_FILE_PATH
from app.logging_config import register_secret_for_redaction

DEFAULT_SETTINGS: Dict[str, Any] = {
    "provider": "ollama",
    "model": "llama3.2",
    "ollama_base_url": "http://localhost:11434",
    "openai_api_key": "",
    "claude_api_key": "",
    "gemini_api_key": "",
    "github_token": "",
}

DEFAULT_MODELS: Dict[str, str] = {
    "ollama": "llama3.2",
    "openai": "gpt-4o-mini",
    "claude": "claude-3-5-sonnet-20241022",
    "gemini": "gemini-1.5-flash",
    "mock": "mock-model",
}

AVAILABLE_PROVIDERS = ["ollama", "openai", "claude", "gemini", "mock"]


def load_raw_settings() -> Dict[str, Any]:
    """Load settings from local JSON file. Creates file with defaults if absent."""
    if not SETTINGS_FILE_PATH.exists():
        save_raw_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()

    try:
        with open(SETTINGS_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}

    merged = DEFAULT_SETTINGS.copy()
    merged.update(data)

    # Register any present keys for logging redaction
    for key in ("openai_api_key", "claude_api_key", "gemini_api_key", "github_token"):
        val = merged.get(key)
        if val:
            register_secret_for_redaction(val)

    return merged


def save_raw_settings(settings_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Persist settings to local JSON file and register keys for log redacting."""
    SETTINGS_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Register keys for log sanitization
    for key in ("openai_api_key", "claude_api_key", "gemini_api_key", "github_token"):
        val = settings_dict.get(key)
        if val:
            register_secret_for_redaction(val)

    with open(SETTINGS_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(settings_dict, f, indent=2)

    return settings_dict


def get_public_settings() -> Dict[str, Any]:
    """Return sanitized settings suitable for frontend API responses - strictly ZERO API keys."""
    raw = load_raw_settings()
    return {
        "provider": raw.get("provider", "ollama"),
        "model": raw.get("model", "llama3.2"),
        "ollama_base_url": raw.get("ollama_base_url", "http://localhost:11434"),
        "has_openai_key": bool(raw.get("openai_api_key")),
        "has_claude_key": bool(raw.get("claude_api_key")),
        "has_gemini_key": bool(raw.get("gemini_api_key")),
        "has_github_token": bool(raw.get("github_token")),
        "available_providers": AVAILABLE_PROVIDERS,
        "default_models": DEFAULT_MODELS,
    }

