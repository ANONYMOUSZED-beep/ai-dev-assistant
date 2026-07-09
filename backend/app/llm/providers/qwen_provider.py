"""Qwen (Alibaba DashScope) provider.

DashScope offers an OpenAI-compatible endpoint, so this reuses
:class:`OpenAICompatibleProvider` and only overrides the base URL and name.
"""

from __future__ import annotations

from app.llm.providers.openai_provider import OpenAICompatibleProvider


class QwenProvider(OpenAICompatibleProvider):
    """Qwen chat-completions provider via DashScope's OpenAI-compatible API."""

    name: str = "qwen"
    base_url: str | None = "https://dashscope.aliyuncs.com/compatible-mode/v1"
