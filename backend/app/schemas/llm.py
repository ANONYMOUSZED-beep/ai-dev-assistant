"""LLM interaction contracts shared by providers, prompts, and services."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class LLMMessage(BaseModel):
    """A single chat message."""

    role: Role
    content: str


class LLMResponse(BaseModel):
    """A non-streamed completion result."""

    content: str
    model: str
    provider: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
