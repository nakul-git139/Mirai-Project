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
DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"


class GeminiAdapter(BaseLLMAdapter):
    """Adapter for Google Gemini REST API with exponential backoff for 429 and timeouts."""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout: float = 60.0,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model or DEFAULT_GEMINI_MODEL, **kwargs)
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
                "Gemini API key is missing. Please configure it in Settings."
            )

        contents: List[Dict[str, Any]] = []
        system_instruction: Optional[Dict[str, Any]] = None

        for m in messages:
            if m.role == "system":
                system_instruction = {"parts": [{"text": m.content}]}
            else:
                role = "model" if m.role == "assistant" else "user"
                contents.append({"role": role, "parts": [{"text": m.content}]})

        generation_config: Dict[str, Any] = {
            "temperature": temperature,
        }

        if format_json:
            generation_config["responseMimeType"] = "application/json"

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": generation_config,
        }

        if system_instruction:
            payload["systemInstruction"] = system_instruction

        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        return {"url": url, "json": payload}

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
                    response = client.post(req["url"], json=req["json"])
                    if response.status_code == 429:
                        if attempt < self.max_retries:
                            delay = self._calculate_backoff(attempt, response)
                            logger.warning(f"Gemini 429 Rate Limit (attempt {attempt+1}/{self.max_retries}). Backing off for {delay:.2f}s...")
                            time.sleep(delay)
                            attempt += 1
                            continue
                        raise LLMProviderRateLimitError(
                            "Hosted provider rate limit exceeded (HTTP 429). Exponential backoff exhausted. Please try again in a few minutes."
                        )
                    response.raise_for_status()
                    data = response.json()

                    candidates = data.get("candidates", [])
                    text = ""
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text = "".join(p.get("text", "") for p in parts)

                    return LLMResponse(
                        content=text,
                        provider="gemini",
                        model=self.model,
                        raw_response=data,
                        usage=data.get("usageMetadata"),
                    )
            except httpx.TimeoutException as exc:
                if attempt < self.max_retries:
                    delay = self._calculate_backoff(attempt)
                    logger.warning(f"Gemini request timeout (attempt {attempt+1}/{self.max_retries}). Backing off for {delay:.2f}s...")
                    time.sleep(delay)
                    attempt += 1
                    continue
                raise LLMProviderTimeoutError(
                    f"Hosted provider (Gemini) request timed out after {self.timeout}s ({attempt} retries)."
                ) from exc
            except (LLMProviderRateLimitError, LLMProviderTimeoutError, ValueError):
                raise
            except Exception as exc:
                raise LLMProviderError(f"Gemini API call failed: {exc}") from exc

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
                    response = await client.post(req["url"], json=req["json"])
                    if response.status_code == 429:
                        if attempt < self.max_retries:
                            delay = self._calculate_backoff(attempt, response)
                            logger.warning(f"Gemini 429 Rate Limit (attempt {attempt+1}/{self.max_retries}). Backing off for {delay:.2f}s...")
                            await asyncio.sleep(delay)
                            attempt += 1
                            continue
                        raise LLMProviderRateLimitError(
                            "Hosted provider rate limit exceeded (HTTP 429). Exponential backoff exhausted. Please try again in a few minutes."
                        )
                    response.raise_for_status()
                    data = response.json()

                    candidates = data.get("candidates", [])
                    text = ""
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text = "".join(p.get("text", "") for p in parts)

                    return LLMResponse(
                        content=text,
                        provider="gemini",
                        model=self.model,
                        raw_response=data,
                        usage=data.get("usageMetadata"),
                    )
            except httpx.TimeoutException as exc:
                if attempt < self.max_retries:
                    delay = self._calculate_backoff(attempt)
                    logger.warning(f"Gemini request timeout (attempt {attempt+1}/{self.max_retries}). Backing off for {delay:.2f}s...")
                    await asyncio.sleep(delay)
                    attempt += 1
                    continue
                raise LLMProviderTimeoutError(
                    f"Hosted provider (Gemini) request timed out after {self.timeout}s ({attempt} retries)."
                ) from exc
            except (LLMProviderRateLimitError, LLMProviderTimeoutError, ValueError):
                raise
            except Exception as exc:
                raise LLMProviderError(f"Gemini API call failed: {exc}") from exc

