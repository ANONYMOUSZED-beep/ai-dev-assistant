"""DeepSeek provider.

DeepSeek exposes an OpenAI-compatible API, so this reuses
:class:`OpenAICompatibleProvider` and only overrides the base URL and name.
"""

from __future__ import annotations

from app.llm.providers.openai_provider import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek chat-completions provider (OpenAI-compatible)."""

    name: str = "deepseek"
    base_url: str | None = "https://api.deepseek.com"
