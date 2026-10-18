from __future__ import annotations
from typing import List, Dict, Any, Optional
import httpx
from app.llm.base import BaseLLMAdapter, LLMMessage, LLMResponse

DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"


class GeminiAdapter(BaseLLMAdapter):
    """Adapter for Google Gemini REST API."""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model or DEFAULT_GEMINI_MODEL, **kwargs)
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

    def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        format_json: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        req = self._prepare_request(messages, temperature, format_json)
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(req["url"], json=req["json"])
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

    async def agenerate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        format_json: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        req = self._prepare_request(messages, temperature, format_json)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(req["url"], json=req["json"])
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
