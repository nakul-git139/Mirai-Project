from __future__ import annotations
import json
import pytest
from pydantic import BaseModel, Field
import httpx

from app.llm.base import LLMMessage
from app.llm.adapters.mock_adapter import MockLLMAdapter
from app.llm.adapters.ollama_adapter import OllamaAdapter
from app.llm.adapters.openai_adapter import OpenAIAdapter
from app.llm.adapters.claude_adapter import ClaudeAdapter
from app.llm.adapters.gemini_adapter import GeminiAdapter
from app.llm.structured import (
    generate_structured_output,
    StructuredOutputError,
    extract_json_from_text,
)


class SampleCheck(BaseModel):
    id: str
    label: str
    passed: bool
    evidence: str
    fix: str


class SampleReview(BaseModel):
    score: int = Field(ge=0, le=100)
    summary: str
    checks: list[SampleCheck]


def test_mock_adapter_basic():
    adapter = MockLLMAdapter(canned_response='{"status": "ok"}')
    res = adapter.generate([LLMMessage(role="user", content="Hello")])
    assert res.content == '{"status": "ok"}'
    assert res.provider == "mock"
    assert adapter.call_count == 1


def test_extract_json_helper():
    # Plain JSON
    assert extract_json_from_text('{"a": 1}') == '{"a": 1}'
    # Markdown codeblock
    assert extract_json_from_text('```json\n{"a": 2}\n```') == '{"a": 2}'
    # Markdown codeblock without json tag
    assert extract_json_from_text('Here is the json:\n```\n{"a": 3}\n```\nHope it helps!') == '{"a": 3}'
    # Text surrounding json
    assert extract_json_from_text('Intro text {"a": 4} outro text') == '{"a": 4}'


def test_structured_output_success_first_attempt():
    valid_data = {
        "score": 95,
        "summary": "Great resume structure",
        "checks": [
            {
                "id": "c1",
                "label": "Action verbs",
                "passed": True,
                "evidence": "Uses Developed, Led",
                "fix": "None needed",
            }
        ],
    }
    adapter = MockLLMAdapter(canned_response=json.dumps(valid_data))
    result = generate_structured_output(
        adapter=adapter,
        prompt="Review this resume",
        schema=SampleReview,
    )

    assert isinstance(result, SampleReview)
    assert result.score == 95
    assert len(result.checks) == 1
    assert result.checks[0].label == "Action verbs"
    assert adapter.call_count == 1


def test_structured_output_malformed_json_retry_success():
    """Test: malformed JSON on first turn triggers a corrective retry that succeeds on 2nd turn."""
    valid_data = {
        "score": 88,
        "summary": "Solid profile",
        "checks": [
            {
                "id": "c2",
                "label": "Contact links",
                "passed": True,
                "evidence": "GitHub link present",
                "fix": "Add LinkedIn link",
            }
        ],
    }
    # First response is malformed, second is valid JSON
    adapter = MockLLMAdapter(
        response_queue=[
            "SORRY, I CANNOT RETURN JSON RIGHT NOW {BROKEN_JSON",
            json.dumps(valid_data),
        ]
    )

    result = generate_structured_output(
        adapter=adapter,
        prompt="Review this resume",
        schema=SampleReview,
        max_retries=2,
    )

    assert isinstance(result, SampleReview)
    assert result.score == 88
    # Proves that retry occurred
    assert adapter.call_count == 2
    # Verify the second call received the correction message with schema error
    second_call_messages = adapter.received_messages[1]
    assert any("rejected due to this schema validation error" in m.content for m in second_call_messages)


