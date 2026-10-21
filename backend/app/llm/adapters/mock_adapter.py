from __future__ import annotations
import os
from typing import List, Dict, Any, Optional
from app.llm.base import BaseLLMAdapter, LLMMessage, LLMResponse, JobCancelledError


class MockLLMAdapter(BaseLLMAdapter):
    """
    Mock LLM adapter for deterministic unit testing.
    Can be loaded with a single response string, or a queue of responses
    to test multi-turn retry behavior (e.g., malformed JSON followed by valid JSON).
    """

    def __init__(
        self,
        model: str = "mock-model",
        canned_response: Optional[str] = None,
        response_queue: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model, **kwargs)
        self.canned_response = canned_response or '{"status": "ok"}'
        self.response_queue: List[str] = list(response_queue) if response_queue else []
        self.call_count = 0
        self.received_messages: List[List[LLMMessage]] = []

    def set_queue(self, responses: List[str]) -> None:
        self.response_queue = list(responses)

    def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        format_json: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        from app.services.job_queue import get_current_job_handle
        handle = get_current_job_handle()
        if handle and handle.is_cancelled():
            raise JobCancelledError("Job was cancelled before mock LLM execution.")

        self.call_count += 1
        self.received_messages.append(messages)

        sleep_sec = float(os.environ.get("MOCK_LLM_SLEEP", "0.0"))
        if sleep_sec > 0:
            import time
            start_t = time.time()
            while time.time() - start_t < sleep_sec:
                if handle and handle.is_cancelled():
                    raise JobCancelledError("Job was cancelled during mock LLM execution.")
                time.sleep(0.05)


        if self.response_queue:
            content = self.response_queue.pop(0)
        else:
            content = self.canned_response

        return LLMResponse(
            content=content,
            provider="mock",
            model=self.model,
            raw_response={"mock": True, "call_count": self.call_count},
            usage={"prompt_tokens": 10, "completion_tokens": 10},
        )

    async def agenerate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        format_json: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        return self.generate(messages, temperature=temperature, format_json=format_json, **kwargs)
