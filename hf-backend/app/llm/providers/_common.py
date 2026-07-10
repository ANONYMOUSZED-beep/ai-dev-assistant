"""Shared helpers for concrete LLM providers.

Contains message-format converters (one chat message list -> each SDK's expected
shape) and a tenacity-based retry policy for transient upstream errors. Nothing in
this module imports a heavy provider SDK, so importing it is always cheap.
"""

from __future__ import annotations

from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.schemas.llm import LLMMessage, Role

OpenAIMessage = dict[str, str]
GeminiContent = dict[str, object]

#: Exception class names that almost always indicate a retryable upstream condition.
_TRANSIENT_EXC_NAMES: frozenset[str] = frozenset(
    {
        "APIConnectionError",
        "APITimeoutError",
        "RateLimitError",
        "InternalServerError",
        "ServiceUnavailableError",
        "Timeout",
        "TimeoutError",
        "ConnectionError",
        "ConnectError",
        "ReadTimeout",
        "RemoteProtocolError",
        "OverloadedError",
    }
)

#: HTTP status codes that should be retried when surfaced on an exception.
_TRANSIENT_STATUS_CODES: frozenset[int] = frozenset({408, 409, 425, 429, 500, 502, 503, 504})


def is_transient_error(exc: BaseException) -> bool:
    """Return ``True`` when ``exc`` looks like a transient, retryable failure.

    Detection is duck-typed by exception class name and any ``status_code`` /
    ``status`` attribute so that no provider SDK needs to be imported here.
    """
    if type(exc).__name__ in _TRANSIENT_EXC_NAMES:
        return True
    for attr in ("status_code", "status", "http_status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int) and value in _TRANSIENT_STATUS_CODES:
            return True
    return False


#: Reusable decorator applied to raw upstream calls. ``reraise=True`` keeps the
#: original SDK exception so the caller can wrap it in :class:`LLMProviderError`.
transient_retry = retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, max=8.0),
    retry=retry_if_exception(is_transient_error),
)


def to_openai_messages(messages: list[LLMMessage]) -> list[OpenAIMessage]:
    """Convert chat messages into the OpenAI ``chat.completions`` message list."""
    return [{"role": message.role.value, "content": message.content} for message in messages]


def split_system(messages: list[LLMMessage]) -> tuple[str | None, list[OpenAIMessage]]:
    """Split system messages from the conversation for SDKs with a dedicated system field.

    Returns ``(system_prompt, conversation)`` where multiple system messages are
    joined with blank lines and the conversation contains only user/assistant turns.
    """
    system_parts = [m.content for m in messages if m.role is Role.SYSTEM]
    conversation: list[OpenAIMessage] = [
        {"role": m.role.value, "content": m.content}
        for m in messages
        if m.role is not Role.SYSTEM
    ]
    system_prompt = "\n\n".join(system_parts) if system_parts else None
    return system_prompt, conversation


def to_gemini_contents(messages: list[LLMMessage]) -> tuple[str | None, list[GeminiContent]]:
    """Convert chat messages into a Gemini ``(system_instruction, contents)`` pair.

    Gemini uses the role ``"model"`` for assistant turns and ``"user"`` otherwise,
    while system prompts are passed separately as a system instruction.
    """
    system_parts = [m.content for m in messages if m.role is Role.SYSTEM]
    contents: list[GeminiContent] = []
    for message in messages:
        if message.role is Role.SYSTEM:
            continue
        role = "model" if message.role is Role.ASSISTANT else "user"
        contents.append({"role": role, "parts": [message.content]})
    system_instruction = "\n\n".join(system_parts) if system_parts else None
    return system_instruction, contents
