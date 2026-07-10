"""Authoritative LLM provider contract.

Concrete providers (OpenAI, Anthropic, Gemini, DeepSeek, Qwen) implement this interface.
This file defines the stable contract consumed by services; provider implementations must
not change these signatures.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.schemas.llm import LLMMessage, LLMResponse


class BaseLLMProvider(ABC):
    """Abstract base for all chat-completion LLM providers."""

    #: Stable provider identifier, e.g. ``"openai"``.
    name: str = "base"

    def __init__(self, *, model: str, temperature: float, max_tokens: int) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    @abstractmethod
    async def generate(self, messages: list[LLMMessage]) -> LLMResponse:
        """Return a complete chat completion for ``messages``."""
        raise NotImplementedError

    @abstractmethod
    async def stream(self, messages: list[LLMMessage]) -> AsyncIterator[str]:
        """Yield response text incrementally as it is generated."""
        raise NotImplementedError
        yield ""  # pragma: no cover  (defines this as an async generator)
