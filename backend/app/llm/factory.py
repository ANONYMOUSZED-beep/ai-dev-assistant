"""LLM provider factory.

Selects and constructs the configured provider from :class:`Settings`. Provider
classes lazily import their SDKs, so importing this module (and therefore
``app.main``) never requires any provider SDK to be installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.config import LLMProviderName, Settings
from app.core.exceptions import ConfigurationError
from app.llm.base import BaseLLMProvider
from app.llm.providers.anthropic_provider import AnthropicProvider
from app.llm.providers.deepseek_provider import DeepSeekProvider
from app.llm.providers.gemini_provider import GeminiProvider
from app.llm.providers.groq_provider import GroqProvider
from app.llm.providers.openai_provider import OpenAIProvider
from app.llm.providers.qwen_provider import QwenProvider

if TYPE_CHECKING:
    from collections.abc import Callable

#: Maps a provider name to its class and the ``Settings`` attribute holding its API key.
_REGISTRY: dict[LLMProviderName, tuple[type[BaseLLMProvider], str]] = {
    "openai": (OpenAIProvider, "openai_api_key"),
    "anthropic": (AnthropicProvider, "anthropic_api_key"),
    "gemini": (GeminiProvider, "google_api_key"),
    "deepseek": (DeepSeekProvider, "deepseek_api_key"),
    "qwen": (QwenProvider, "qwen_api_key"),
    "groq": (GroqProvider, "groq_api_key"),
}


def get_llm_provider(settings: Settings) -> BaseLLMProvider:
    """Build the :class:`BaseLLMProvider` selected by ``settings.llm_provider``.

    The API key is read from the matching ``Settings`` attribute. A missing key is
    only fatal in production (raising :class:`ConfigurationError`); otherwise the
    provider is still constructed and the key is validated lazily at call time.
    """
    entry: tuple[type[BaseLLMProvider], str] | None = _REGISTRY.get(settings.llm_provider)
    if entry is None:  # pragma: no cover - guarded by the Literal type on Settings
        raise ConfigurationError(f"Unsupported LLM provider: {settings.llm_provider!r}")

    provider_cls, api_key_attr = entry
    api_key: str | None = getattr(settings, api_key_attr)

    if not api_key and settings.is_production:
        raise ConfigurationError(
            f"Missing API key '{api_key_attr}' required for provider "
            f"'{settings.llm_provider}' in production.",
            details={"provider": settings.llm_provider, "setting": api_key_attr},
        )

    factory: Callable[..., BaseLLMProvider] = provider_cls
    return factory(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        api_key=api_key,
    )
