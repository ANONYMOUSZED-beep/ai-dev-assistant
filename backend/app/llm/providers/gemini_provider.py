"""Google Gemini provider.

``google.generativeai`` ships a synchronous client, so all calls are offloaded to a
worker thread via :func:`asyncio.to_thread`. Streaming pulls chunks from the sync
iterator one item at a time, also off the event loop. The SDK is imported lazily.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import Any

from app.core.exceptions import LLMProviderError
from app.llm.base import BaseLLMProvider
from app.llm.providers._common import to_gemini_contents, transient_retry
from app.schemas.llm import LLMMessage, LLMResponse

#: Sentinel returned by :func:`_safe_next` when the sync iterator is exhausted.
_STREAM_DONE: object = object()


def _safe_next(iterator: Iterator[Any]) -> Any:
    """Return the next item from ``iterator`` or :data:`_STREAM_DONE` when exhausted."""
    try:
        return next(iterator)
    except StopIteration:
        return _STREAM_DONE


def _chunk_text(chunk: Any) -> str:
    """Safely extract text from a Gemini chunk/response without raising."""
    try:
        return chunk.text or ""
    except Exception:  # noqa: BLE001 - .text raises when a chunk has no text part
        return ""


class GeminiProvider(BaseLLMProvider):
    """Google Gemini (Generative AI) provider."""

    name: str = "gemini"

    def __init__(
        self,
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        api_key: str | None = None,
    ) -> None:
        super().__init__(model=model, temperature=temperature, max_tokens=max_tokens)
        self.api_key = api_key

    def _generation_config(self) -> dict[str, Any]:
        return {"temperature": self.temperature, "max_output_tokens": self.max_tokens}

    def _build_model(self, system_instruction: str | None) -> Any:
        """Configure the SDK and return a ``GenerativeModel`` instance."""
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)
        return genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system_instruction,
        )

    @transient_retry
    async def _raw_generate(self, model: Any, contents: list[dict[str, object]]) -> Any:
        return await asyncio.to_thread(
            model.generate_content,
            contents,
            generation_config=self._generation_config(),
        )

    async def generate(self, messages: list[LLMMessage]) -> LLMResponse:
        system_instruction, contents = to_gemini_contents(messages)
        try:
            model = self._build_model(system_instruction)
            response = await self._raw_generate(model, contents)
        except LLMProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalize all SDK errors
            raise LLMProviderError(f"{self.name} completion failed: {exc}") from exc

        usage = getattr(response, "usage_metadata", None)
        return LLMResponse(
            content=_chunk_text(response),
            model=self.model,
            provider=self.name,
            prompt_tokens=getattr(usage, "prompt_token_count", None),
            completion_tokens=getattr(usage, "candidates_token_count", None),
        )

    async def stream(self, messages: list[LLMMessage]) -> AsyncIterator[str]:
        system_instruction, contents = to_gemini_contents(messages)
        try:
            model = self._build_model(system_instruction)
            response = await asyncio.to_thread(
                model.generate_content,
                contents,
                generation_config=self._generation_config(),
                stream=True,
            )
            iterator = iter(response)
            while True:
                chunk = await asyncio.to_thread(_safe_next, iterator)
                if chunk is _STREAM_DONE:
                    break
                text = _chunk_text(chunk)
                if text:
                    yield text
        except Exception as exc:  # noqa: BLE001 - normalize all SDK errors
            raise LLMProviderError(f"{self.name} streaming failed: {exc}") from exc
