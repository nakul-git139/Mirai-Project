from __future__ import annotations
import json
import time
import logging
from typing import List, Dict, Any, Optional, AsyncIterator, Iterator
import httpx

from app.llm.base import BaseLLMAdapter, LLMMessage, LLMResponse
from app.services.timing_logger import log_llm_timing

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_TIMEOUT_SECONDS = 900.0  # Raised to 900 seconds for slow CPU machines
DEFAULT_NUM_CTX = 8192
DEFAULT_SEED = 42
DEFAULT_KEEP_ALIVE = "60m"


class OllamaAdapter(BaseLLMAdapter):
    """
    Adapter for local/network Ollama instances.
    Enforces num_ctx >= 8192, fixed seed (42), temperature 0, num_predict cap,
    keep_alive to keep model loaded in memory, raised 900s timeout,
    and automatic per-call latency/token logging.
    """

    def __init__(
        self,
        model: str,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        num_ctx: int = DEFAULT_NUM_CTX,
        seed: int = DEFAULT_SEED,
        keep_alive: str = DEFAULT_KEEP_ALIVE,
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model, **kwargs)
        self.base_url = (base_url or DEFAULT_OLLAMA_URL).rstrip("/")
        self.timeout = timeout
        self.num_ctx = max(num_ctx, DEFAULT_NUM_CTX)
        self.seed = seed
        self.keep_alive = keep_alive

    def _prepare_payload(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        format_json: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if not self.model:
            raise ValueError(
                "No model specified for Ollama. Configure a model in Settings (e.g. 'qwen2.5:3b', 'llama3.2', or 'mistral')."
            )

        num_predict = kwargs.get("num_predict") or kwargs.get("max_tokens") or 512

        options: Dict[str, Any] = {
            "temperature": temperature,
            "seed": kwargs.get("seed", self.seed),
            "num_ctx": self.num_ctx,
            "num_predict": num_predict,
        }

        # Allow passing extra custom ollama options
        if "options" in kwargs and isinstance(kwargs["options"], dict):
            options.update(kwargs["options"])

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": bool(kwargs.get("stream", False)),
            "options": options,
            "keep_alive": kwargs.get("keep_alive", self.keep_alive),
        }

        if format_json:
            payload["format"] = "json"

        return payload

    def _handle_error(self, exc: Exception) -> Exception:
        if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout)):
            return RuntimeError(
                f"Ollama is not running at {self.base_url}. Start it with: 'ollama serve' or verify network connectivity."
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
                f"Ollama request timed out after {self.timeout}s. CPU inference may be slow or overloaded."
            )
        return exc

    def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        format_json: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        feature = kwargs.get("feature", "llm_generation")
        payload = self._prepare_payload(messages, temperature, format_json, **kwargs)
        timeout_config = httpx.Timeout(self.timeout, connect=30.0)

        t_start = time.perf_counter()
        try:
            with httpx.Client(timeout=timeout_config) as client:
                response = client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as e:
            t_elapsed = time.perf_counter() - t_start
            log_llm_timing(
                feature=feature,
                provider="ollama",
                model=self.model,
                prompt_tokens=0,
                output_tokens=0,
                duration_seconds=t_elapsed,
                status="error",
                metadata={"error": str(e)},
            )
            raise self._handle_error(e) from e

        t_elapsed = time.perf_counter() - t_start
        content = data.get("message", {}).get("content", "")
        prompt_tokens = data.get("prompt_eval_count", 0)
        output_tokens = data.get("eval_count", 0)

        log_llm_timing(
            feature=feature,
            provider="ollama",
            model=self.model,
            prompt_tokens=prompt_tokens,
            output_tokens=output_tokens,
            duration_seconds=t_elapsed,
            status="success",
        )

        return LLMResponse(
            content=content,
            provider="ollama",
            model=self.model,
            raw_response=data,
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": output_tokens,
                "total_duration": data.get("total_duration", 0),
                "duration_seconds": t_elapsed,
            },
        )

    async def agenerate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        format_json: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        feature = kwargs.get("feature", "llm_generation")
        payload = self._prepare_payload(messages, temperature, format_json, **kwargs)
        timeout_config = httpx.Timeout(self.timeout, connect=30.0)

        t_start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as e:
            t_elapsed = time.perf_counter() - t_start
            log_llm_timing(
                feature=feature,
                provider="ollama",
                model=self.model,
                prompt_tokens=0,
                output_tokens=0,
                duration_seconds=t_elapsed,
                status="error",
                metadata={"error": str(e)},
            )
            raise self._handle_error(e) from e

        t_elapsed = time.perf_counter() - t_start
        content = data.get("message", {}).get("content", "")
        prompt_tokens = data.get("prompt_eval_count", 0)
        output_tokens = data.get("eval_count", 0)

        log_llm_timing(
            feature=feature,
            provider="ollama",
            model=self.model,
            prompt_tokens=prompt_tokens,
            output_tokens=output_tokens,
            duration_seconds=t_elapsed,
            status="success",
        )

        return LLMResponse(
            content=content,
            provider="ollama",
            model=self.model,
            raw_response=data,
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": output_tokens,
                "total_duration": data.get("total_duration", 0),
                "duration_seconds": t_elapsed,
            },
        )

    async def astream_generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        format_json: bool = False,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Streams response tokens as they arrive from Ollama API.
        """
        payload = self._prepare_payload(messages, temperature, format_json, stream=True, **kwargs)
        timeout_config = httpx.Timeout(self.timeout, connect=30.0)

        async with httpx.AsyncClient(timeout=timeout_config) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("message", {}).get("content", "")
                        if token:
                            yield token
                    except Exception:
                        continue
