from __future__ import annotations
import os
import logging
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.logging_config import SensitiveDataFilter, register_secret_for_redaction
from app.config import resolve_secret_key


def test_settings_retrieval_contains_no_raw_keys(client: TestClient):
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()

    assert "provider" in data
    assert "model" in data
    assert "ollama_base_url" in data
    assert "has_openai_key" in data
    assert "has_claude_key" in data
    assert "has_gemini_key" in data

    # Strictly confirm no raw secret fields exist in response
    assert "openai_api_key" not in data
    assert "claude_api_key" not in data
    assert "gemini_api_key" not in data


def test_settings_update_persists_without_leaking_key(client: TestClient):
    # Assemble test secret dynamically at runtime
    secret_key = "sk-" + "test-secret-never-expose-in-api-" + "12345"

    update_payload = {
        "provider": "openai",
        "model": "gpt-4o",
        "openai_api_key": secret_key,
    }

    # Post new settings
    res = client.post("/api/settings", json=update_payload)
    assert res.status_code == 200
    data = res.json()

    assert data["provider"] == "openai"
    assert data["model"] == "gpt-4o"
    assert data["has_openai_key"] is True

    # Assert secret string is nowhere in JSON response body
    raw_response_text = res.text
    assert secret_key not in raw_response_text
    assert "openai_api_key" not in data


def test_log_sanitizer_redacts_api_keys():
    test_key = "sk-" + "test-secret-key-super-" + "confidential"
    register_secret_for_redaction(test_key)

    filter_obj = SensitiveDataFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg=f"Connecting with API key: {test_key}",
        args=(),
        exc_info=None,
    )

    filter_obj.filter(record)
    assert test_key not in record.msg
    assert "[REDACTED_API_KEY]" in record.msg or "[REDACTED_SECRET]" in record.msg


def test_test_connection_mock(client: TestClient):
    res = client.post(
        "/api/settings/test-connection",
        json={"provider": "mock", "model": "mock-test"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["provider"] == "mock"


def test_production_startup_fails_without_secret_key(monkeypatch):
    """Verify that when APP_ENV=production and SECRET_KEY is missing, application startup fails."""
    monkeypatch.delenv("SECRET_KEY", raising=False)
    fake_env = Path("/tmp/nonexistent_test_env_1")
    fake_backend_env = Path("/tmp/nonexistent_test_env_2")

    with pytest.raises(RuntimeError) as exc_info:
        resolve_secret_key(
            app_env="production",
            env_file=fake_env,
            backend_env_file=fake_backend_env,
        )
    assert "SECRET_KEY environment variable is required when APP_ENV=production" in str(exc_info.value)


def test_compromised_legacy_key_rejected(monkeypatch):
    """Verify that the deprecated, compromised development key is rejected with a fatal error."""
    compromised_key = "mirai_" + "placement_copilot_secret_jwt_key_2026"
    monkeypatch.setenv("SECRET_KEY", compromised_key)

    with pytest.raises(RuntimeError) as exc_info:
        resolve_secret_key(app_env="development")
    assert "matches the deprecated, compromised default key" in str(exc_info.value)
