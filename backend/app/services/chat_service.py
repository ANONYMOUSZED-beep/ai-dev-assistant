"""Documentation chat service.

Implements the core RAG answer flow: retrieve grounded context, build a context-aware
prompt, generate (or stream) an answer, and attach citations.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.llm import prompts
from app.llm.base import BaseLLMProvider
from app.rag.contracts import build_citations
from app.rag.pipeline import RagPipeline
from app.schemas.chat import Answer


class ChatService:
    """RAG-grounded documentation Q&A."""

    def __init__(self, rag: RagPipeline, llm: BaseLLMProvider) -> None:
        self._rag = rag
        self._llm = llm

    async def answer(self, question: str, collection: str = "docs") -> Answer:
        """Return a grounded answer with citations for ``question``."""
        chunks = await self._rag.retrieve(question, collection)
        messages = prompts.build_doc_qa_messages(question, chunks)
        response = await self._llm.generate(messages)
        return Answer(
            text=response.content,
            citations=build_citations(chunks),
            model=response.model,
            provider=response.provider,
        )

    async def stream(self, question: str, collection: str = "docs") -> AsyncIterator[str]:
        """Stream answer tokens for ``question`` (citations are sent separately)."""
        chunks = await self._rag.retrieve(question, collection)
        messages = prompts.build_doc_qa_messages(question, chunks)
        async for token in self._llm.stream(messages):
            yield token

    async def retrieve_citations(self, question: str, collection: str = "docs") -> Answer:
        """Return citations only (used to enrich a streamed answer)."""
        chunks = await self._rag.retrieve(question, collection)
        return Answer(text="", citations=build_citations(chunks))
