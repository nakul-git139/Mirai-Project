from __future__ import annotations
from typing import List, Dict, Any, Optional
import time
import asyncio
import random
import logging
import httpx
from app.llm.base import (
    BaseLLMAdapter,
    LLMMessage,
    LLMResponse,
    LLMProviderRateLimitError,
    LLMProviderTimeoutError,
    LLMProviderError,
    JobCancelledError,
)


logger = logging.getLogger(__name__)
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


class OpenAIAdapter(BaseLLMAdapter):
    """Adapter for OpenAI Chat Completions API with exponential backoff for 429 and timeouts."""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 60.0,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model or DEFAULT_OPENAI_MODEL, **kwargs)
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
                "OpenAI API key is missing. Please configure it in Settings."
            )

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }

        if format_json:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        return {"headers": headers, "json": payload}

    def _calculate_backoff(self, attempt: int, response: Optional[httpx.Response] = None) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After")
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
        from app.services.job_queue import get_current_job_handle
        handle = get_current_job_handle()

        while True:
            if handle and handle.is_cancelled():
                raise JobCancelledError("Job was cancelled before OpenAI request.")

            try:
                with httpx.Client(timeout=self.timeout) as client:
                    if handle:
                        handle.set_active_client(client)
                    try:
                        response = client.post(f"{self.base_url}/chat/completions", **req)
                    finally:
                        if handle:
                            handle.clear_active_client(client)

                    if response.status_code == 429:
                        if attempt < self.max_retries:
                            delay = self._calculate_backoff(attempt, response)
                            logger.warning(f"OpenAI 429 Rate Limit (attempt {attempt+1}/{self.max_retries}). Backing off for {delay:.2f}s...")
                            if handle and handle.wait_or_cancelled(delay):
                                raise JobCancelledError("Job was cancelled during rate limit backoff.")
                            elif not handle:
                                time.sleep(delay)
                            attempt += 1
                            continue
                        raise LLMProviderRateLimitError(
                            "Hosted provider rate limit exceeded (HTTP 429). Exponential backoff exhausted. Please try again in a few minutes."
                        )
                    response.raise_for_status()
                    data = response.json()
                    choice = data["choices"][0]
                    return LLMResponse(
                        content=choice["message"]["content"],
                        provider="openai",
                        model=self.model,
                        raw_response=data,
                        usage=data.get("usage"),
                    )
            except httpx.TimeoutException as exc:
                if handle and handle.is_cancelled():
                    raise JobCancelledError("Job was cancelled during timeout.") from exc
                if attempt < self.max_retries:
                    delay = self._calculate_backoff(attempt)
                    logger.warning(f"OpenAI request timeout (attempt {attempt+1}/{self.max_retries}). Backing off for {delay:.2f}s...")
                    if handle and handle.wait_or_cancelled(delay):
                        raise JobCancelledError("Job was cancelled during timeout backoff.")
                    elif not handle:
                        time.sleep(delay)
                    attempt += 1
                    continue
                raise LLMProviderTimeoutError(
                    f"Hosted provider (OpenAI) request timed out after {self.timeout}s ({attempt} retries)."
                ) from exc
            except (JobCancelledError, LLMProviderRateLimitError, LLMProviderTimeoutError, ValueError):
                raise
            except Exception as exc:
                if handle and handle.is_cancelled():
                    raise JobCancelledError("Job was cancelled during API call.") from exc
                raise LLMProviderError(f"OpenAI API call failed: {exc}") from exc

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
                    response = await client.post(f"{self.base_url}/chat/completions", **req)
                    if response.status_code == 429:
                        if attempt < self.max_retries:
                            delay = self._calculate_backoff(attempt, response)
                            logger.warning(f"OpenAI 429 Rate Limit (attempt {attempt+1}/{self.max_retries}). Backing off for {delay:.2f}s...")
                            await asyncio.sleep(delay)
                            attempt += 1
                            continue
                        raise LLMProviderRateLimitError(
                            "Hosted provider rate limit exceeded (HTTP 429). Exponential backoff exhausted. Please try again in a few minutes."
                        )
                    response.raise_for_status()
                    data = response.json()
                    choice = data["choices"][0]
                    return LLMResponse(
                        content=choice["message"]["content"],
                        provider="openai",
                        model=self.model,
                        raw_response=data,
                        usage=data.get("usage"),
                    )
            except httpx.TimeoutException as exc:
                if attempt < self.max_retries:
                    delay = self._calculate_backoff(attempt)
                    logger.warning(f"OpenAI request timeout (attempt {attempt+1}/{self.max_retries}). Backing off for {delay:.2f}s...")
                    await asyncio.sleep(delay)
                    attempt += 1
                    continue
                raise LLMProviderTimeoutError(
                    f"Hosted provider (OpenAI) request timed out after {self.timeout}s ({attempt} retries)."
                ) from exc
            except (LLMProviderRateLimitError, LLMProviderTimeoutError, ValueError):
                raise
            except Exception as exc:
                raise LLMProviderError(f"OpenAI API call failed: {exc}") from exc

