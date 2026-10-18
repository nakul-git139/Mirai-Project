from __future__ import annotations
from typing import List, Dict, Any, Optional
import httpx
from app.llm.base import BaseLLMAdapter, LLMMessage, LLMResponse

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_TIMEOUT_SECONDS = 120.0
DEFAULT_NUM_CTX = 8192


class OllamaAdapter(BaseLLMAdapter):
    """
    Adapter for local Ollama instances.
    Enforces num_ctx >= 8192, format='json' when requested, long timeouts,
    and returns actionable error messages if Ollama is not running or model is missing.
    """

    def __init__(
        self,
        model: str,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        num_ctx: int = DEFAULT_NUM_CTX,
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model, **kwargs)
        self.base_url = (base_url or DEFAULT_OLLAMA_URL).rstrip("/")
        self.timeout = timeout
        self.num_ctx = max(num_ctx, DEFAULT_NUM_CTX)

    def _prepare_payload(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        format_json: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if not self.model:
            raise ValueError(
                "No model specified for Ollama. Configure a model in Settings (e.g. 'llama3.2', 'qwen2.5', or 'mistral')."
            )

        options: Dict[str, Any] = {
            "temperature": temperature,
            "num_ctx": self.num_ctx,
        }
        if "max_tokens" in kwargs and kwargs["max_tokens"]:
            options["num_predict"] = kwargs["max_tokens"]
        else:
            options["num_predict"] = 512

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": options,
        }

        if format_json:
            payload["format"] = "json"

        # Allow passing extra ollama options
        if "options" in kwargs and isinstance(kwargs["options"], dict):
            payload["options"].update(kwargs["options"])

        return payload

    def _handle_error(self, exc: Exception) -> Exception:
        if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout)):
            return RuntimeError(
                f"Ollama is not running at {self.base_url}. Start it with: 'ollama serve'"
            )
        if isinstance(exc, httpx.HTTPStatusError):
            status_code = exc.response.status_code
            text = exc.response.text.lower()
            if status_code == 404 or "not found" in text:
                return RuntimeError(
                    f"Model '{self.model}' not found in Ollama. Pull it with: 'ollama pull {self.model}'"
                )
            return RuntimeError(
                f"Ollama returned HTTP error {status_code}: {exc.response.text}"
            )
        if isinstance(exc, (httpx.ReadTimeout, httpx.WriteTimeout)):
            return TimeoutError(
                f"Ollama request timed out after {self.timeout}s. Local inference may be slow or overloaded."
            )
        return exc

    def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        format_json: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        payload = self._prepare_payload(messages, temperature, format_json, **kwargs)
        timeout_config = httpx.Timeout(self.timeout, connect=10.0)

        try:
            with httpx.Client(timeout=timeout_config) as client:
                response = client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as e:
            raise self._handle_error(e) from e

        content = data.get("message", {}).get("content", "")
        return LLMResponse(
            content=content,
            provider="ollama",
            model=self.model,
            raw_response=data,
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_duration": data.get("total_duration", 0),
            },
        )

    async def agenerate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        format_json: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        payload = self._prepare_payload(messages, temperature, format_json, **kwargs)
        timeout_config = httpx.Timeout(self.timeout, connect=10.0)

        try:
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as e:
            raise self._handle_error(e) from e

        content = data.get("message", {}).get("content", "")
        return LLMResponse(
            content=content,
            provider="ollama",
            model=self.model,
            raw_response=data,
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_duration": data.get("total_duration", 0),
            },
        )
