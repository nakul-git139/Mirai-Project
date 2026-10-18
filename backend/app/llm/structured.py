from __future__ import annotations
import json
import re
from typing import Type, TypeVar, Optional, List, Any
from pydantic import BaseModel, ValidationError
from app.llm.base import BaseLLMAdapter, LLMMessage

T = TypeVar("T", bound=BaseModel)


class StructuredOutputError(Exception):
    """Raised when an LLM fails to produce output conforming to the expected schema."""

    def __init__(
        self,
        message: str,
        errors: Optional[List[str]] = None,
        last_raw: str = "",
    ) -> None:
        super().__init__(message)
        self.errors = errors or []
        self.last_raw = last_raw


def extract_json_from_text(text: str) -> str:
    """Extract clean JSON string from raw model text, stripping markdown code fences."""
    text = text.strip()

    # If wrapped in markdown code fence, extract it
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if code_block_match:
        text = code_block_match.group(1).strip()

    # If text starts with something before the first '{' or '[', slice from there
    first_brace = text.find("{")
    first_bracket = text.find("[")
    starts = [idx for idx in [first_brace, first_bracket] if idx != -1]
    if starts:
        start_idx = min(starts)
        last_brace = text.rfind("}")
        last_bracket = text.rfind("]")
        ends = [idx for idx in [last_brace, last_bracket] if idx != -1]
        if ends:
            end_idx = max(ends) + 1
            text = text[start_idx:end_idx]

    return text


def generate_structured_output(
    adapter: BaseLLMAdapter,
    prompt: str,
    schema: Type[T],
    system_prompt: Optional[str] = None,
    max_retries: int = 2,
    temperature: float = 0.0,
) -> T:
    """
    Synchronous structured output helper. Calls the adapter with temperature 0.0,
    validates the output against the Pydantic schema, and performs an automatic
    corrective retry loop if JSON is malformed or violates the schema.
    """
    schema_json_str = json.dumps(schema.model_json_schema(), indent=2)
    sys_instruction = (
        f"{system_prompt or 'You are a precise JSON-generating assistant.'}\n\n"
        f"You MUST output valid, parseable JSON conforming strictly to this JSON schema:\n"
        f"{schema_json_str}\n\n"
        f"Do not include explanation, greetings, or markdown fences outside the JSON."
    )

    messages: List[LLMMessage] = [
        LLMMessage(role="system", content=sys_instruction),
        LLMMessage(role="user", content=prompt),
    ]

    last_raw = ""
    last_error = ""

    for attempt in range(max_retries + 1):
        response = adapter.generate(
            messages=messages,
            temperature=temperature,
            format_json=True,
        )
        last_raw = response.content

        try:
            cleaned = extract_json_from_text(last_raw)
            parsed_dict = json.loads(cleaned)
            return schema.model_validate(parsed_dict)
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            last_error = f"{type(exc).__name__}: {str(exc)}"

            if attempt < max_retries:
                # Add corrective turn for retry
                messages.append(LLMMessage(role="assistant", content=last_raw))
                messages.append(
                    LLMMessage(
                        role="user",
                        content=(
                            f"Your previous response was rejected due to this schema validation error:\n"
                            f"{last_error}\n\n"
                            f"Please correct the error and output ONLY the valid JSON matching the schema:\n"
                            f"{schema_json_str}"
                        ),
                    )
                )

    raise StructuredOutputError(
        message=(
            f"Failed to generate structured output for '{schema.__name__}' "
            f"after {max_retries + 1} attempts. Last schema error: {last_error}"
        ),
        errors=[last_error],
        last_raw=last_raw,
    )


async def agenerate_structured_output(
    adapter: BaseLLMAdapter,
    prompt: str,
    schema: Type[T],
    system_prompt: Optional[str] = None,
    max_retries: int = 2,
    temperature: float = 0.0,
) -> T:
    """
    Asynchronous structured output helper with retry and schema validation.
    """
    schema_json_str = json.dumps(schema.model_json_schema(), indent=2)
    sys_instruction = (
        f"{system_prompt or 'You are a precise JSON-generating assistant.'}\n\n"
        f"You MUST output valid, parseable JSON conforming strictly to this JSON schema:\n"
        f"{schema_json_str}\n\n"
        f"Do not include explanation, greetings, or markdown fences outside the JSON."
    )

    messages: List[LLMMessage] = [
        LLMMessage(role="system", content=sys_instruction),
        LLMMessage(role="user", content=prompt),
    ]

    last_raw = ""
    last_error = ""

    for attempt in range(max_retries + 1):
        response = await adapter.agenerate(
            messages=messages,
            temperature=temperature,
            format_json=True,
        )
        last_raw = response.content

        try:
            cleaned = extract_json_from_text(last_raw)
            parsed_dict = json.loads(cleaned)
            return schema.model_validate(parsed_dict)
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            last_error = f"{type(exc).__name__}: {str(exc)}"

            if attempt < max_retries:
                messages.append(LLMMessage(role="assistant", content=last_raw))
                messages.append(
                    LLMMessage(
                        role="user",
                        content=(
                            f"Your previous response was rejected due to this schema validation error:\n"
                            f"{last_error}\n\n"
                            f"Please correct the error and output ONLY the valid JSON matching the schema:\n"
                            f"{schema_json_str}"
                        ),
                    )
                )

    raise StructuredOutputError(
        message=(
            f"Failed to generate structured output for '{schema.__name__}' "
            f"after {max_retries + 1} attempts. Last schema error: {last_error}"
        ),
        errors=[last_error],
        last_raw=last_raw,
    )
