"""AI pair-programmer service: explain, refactor, test, document, optimize, security."""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.llm import prompts
from app.llm.base import BaseLLMProvider
from app.rag.contracts import build_citations
from app.rag.pipeline import RagPipeline
from app.schemas.chat import Answer, PairAction


class PairService:
    """Code-centric assistant actions grounded in optional documentation context."""

    def __init__(self, rag: RagPipeline, llm: BaseLLMProvider) -> None:
        self._rag = rag
        self._llm = llm

    async def run(
        self,
        action: PairAction,
        code: str,
        language: str | None = None,
        instructions: str | None = None,
    ) -> Answer:
        # Pull best-practice context for optimisation/security/refactor actions.
        chunks = []
        if action in {PairAction.OPTIMIZE, PairAction.SECURITY, PairAction.REFACTOR}:
            query = f"{language or ''} {action.value} best practices".strip()
            chunks = await self._rag.retrieve(query, "docs")
        messages = prompts.build_pair_messages(action, code, chunks, language, instructions)
        response = await self._llm.generate(messages)
        return Answer(
            text=response.content,
            citations=build_citations(chunks),
            model=response.model,
            provider=response.provider,
        )

    async def _retrieve_chunks(
        self, action: PairAction, language: str | None
    ) -> list:
        """Pull best-practice context for optimisation/security/refactor actions."""
        chunks = []
        if action in {PairAction.OPTIMIZE, PairAction.SECURITY, PairAction.REFACTOR}:
            query = f"{language or ''} {action.value} best practices".strip()
            chunks = await self._rag.retrieve(query, "docs")
        return chunks

    async def retrieve_citations(
        self,
        action: PairAction,
        code: str,
        language: str | None = None,
        instructions: str | None = None,
    ) -> Answer:
        """Return citations only (often empty) to enrich a streamed answer."""
        chunks = await self._retrieve_chunks(action, language)
        return Answer(text="", citations=build_citations(chunks))

    async def stream(
        self,
        action: PairAction,
        code: str,
        language: str | None = None,
        instructions: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream pair-programming answer tokens."""
        chunks = await self._retrieve_chunks(action, language)
        messages = prompts.build_pair_messages(action, code, chunks, language, instructions)
        async for token in self._llm.stream(messages):
            yield token
