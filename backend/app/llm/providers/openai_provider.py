"""OpenAI provider and the shared OpenAI-compatible base.

The :class:`OpenAICompatibleProvider` base is reused by any vendor exposing an
OpenAI-style ``/chat/completions`` API (DeepSeek, Qwen). The ``openai`` SDK is
imported lazily so importing this module never requires the package to be present.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, cast

from app.core.exceptions import LLMProviderError
from app.llm.base import BaseLLMProvider
from app.llm.providers._common import to_openai_messages, transient_retry
from app.schemas.llm import LLMMessage, LLMResponse

if TYPE_CHECKING:
    from openai import AsyncOpenAI


class OpenAICompatibleProvider(BaseLLMProvider):
    """Base class for providers speaking the OpenAI chat-completions protocol."""

    name: str = "openai-compatible"
    #: Override in subclasses to target an OpenAI-compatible third-party endpoint.
    base_url: str | None = None

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
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        """Lazily build and cache the async OpenAI client."""
        if self._client is None:
            from openai import AsyncOpenAI

            kwargs: dict[str, Any] = {"api_key": self.api_key}
            if self.base_url is not None:
                kwargs["base_url"] = self.base_url
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    @transient_retry
    async def _raw_generate(self, client: AsyncOpenAI, messages: list[dict[str, str]]) -> Any:
        return await client.chat.completions.create(
            model=self.model,
            messages=cast(Any, messages),
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

    async def generate(self, messages: list[LLMMessage]) -> LLMResponse:
        client = self._get_client()
        payload = to_openai_messages(messages)
        try:
            response = await self._raw_generate(client, payload)
        except LLMProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalize all SDK errors
            raise LLMProviderError(f"{self.name} completion failed: {exc}") from exc

        choice = response.choices[0]
        usage = getattr(response, "usage", None)
        return LLMResponse(
            content=choice.message.content or "",
            model=self.model,
            provider=self.name,
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
        )

    async def stream(self, messages: list[LLMMessage]) -> AsyncIterator[str]:
        client = self._get_client()
        payload = to_openai_messages(messages)
        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=cast(Any, payload),
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
            )
            async for chunk in cast("AsyncIterator[Any]", response):
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)
                if content:
                    yield content
        except Exception as exc:  # noqa: BLE001 - normalize all SDK errors
            raise LLMProviderError(f"{self.name} streaming failed: {exc}") from exc


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI chat-completions provider."""

    name: str = "openai"
