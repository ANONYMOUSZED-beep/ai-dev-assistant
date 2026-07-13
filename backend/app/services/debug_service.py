"""Error / stack-trace debugging service."""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.llm import prompts
from app.llm.base import BaseLLMProvider
from app.rag.contracts import build_citations
from app.rag.pipeline import RagPipeline
from app.schemas.chat import Answer
from app.services.repository_service import repo_collection


class DebugService:
    """Analyse errors/stack traces and propose corrected code."""

    def __init__(self, rag: RagPipeline, llm: BaseLLMProvider) -> None:
        self._rag = rag
        self._llm = llm

    async def debug(
        self,
        error: str,
        language: str | None = None,
        code_context: str | None = None,
        repository_id: str | None = None,
    ) -> Answer:
        collection = repo_collection(repository_id) if repository_id else "docs"
        query = error if not language else f"{language} error: {error}"
        chunks = await self._rag.retrieve(query, collection)
        messages = prompts.build_debug_messages(error, chunks, language, code_context)
        response = await self._llm.generate(messages)
        return Answer(
            text=response.content,
            citations=build_citations(chunks),
            model=response.model,
            provider=response.provider,
        )

    async def retrieve_citations(
        self,
        error: str,
        language: str | None = None,
        code_context: str | None = None,
        repository_id: str | None = None,
    ) -> Answer:
        """Return citations only (used to enrich a streamed answer)."""
        collection = repo_collection(repository_id) if repository_id else "docs"
        query = error if not language else f"{language} error: {error}"
        chunks = await self._rag.retrieve(query, collection)
        return Answer(text="", citations=build_citations(chunks))

    async def stream(
        self,
        error: str,
        language: str | None = None,
        code_context: str | None = None,
        repository_id: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream debug answer tokens. Debug always answers from the error text."""
        collection = repo_collection(repository_id) if repository_id else "docs"
        query = error if not language else f"{language} error: {error}"
        chunks = await self._rag.retrieve(query, collection)
        messages = prompts.build_debug_messages(error, chunks, language, code_context)
        async for token in self._llm.stream(messages):
            yield token
