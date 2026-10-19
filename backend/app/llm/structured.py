from __future__ import annotations
import json
import re
import logging
from typing import Type, TypeVar, Optional, List, Any
from pydantic import BaseModel, ValidationError
from app.llm.base import BaseLLMAdapter, LLMMessage

logger = logging.getLogger(__name__)

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


def build_schema_instruction(schema: Type[T], base_system_prompt: Optional[str] = None) -> tuple[str, str]:
    """
    Builds a compact, high-precision instruction prompting the model to fill in a JSON instance.
    Critically, avoids dumping raw JSON Schema metakeys (e.g., 'properties', 'title') which
    causes small SLMs like qwen2.5:3b to hallucinate schema definitions rather than instances.
    Returns (sys_instruction, skeleton).
    """
    fields_desc = []
    if hasattr(schema, "model_fields"):
        for name, field in schema.model_fields.items():
            desc = field.description or name
            type_name = getattr(field.annotation, "__name__", str(field.annotation))
            fields_desc.append(f'  "{name}": <{type_name}: {desc}>')
        skeleton = "{\n" + ",\n".join(fields_desc) + "\n}"
    else:
        skeleton = json.dumps(schema.model_json_schema(), indent=2)

    sys_part = base_system_prompt or "You are a precise JSON-generating assistant."
    instruction = (
        f"{sys_part}\n\n"
        f"You MUST output a single valid JSON object with these EXACT keys:\n"
        f"{skeleton}\n\n"
        f"CRITICAL INSTRUCTIONS:\n"
        f"- Output ONLY the JSON object filling in the requested values.\n"
        f"- Do NOT output schema metadata like 'properties', 'title', or 'type'.\n"
        f"- Keep all string values concise, direct, and factual."
    )
    return instruction, skeleton


def generate_structured_output(
    adapter: BaseLLMAdapter,
    prompt: str,
    schema: Type[T],
    system_prompt: Optional[str] = None,
    max_retries: int = 2,
    temperature: float = 0.0,
    feature: Optional[str] = None,
    num_predict: Optional[int] = None,
    **kwargs: Any,
) -> T:
    """
    Synchronous structured output helper. Calls the adapter with temperature 0.0,
    validates the output against the Pydantic schema, and performs an automatic
    corrective retry loop if JSON is malformed, times out, or violates the schema.
    """
    sys_instruction, skeleton = build_schema_instruction(schema, system_prompt)

    messages: List[LLMMessage] = [
        LLMMessage(role="system", content=sys_instruction),
        LLMMessage(role="user", content=prompt),
    ]

    last_raw = ""
    last_error = ""
    feature_name = feature or f"structured_{schema.__name__.lower()}"

    for attempt in range(max_retries + 1):
        try:
            response = adapter.generate(
                messages=messages,
                temperature=temperature,
                format_json=True,
                feature=feature_name,
                num_predict=num_predict,
                **kwargs,
            )
            last_raw = response.content
        except (TimeoutError, RuntimeError) as exc:
            last_error = f"{type(exc).__name__}: {str(exc)}"
            logger.warning(f"Structured output attempt {attempt + 1}/{max_retries + 1} failed: {last_error}")
            if attempt < max_retries:
                continue
            raise StructuredOutputError(
                message=f"LLM request failed after {max_retries + 1} attempts due to: {last_error}",
                errors=[last_error],
                last_raw=last_raw,
            ) from exc

        try:
            cleaned = extract_json_from_text(last_raw)
            parsed_dict = json.loads(cleaned)
            return schema.model_validate(parsed_dict)
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            last_error = f"{type(exc).__name__}: {str(exc)}"
            logger.warning(
                f"Schema validation error on attempt {attempt + 1}/{max_retries + 1}: {last_error}"
            )

            if attempt < max_retries:
                messages.append(LLMMessage(role="assistant", content=last_raw))
                messages.append(
                    LLMMessage(
                        role="user",
                        content=(
                            f"Your previous response was rejected due to this schema validation error:\n"
                            f"{last_error}\n\n"
                            f"Please correct the error and output ONLY the valid JSON matching this structure:\n"
                            f"{skeleton}"
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
    feature: Optional[str] = None,
    num_predict: Optional[int] = None,
    **kwargs: Any,
) -> T:
    """
    Asynchronous structured output helper with retry, timeout protection, and schema validation.
    """
    sys_instruction, skeleton = build_schema_instruction(schema, system_prompt)

    messages: List[LLMMessage] = [
        LLMMessage(role="system", content=sys_instruction),
        LLMMessage(role="user", content=prompt),
    ]

    last_raw = ""
    last_error = ""
    feature_name = feature or f"structured_{schema.__name__.lower()}"

    for attempt in range(max_retries + 1):
        try:
            response = await adapter.agenerate(
                messages=messages,
                temperature=temperature,
                format_json=True,
                feature=feature_name,
                num_predict=num_predict,
                **kwargs,
            )
            last_raw = response.content
        except (TimeoutError, RuntimeError) as exc:
            last_error = f"{type(exc).__name__}: {str(exc)}"
            logger.warning(f"Async structured output attempt {attempt + 1}/{max_retries + 1} failed: {last_error}")
            if attempt < max_retries:
                continue
            raise StructuredOutputError(
                message=f"LLM request failed after {max_retries + 1} attempts due to: {last_error}",
                errors=[last_error],
                last_raw=last_raw,
            ) from exc

        try:
            cleaned = extract_json_from_text(last_raw)
            parsed_dict = json.loads(cleaned)
            return schema.model_validate(parsed_dict)
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            last_error = f"{type(exc).__name__}: {str(exc)}"
            logger.warning(
                f"Async schema validation error on attempt {attempt + 1}/{max_retries + 1}: {last_error}"
            )

            if attempt < max_retries:
                messages.append(LLMMessage(role="assistant", content=last_raw))
                messages.append(
                    LLMMessage(
                        role="user",
                        content=(
                            f"Your previous response was rejected due to this schema validation error:\n"
                            f"{last_error}\n\n"
                            f"Please correct the error and output ONLY the valid JSON matching this structure:\n"
                            f"{skeleton}"
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

