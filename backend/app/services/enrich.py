"""Post-answer enrichment: cheap LLM-generated follow-up question suggestions."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.llm import prompts

if TYPE_CHECKING:
    from app.llm.base import BaseLLMProvider

_MAX_FOLLOW_UPS = 3
_MAX_LEN = 120
_MAX_TITLE_LEN = 60


async def generate_title(llm: BaseLLMProvider, question: str) -> str | None:
    """Return a short conversation title from the first question, or None on failure."""
    question = (question or "").strip()
    if not question:
        return None
    try:
        response = await llm.generate(prompts.build_title_messages(question))
    except Exception:  # noqa: BLE001 - titling must never break the response
        return None
    title = _clean(response.content.strip().splitlines()[0] if response.content else "")
    if not title:
        return None
    if len(title) > _MAX_TITLE_LEN:
        title = title[: _MAX_TITLE_LEN - 1].rstrip() + "…"
    return title


def _clean(line: str) -> str:
    # Strip common list prefixes (numbers, bullets, dashes) and surrounding quotes.
    line = re.sub(r"^\s*(?:\d+[.)]|[-*•])\s*", "", line).strip()
    return line.strip("\"'").strip()


async def generate_follow_ups(
    llm: BaseLLMProvider, question: str, answer: str
) -> list[str]:
    """Return up to 3 short follow-up questions, or [] on any failure.

    Best-effort: never raises, so it can't break the answer it enriches.
    """
    answer = (answer or "").strip()
    if not answer or len(answer) < 40:
        return []
    try:
        response = await llm.generate(prompts.build_follow_up_messages(question, answer))
    except Exception:  # noqa: BLE001 - enrichment must never break the response
        return []

    seen: set[str] = set()
    results: list[str] = []
    for raw in response.content.splitlines():
        text = _clean(raw)
        if not text or len(text) > _MAX_LEN or not text.endswith("?"):
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        results.append(text)
        if len(results) >= _MAX_FOLLOW_UPS:
            break
    return results
