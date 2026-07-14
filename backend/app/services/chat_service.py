"""Documentation chat service.

Implements the core RAG answer flow: retrieve grounded context, build a context-aware
prompt, generate (or stream) an answer, and attach citations.
"""

from __future__ import annotations

import math
from collections.abc import AsyncIterator

from app.core.logging import get_logger
from app.llm import prompts
from app.llm.base import BaseLLMProvider
from app.rag.contracts import build_citations
from app.rag.pipeline import RagPipeline
from app.schemas.chat import Answer
from app.schemas.rag import RetrievedChunk

logger = get_logger(__name__)

# Shown when a knowledge base has no matching (or no) indexed content, so we never
# answer ungrounded and pretend it came from the user's documents.
_NO_CONTEXT_MESSAGE = (
    "I couldn't find anything about that in this knowledge base. It may not have any "
    "documents yet — add some with the **+** next to Documentation, or switch to a "
    "different knowledge base. I only answer from the documents you've indexed so I can "
    "cite real sources."
)


def _grounding_confidence(chunks: list[RetrievedChunk]) -> float | None:
    """Aggregate how well retrieved context supports an answer, as a [0,1] score.

    Uses the top chunks' cross-encoder rerank logits (bge-reranker-v2-m3, roughly
    -10..+10) mapped through a sigmoid, so a strongly relevant top hit yields high
    confidence and irrelevant context yields low. Falls back to the fused [0,1]
    score when rerank scores are absent.
    """
    if not chunks:
        return None
    top = chunks[: min(3, len(chunks))]
    scores = [
        1.0 / (1.0 + math.exp(-rc.rerank_score))
        if rc.rerank_score is not None
        else rc.score
        for rc in top
    ]
    return sum(scores) / len(scores)


def _clean_follow_ups(text: str) -> list[str]:
    """Parse raw model output into at most 3 clean follow-up questions.

    Splits on newlines, strips leading bullets/numbers/punctuation and surrounding
    quotes, drops empty lines, and caps the result at 3 items.
    """
    cleaned: list[str] = []
    for line in text.splitlines():
        item = line.strip()
        # Strip leading bullets, numbering and punctuation (e.g. "1.", "-", "*", ")").
        item = item.lstrip("-*•0123456789.)(] \t")
        # Strip surrounding quotes.
        item = item.strip().strip('"').strip("'").strip()
        if item:
            cleaned.append(item)
        if len(cleaned) == 3:
            break
    return cleaned


class ChatService:
    """RAG-grounded documentation Q&A."""

    def __init__(self, rag: RagPipeline, llm: BaseLLMProvider) -> None:
        self._rag = rag
        self._llm = llm

    async def answer(self, question: str, collection: str = "docs") -> Answer:
        """Return a grounded answer with citations for ``question``."""
        chunks = await self._rag.retrieve(question, collection)
        if not chunks:
            return Answer(text=_NO_CONTEXT_MESSAGE, citations=[])
        messages = prompts.build_doc_qa_messages(question, chunks)
        response = await self._llm.generate(messages)
        answer = Answer(
            text=response.content,
            citations=build_citations(chunks),
            model=response.model,
            provider=response.provider,
            confidence=_grounding_confidence(chunks),
        )
        try:
            answer.follow_ups = await self.follow_ups(question, response.content)
        except Exception:  # noqa: BLE001 - follow-ups are best-effort, never break the answer
            logger.exception("Follow-up generation failed")
            answer.follow_ups = []
        return answer

    async def follow_ups(self, question: str, answer_text: str) -> list[str]:
        """Suggest up to 3 short follow-up questions for the given Q&A."""
        response = await self._llm.generate(
            prompts.build_followups_messages(question, answer_text)
        )
        return _clean_follow_ups(response.content)

    async def stream(self, question: str, collection: str = "docs") -> AsyncIterator[str]:
        """Stream answer tokens for ``question`` (citations are sent separately)."""
        chunks = await self._rag.retrieve(question, collection)
        if not chunks:
            yield _NO_CONTEXT_MESSAGE
            return
        messages = prompts.build_doc_qa_messages(question, chunks)
        async for token in self._llm.stream(messages):
            yield token

    async def retrieve_citations(self, question: str, collection: str = "docs") -> Answer:
        """Return citations only (used to enrich a streamed answer)."""
        chunks = await self._rag.retrieve(question, collection)
        return Answer(
            text="",
            citations=build_citations(chunks),
            confidence=_grounding_confidence(chunks),
        )
