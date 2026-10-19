from __future__ import annotations
import os
import json
import pytest
from pydantic import BaseModel, Field

from app.llm.adapters.ollama_adapter import OllamaAdapter
from app.llm.adapters.mock_adapter import MockLLMAdapter
from app.llm.base import LLMMessage
from app.llm.structured import generate_structured_output, StructuredOutputError
from app.services.settings_service import load_raw_settings, get_default_settings
from app.services.timing_logger import log_llm_timing, get_recent_timing_logs
from app.services.live_link_checker import generate_live_link_summary
from app.services.job_discovery.ranker import generate_job_match_explanation


class DummyOutputSchema(BaseModel):
    status: str = Field(description="status flag")
    count: int = Field(description="item count")


def test_ollama_payload_options_and_keep_alive():
    """Verify temperature 0, seed 42, num_ctx 8192, and keep_alive '60m' are injected."""
    adapter = OllamaAdapter(
        model="qwen2.5:3b",
        base_url="http://localhost:11434",
        seed=42,
        num_ctx=8192,
        keep_alive="60m",
    )
    messages = [LLMMessage(role="user", content="Hello")]
    payload = adapter._prepare_payload(messages, temperature=0.0, format_json=True, num_predict=150)

    assert payload["model"] == "qwen2.5:3b"
    assert payload["keep_alive"] == "60m"
    assert payload["format"] == "json"
    assert payload["options"]["temperature"] == 0.0
    assert payload["options"]["seed"] == 42
    assert payload["options"]["num_ctx"] == 8192
    assert payload["options"]["num_predict"] == 150


def test_ollama_base_url_and_model_configurable_via_env(monkeypatch):
    """Verify OLLAMA_BASE_URL and OLLAMA_MODEL environment variables are respected."""
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama-test-host:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:3b")

    defaults = get_default_settings()
    assert defaults["ollama_base_url"] == "http://ollama-test-host:11434"
    assert defaults["model"] == "qwen2.5:3b"


def test_timing_logger_records_to_db_and_file():
    """Verify log_llm_timing successfully records metrics to SQLite and file."""
    log_llm_timing(
        feature="test_robustness_feature",
        provider="ollama",
        model="qwen2.5:3b",
        prompt_tokens=120,
        output_tokens=45,
        duration_seconds=2.45,
        status="success",
        metadata={"test_run": True},
    )

    logs = get_recent_timing_logs(limit=10)
    assert len(logs) > 0
    latest = logs[0]
    assert latest["feature"] == "test_robustness_feature"
    assert latest["provider"] == "ollama"
    assert latest["model"] == "qwen2.5:3b"


def test_structured_output_retry_up_to_2_times():
    """Verify structured output retries up to 2 times on malformed JSON before succeeding."""
    mock_adapter = MockLLMAdapter(model="mock-retry")
    mock_adapter.set_queue([
        "Malformed invalid json text",
        '{"status": "recovered", "count": 10}',
    ])

    result: DummyOutputSchema = generate_structured_output(
        adapter=mock_adapter,
        prompt="Produce dummy output",
        schema=DummyOutputSchema,
        max_retries=2,
    )

    assert result.status == "recovered"
    assert result.count == 10
    assert mock_adapter.call_count == 2


def test_structured_output_exceeding_max_retries_raises_clear_error():
    """Verify structured output raises a clear error after exhausting retries."""
    mock_adapter = MockLLMAdapter(model="mock-fail")
    mock_adapter.set_queue([
        "Broken 1",
        "Broken 2",
        "Broken 3",
    ])

    with pytest.raises(StructuredOutputError) as exc_info:
        generate_structured_output(
            adapter=mock_adapter,
            prompt="Produce output",
            schema=DummyOutputSchema,
            max_retries=2,
        )

    assert "Failed to generate structured output" in str(exc_info.value)
    assert mock_adapter.call_count == 3


def test_live_link_summary_with_mock():
    """Verify live link summary generation works with structured schema."""
    mock_adapter = MockLLMAdapter(
        model="mock",
        canned_response='{"summary": "Live app loads cleanly with interactive UI.", "status_assessment": "production_ready"}',
    )
    result = generate_live_link_summary(
        url="https://demo.app",
        page_title="Copilot Demo",
        headings=["Home", "Dashboard"],
        status_code=200,
        console_errors=[],
        adapter=mock_adapter,
    )
    assert "production_ready" in result["status_assessment"]
    assert len(result["summary"]) > 0


def test_job_match_explanation_with_mock():
    """Verify job match explanation generation produces structured breakdown."""
    mock_adapter = MockLLMAdapter(
        model="mock",
        canned_response='{"match_summary": "Strong alignment with Python and React backend requirements.", "key_strengths": ["FastAPI", "PostgreSQL"], "missing_skills": ["Kubernetes"], "suggested_action": "Highlight containerization in capstone."}',
    )
    result = generate_job_match_explanation(
        job_title="Full Stack Engineer",
        job_skills=["Python", "FastAPI", "React", "Docker"],
        candidate_skills=["Python", "FastAPI", "React"],
        score=85,
        adapter=mock_adapter,
    )
    assert "FastAPI" in result["key_strengths"]
    assert "Kubernetes" in result["missing_skills"]


def test_timing_logs_endpoint_requires_admin(client, student_auth_headers, admin_auth_headers):
    """Verify GET /api/settings/timing-logs strictly enforces admin authentication."""
    # 1. Unauthenticated request -> 401
    r_unauth = client.get("/api/settings/timing-logs")
    assert r_unauth.status_code == 401, f"Expected 401, got {r_unauth.status_code}"

    # 2. Student request -> 403 Forbidden
    r_student = client.get("/api/settings/timing-logs", headers=student_auth_headers)
    assert r_student.status_code == 403, f"Expected 403, got {r_student.status_code}"

    # 3. Admin request -> 200 OK
    r_admin = client.get("/api/settings/timing-logs", headers=admin_auth_headers)
    assert r_admin.status_code == 200, f"Expected 200, got {r_admin.status_code}"
    assert isinstance(r_admin.json(), list)


@pytest.mark.live
def test_live_remote_ollama_connectivity_and_generation():
    """Live connectivity and generation verification against remote Ollama server (http://<OLLAMA_HOST>:11434)."""
    ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    adapter = OllamaAdapter(model="qwen2.5:3b", base_url=ollama_url, timeout=60.0)
    response = adapter.generate([LLMMessage(role="user", content="Ping test. Respond with 'READY'.")])
    assert len(response.content) > 0


@pytest.mark.live
def test_live_remote_ollama_structured_json():
    """Live structured JSON generation verification against remote Ollama."""
    ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    adapter = OllamaAdapter(model="qwen2.5:3b", base_url=ollama_url, timeout=60.0)
    result: DummyOutputSchema = generate_structured_output(
        adapter=adapter,
        prompt="Produce a JSON object with status 'active' and count 42.",
        schema=DummyOutputSchema,
        temperature=0.0,
    )
    assert result.status.lower() == "active"
    assert result.count == 42

