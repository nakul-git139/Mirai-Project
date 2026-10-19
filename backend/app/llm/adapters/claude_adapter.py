from __future__ import annotations
from typing import List, Dict, Any, Optional
import time
import asyncio
import random
import logging
from app.llm.base import (
    BaseLLMAdapter,
    LLMMessage,
    LLMResponse,
    LLMProviderRateLimitError,
    LLMProviderTimeoutError,
    LLMProviderError,
)

logger = logging.getLogger(__name__)
DEFAULT_CLAUDE_MODEL = "claude-3-5-sonnet-20241022"


class ClaudeAdapter(BaseLLMAdapter):
    """Adapter for Anthropic Claude Messages API with exponential backoff for 429 and timeouts."""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: str = "https://api.anthropic.com/v1",
        timeout: float = 60.0,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model or DEFAULT_CLAUDE_MODEL, **kwargs)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base

    def _prepare_request(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        format_json: bool = False,
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError(
                "Anthropic API key is missing. Please configure it in Settings."
            )

        system_prompts: List[str] = []
        anthropic_messages: List[Dict[str, str]] = []

        for m in messages:
            if m.role == "system":
                system_prompts.append(m.content)
            else:
                anthropic_messages.append({"role": m.role, "content": m.content})

        if format_json:
            system_prompts.append("You MUST respond ONLY with valid, parseable JSON. Do not include markdown code block formatting or explanation.")

        payload: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "temperature": temperature,
            "messages": anthropic_messages,
        }

        if system_prompts:
            payload["system"] = "\n\n".join(system_prompts)

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        return {"headers": headers, "json": payload}

    def _calculate_backoff(self, attempt: int, response: Optional[httpx.Response] = None) -> float:
        if response is not None:
            retry_after = response.headers.get("retry-after")
            if retry_after:
                try:
                    return min(float(retry_after), 15.0)
                except ValueError:
                    pass
        jitter = random.uniform(0.05, 0.25)
        return min(self.backoff_base * (2 ** attempt) + jitter, 15.0)

    def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        format_json: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        req = self._prepare_request(messages, temperature, format_json)
        attempt = 0

        while True:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(f"{self.base_url}/messages", **req)
                    if response.status_code == 429:
                        if attempt < self.max_retries:
                            delay = self._calculate_backoff(attempt, response)
                            logger.warning(f"Claude 429 Rate Limit (attempt {attempt+1}/{self.max_retries}). Backing off for {delay:.2f}s...")
                            time.sleep(delay)
                            attempt += 1
                            continue
                        raise LLMProviderRateLimitError(
                            "Hosted provider rate limit exceeded (HTTP 429). Exponential backoff exhausted. Please try again in a few minutes."
                        )
                    response.raise_for_status()
                    data = response.json()

                    content_blocks = data.get("content", [])
                    text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")

                    return LLMResponse(
                        content=text,
                        provider="claude",
                        model=self.model,
                        raw_response=data,
                        usage=data.get("usage"),
                    )
            except httpx.TimeoutException as exc:
                if attempt < self.max_retries:
                    delay = self._calculate_backoff(attempt)
                    logger.warning(f"Claude request timeout (attempt {attempt+1}/{self.max_retries}). Backing off for {delay:.2f}s...")
                    time.sleep(delay)
                    attempt += 1
                    continue
                raise LLMProviderTimeoutError(
                    f"Hosted provider (Claude) request timed out after {self.timeout}s ({attempt} retries)."
                ) from exc
            except (LLMProviderRateLimitError, LLMProviderTimeoutError, ValueError):
                raise
            except Exception as exc:
                raise LLMProviderError(f"Claude API call failed: {exc}") from exc

    async def agenerate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        format_json: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        req = self._prepare_request(messages, temperature, format_json)
        attempt = 0

        while True:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(f"{self.base_url}/messages", **req)
                    if response.status_code == 429:
                        if attempt < self.max_retries:
                            delay = self._calculate_backoff(attempt, response)
                            logger.warning(f"Claude 429 Rate Limit (attempt {attempt+1}/{self.max_retries}). Backing off for {delay:.2f}s...")
                            await asyncio.sleep(delay)
                            attempt += 1
                            continue
                        raise LLMProviderRateLimitError(
                            "Hosted provider rate limit exceeded (HTTP 429). Exponential backoff exhausted. Please try again in a few minutes."
                        )
                    response.raise_for_status()
                    data = response.json()

                    content_blocks = data.get("content", [])
                    text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")

                    return LLMResponse(
                        content=text,
                        provider="claude",
                        model=self.model,
                        raw_response=data,
                        usage=data.get("usage"),
                    )
            except httpx.TimeoutException as exc:
                if attempt < self.max_retries:
                    delay = self._calculate_backoff(attempt)
                    logger.warning(f"Claude request timeout (attempt {attempt+1}/{self.max_retries}). Backing off for {delay:.2f}s...")
                    await asyncio.sleep(delay)
                    attempt += 1
                    continue
                raise LLMProviderTimeoutError(
                    f"Hosted provider (Claude) request timed out after {self.timeout}s ({attempt} retries)."
                ) from exc
            except (LLMProviderRateLimitError, LLMProviderTimeoutError, ValueError):
                raise
            except Exception as exc:
                raise LLMProviderError(f"Claude API call failed: {exc}") from exc