def test_structured_output_persistent_malformed_raises_clear_schema_error():
    """Test: persistent invalid responses exhaust retries and raise clear StructuredOutputError."""
    adapter = MockLLMAdapter(
        response_queue=[
            "MALFORMED 1",
            "MALFORMED 2",
            "MALFORMED 3",
        ]
    )

    with pytest.raises(StructuredOutputError) as exc_info:
        generate_structured_output(
            adapter=adapter,
            prompt="Analyze",
            schema=SampleReview,
            max_retries=2,
        )

    err_msg = str(exc_info.value)
    assert "Failed to generate structured output for 'SampleReview'" in err_msg
    assert "after 3 attempts" in err_msg
    assert len(exc_info.value.errors) > 0


def test_structured_output_schema_field_validation_failure_retry():
    """Test: valid JSON but invalid schema fields (e.g. score > 100) triggers retry."""
    invalid_schema_data = {
        "score": 999,  # exceeds ge=0, le=100
        "summary": "Out of bounds score",
        "checks": [],
    }
    valid_data = {
        "score": 90,
        "summary": "Corrected score",
        "checks": [],
    }
    adapter = MockLLMAdapter(
        response_queue=[
            json.dumps(invalid_schema_data),
            json.dumps(valid_data),
        ]
    )

    result = generate_structured_output(
        adapter=adapter,
        prompt="Score candidate",
        schema=SampleReview,
        max_retries=2,
    )

    assert result.score == 90
    assert adapter.call_count == 2


def test_ollama_adapter_configuration():
    adapter = OllamaAdapter(
        model="llama3.2",
        base_url="http://localhost:11434/",
        num_ctx=8192,
    )
    assert adapter.base_url == "http://localhost:11434"
    assert adapter.num_ctx >= 8192

    # Check payload structure
    payload = adapter._prepare_payload(
        messages=[LLMMessage(role="user", content="Test")],
        format_json=True,
    )
    assert payload["format"] == "json"
    assert payload["options"]["num_ctx"] >= 8192
    assert payload["model"] == "llama3.2"


def test_ollama_adapter_unreachable_error_actionable():
    """When Ollama is not reachable, returns clear error telling user to run 'ollama serve'."""
    adapter = OllamaAdapter(
        model="llama3.2",
        base_url="http://127.0.0.1:54321",  # Unused port
        timeout=1.0,
    )
    with pytest.raises(RuntimeError) as exc_info:
        adapter.generate([LLMMessage(role="user", content="Hi")])

    err_str = str(exc_info.value)
    assert "Ollama is not running" in err_str
    assert "ollama serve" in err_str


def test_ollama_adapter_model_missing_error_actionable():
    """When model is missing, returns clear error telling user to run 'ollama pull <model>'."""
    adapter = OllamaAdapter(model="nonexistent-model-xyz", base_url="http://localhost:11434")

    # Mock 404 response
    req = httpx.Request("POST", "http://localhost:11434/api/chat")
    resp = httpx.Response(status_code=404, request=req, text='{"error": "model nonexistent-model-xyz not found"}')
    http_error = httpx.HTTPStatusError("Not Found", request=req, response=resp)

    handled_exc = adapter._handle_error(http_error)
    assert isinstance(handled_exc, RuntimeError)
    assert "not found in Ollama" in str(handled_exc)
    assert "ollama pull nonexistent-model-xyz" in str(handled_exc)


def test_cloud_adapters_require_api_key():
    openai = OpenAIAdapter(model="gpt-4o-mini", api_key="")
    with pytest.raises(ValueError) as exc:
        openai.generate([LLMMessage(role="user", content="Hi")])
    assert "OpenAI API key is missing" in str(exc.value)

    claude = ClaudeAdapter(model="claude-3-5-sonnet", api_key="")
    with pytest.raises(ValueError) as exc:
        claude.generate([LLMMessage(role="user", content="Hi")])
    assert "Anthropic API key is missing" in str(exc.value)

    gemini = GeminiAdapter(model="gemini-1.5-flash", api_key="")
    with pytest.raises(ValueError) as exc:
        gemini.generate([LLMMessage(role="user", content="Hi")])
    assert "Gemini API key is missing" in str(exc.value)
