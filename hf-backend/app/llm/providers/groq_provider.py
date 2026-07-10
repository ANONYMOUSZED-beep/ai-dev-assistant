"""Groq provider.

Groq exposes an OpenAI-compatible API (served on Groq LPU hardware for very low
latency), so this reuses :class:`OpenAICompatibleProvider` and only overrides the
base URL and name.
"""

from __future__ import annotations

from app.llm.providers.openai_provider import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    """Groq chat-completions provider (OpenAI-compatible)."""

    name: str = "groq"
    base_url: str | None = "https://api.groq.com/openai/v1"
