from __future__ import annotations
from typing import List, Dict, Any, Optional
import httpx
from app.llm.base import BaseLLMAdapter, LLMMessage, LLMResponse

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


class OpenAIAdapter(BaseLLMAdapter):
    """Adapter for OpenAI Chat Completions API."""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model or DEFAULT_OPENAI_MODEL, **kwargs)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

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

    def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        format_json: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        req = self._prepare_request(messages, temperature, format_json)
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/chat/completions", **req)
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

    async def agenerate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        format_json: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        req = self._prepare_request(messages, temperature, format_json)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/chat/completions", **req)
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
