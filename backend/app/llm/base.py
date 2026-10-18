from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    role: str = Field(description="Role of the speaker: system, user, assistant")
    content: str = Field(description="Content of the message")


class LLMResponse(BaseModel):
    content: str
    provider: str
    model: str
    raw_response: Optional[Dict[str, Any]] = None
    usage: Optional[Dict[str, Any]] = None


class BaseLLMAdapter(ABC):
    """Abstract interface for all LLM provider adapters."""

    def __init__(self, model: str, **kwargs: Any) -> None:
        self.model = model
        self.kwargs = kwargs

    @abstractmethod
    def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        format_json: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        """Synchronous chat completion."""
        pass

    @abstractmethod
    async def agenerate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        format_json: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        """Asynchronous chat completion."""
        pass
