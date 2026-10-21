from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from app import config
from app.config import SETTINGS_FILE_PATH
from app.logging_config import register_secret_for_redaction


def get_default_settings() -> Dict[str, Any]:
    base_url = os.environ.get("OLLAMA_BASE_URL", config.DEFAULT_OLLAMA_BASE_URL)
    model = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
    provider = os.environ.get("DEFAULT_LLM_PROVIDER") or os.environ.get("LLM_PROVIDER", "ollama")
    return {
        "provider": provider,
        "model": model,
        "ollama_base_url": base_url,
        "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
        "claude_api_key": os.environ.get("CLAUDE_API_KEY", ""),
        "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
        "github_token": os.environ.get("GITHUB_TOKEN", ""),
        "concurrency_limits": config.DEFAULT_CONCURRENCY_LIMITS.copy(),
        "rate_limit_reviews_per_hour": config.DEFAULT_RATE_LIMIT_REVIEWS_PER_HOUR,
        "rate_limit_window_seconds": config.DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
    }


DEFAULT_SETTINGS: Dict[str, Any] = get_default_settings()

DEFAULT_MODELS: Dict[str, str] = {
    "ollama": os.environ.get("OLLAMA_MODEL", "qwen2.5:3b"),
    "openai": "gpt-4o-mini",
    "claude": "claude-3-5-sonnet-20241022",
    "gemini": "gemini-1.5-flash",
    "mock": "mock-model",
}

AVAILABLE_PROVIDERS = ["ollama", "openai", "claude", "gemini", "mock"]


def load_raw_settings() -> Dict[str, Any]:
    """Load settings from local JSON file. Creates file with defaults if absent."""
    defaults = get_default_settings()
    if not SETTINGS_FILE_PATH.exists():
        save_raw_settings(defaults)
        return defaults.copy()

    try:
        with open(SETTINGS_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}

    merged = defaults.copy()
    merged.update(data)
    if os.environ.get("LLM_PROVIDER"):
        merged["provider"] = os.environ.get("LLM_PROVIDER")

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


def check_ollama_connectivity(base_url: str, timeout: float = 1.5) -> Tuple[bool, str]:
    """
    Fast fail-check for remote/local Ollama connectivity.
    Returns (True, "") if reachable, or (False, error_reason) if unreachable.
    """
    if not base_url or not base_url.strip():
        return False, "Ollama base URL is empty. Please configure a valid host in Settings."

    url = base_url.strip().rstrip("/")
    if "<" in url or ">" in url or "placeholder" in url.lower():
        return False, f"Ollama base URL contains placeholder '{base_url}'. Please update Settings with a valid host IP."

    import httpx
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(f"{url}/api/tags")
            if resp.status_code == 200:
                return True, ""
            return False, f"Ollama returned HTTP {resp.status_code} at {url}."
    except Exception as e:
        return False, f"Remote Ollama host at '{url}' is unreachable ({type(e).__name__}). Please verify the Ollama machine is running on your network."


def get_public_settings() -> Dict[str, Any]:
    """Return sanitized settings suitable for frontend API responses - strictly ZERO API keys."""
    raw = load_raw_settings()
    env_provider = os.environ.get("LLM_PROVIDER")
    return {
        "provider": raw.get("provider", "ollama"),
        "model": raw.get("model", "qwen2.5:3b"),
        "ollama_base_url": raw.get("ollama_base_url", config.DEFAULT_OLLAMA_BASE_URL),
        "has_openai_key": bool(raw.get("openai_api_key")),
        "has_claude_key": bool(raw.get("claude_api_key")),
        "has_gemini_key": bool(raw.get("gemini_api_key")),
        "has_github_token": bool(raw.get("github_token")),
        "available_providers": AVAILABLE_PROVIDERS,
        "default_models": DEFAULT_MODELS,
        "concurrency_limits": raw.get("concurrency_limits", config.DEFAULT_CONCURRENCY_LIMITS),
        "rate_limit_reviews_per_hour": raw.get("rate_limit_reviews_per_hour", config.DEFAULT_RATE_LIMIT_REVIEWS_PER_HOUR),
        "enable_mock_interview": getattr(config, "ENABLE_MOCK_INTERVIEW", False),
        "env_forced": bool(env_provider),
        "env_forced_provider": env_provider,
    }
