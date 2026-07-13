"""GitHub repository indexing and chat service."""

from __future__ import annotations

from app.core.config import get_settings
from app.core.logging import get_logger
from app.llm import prompts
from app.llm.base import BaseLLMProvider
from app.rag.contracts import build_citations
from app.rag.ingestion import load_github_repo
from app.rag.pipeline import RagPipeline
from app.schemas.chat import Answer

logger = get_logger(__name__)


def repo_collection(repository_id: str) -> str:
    """Vector-store collection name for a repository."""
    return f"repo:{repository_id}"


class RepositoryService:
    """Index repositories and answer questions grounded in their code."""

    def __init__(self, rag: RagPipeline, llm: BaseLLMProvider) -> None:
        self._rag = rag
        self._llm = llm

    async def index(
        self, repository_id: str, url: str, branch: str | None = None
    ) -> tuple[int, int]:
        """Clone/fetch and index a repository. Returns ``(files, chunks)``."""
        settings = get_settings()
        documents = load_github_repo(url, branch=branch, github_token=settings.github_token)
        chunks = await self._rag.ingest(documents, repo_collection(repository_id))
        logger.info("Indexed repo %s: %d files, %d chunks", url, len(documents), chunks)
        return len(documents), chunks

    async def answer(self, repository_id: str, question: str) -> Answer:
        """Answer a question grounded in the indexed repository."""
        chunks = await self._rag.retrieve(question, repo_collection(repository_id))
        if not chunks:
            return Answer(
                text=(
                    "I couldn't find anything relevant in this repository's indexed "
                    "code. If indexing just finished, try again in a moment — otherwise "
                    "try rephrasing your question to mention a file, function, or feature."
                ),
                citations=[],
            )
        messages = prompts.build_repo_qa_messages(question, chunks)
        response = await self._llm.generate(messages)
        return Answer(
            text=response.content,
            citations=build_citations(chunks),
            model=response.model,
            provider=response.provider,
        )
