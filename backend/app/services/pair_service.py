"""AI pair-programmer service: explain, refactor, test, document, optimize, security."""

from __future__ import annotations

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
