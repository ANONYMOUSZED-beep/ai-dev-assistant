"""Anthropic (Claude) provider.

System messages are mapped to Anthropic's dedicated ``system`` parameter while
user/assistant turns become ``messages``. The ``anthropic`` SDK is imported lazily.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from app.core.exceptions import LLMProviderError
from app.llm.base import BaseLLMProvider
from app.llm.providers._common import split_system, transient_retry
from app.schemas.llm import LLMMessage, LLMResponse

if TYPE_CHECKING:
    from anthropic import AsyncAnthropic


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Messages API provider."""

    name: str = "anthropic"

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
        self._client: AsyncAnthropic | None = None

    def _get_client(self) -> AsyncAnthropic:
        """Lazily build and cache the async Anthropic client."""
        if self._client is None:
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    def _build_kwargs(self, messages: list[LLMMessage]) -> dict[str, Any]:
        system, conversation = split_system(messages)
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": conversation,
        }
        if system is not None:
            kwargs["system"] = system
        return kwargs

    @transient_retry
    async def _raw_generate(self, client: AsyncAnthropic, kwargs: dict[str, Any]) -> Any:
        return await client.messages.create(**kwargs)

    async def generate(self, messages: list[LLMMessage]) -> LLMResponse:
        client = self._get_client()
        kwargs = self._build_kwargs(messages)
        try:
            response = await self._raw_generate(client, kwargs)
        except LLMProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalize all SDK errors
            raise LLMProviderError(f"{self.name} completion failed: {exc}") from exc

        content = "".join(
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        )
        usage = getattr(response, "usage", None)
        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.name,
            prompt_tokens=getattr(usage, "input_tokens", None),
            completion_tokens=getattr(usage, "output_tokens", None),
        )

    async def stream(self, messages: list[LLMMessage]) -> AsyncIterator[str]:
        client = self._get_client()
        kwargs = self._build_kwargs(messages)
        try:
            async with client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    if text:
                        yield text
        except Exception as exc:  # noqa: BLE001 - normalize all SDK errors
            raise LLMProviderError(f"{self.name} streaming failed: {exc}") from exc
