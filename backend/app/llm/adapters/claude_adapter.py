from __future__ import annotations
from typing import List, Dict, Any, Optional
import httpx
from app.llm.base import BaseLLMAdapter, LLMMessage, LLMResponse

DEFAULT_CLAUDE_MODEL = "claude-3-5-sonnet-20241022"


class ClaudeAdapter(BaseLLMAdapter):
    """Adapter for Anthropic Claude Messages API."""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: str = "https://api.anthropic.com/v1",
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model or DEFAULT_CLAUDE_MODEL, **kwargs)
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

    def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        format_json: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        req = self._prepare_request(messages, temperature, format_json)
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/messages", **req)
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

    async def agenerate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        format_json: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        req = self._prepare_request(messages, temperature, format_json)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/messages", **req)
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
