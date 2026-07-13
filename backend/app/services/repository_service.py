"""GitHub repository indexing and chat service."""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.core.config import get_settings
from app.core.logging import get_logger
from app.llm import prompts
from app.llm.base import BaseLLMProvider
from app.rag.contracts import build_citations
from app.rag.ingestion import load_github_repo
from app.rag.pipeline import RagPipeline
from app.schemas.chat import Answer

logger = get_logger(__name__)

_NO_CONTEXT_MESSAGE = (
    "I couldn't find anything relevant in this repository's indexed code. If indexing "
    "just finished, try again in a moment — otherwise try rephrasing to mention a "
    "file, function, or feature."
)


def repo_collection(repository_id: str) -> str:
    """Vector-store collection name for a repository."""
    return f"repo:{repository_id}"


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
            return Answer(text=_NO_CONTEXT_MESSAGE, citations=[])
        messages = prompts.build_repo_qa_messages(question, chunks)
        response = await self._llm.generate(messages)
        answer = Answer(
            text=response.content,
            citations=build_citations(chunks),
            model=response.model,
            provider=response.provider,
        )
        try:
            answer.follow_ups = await self.follow_ups(question, response.content)
        except Exception:  # noqa: BLE001 - follow-ups are best-effort, never break the answer
            logger.exception("Follow-up generation failed")
            answer.follow_ups = []
        return answer

    async def generate_overview(self, repository_id: str) -> Answer:
        """Generate a one-page architecture tour grounded in the indexed repository."""
        chunks = await self._rag.retrieve(
            "architecture overview entry point how to run main modules",
            repo_collection(repository_id),
        )
        if not chunks:
            return Answer(text="", citations=[])
        messages = prompts.build_repo_overview_messages(chunks)
        response = await self._llm.generate(messages)
        return Answer(
            text=response.content,
            citations=build_citations(chunks),
            model=response.model,
            provider=response.provider,
        )

    async def follow_ups(self, question: str, answer_text: str) -> list[str]:
        """Suggest up to 3 short follow-up questions for the given Q&A."""
        response = await self._llm.generate(
            prompts.build_followups_messages(question, answer_text)
        )
        return _clean_follow_ups(response.content)

    async def retrieve_citations(self, repository_id: str, question: str) -> Answer:
        """Return citations only (used to enrich a streamed answer)."""
        chunks = await self._rag.retrieve(question, repo_collection(repository_id))
        return Answer(text="", citations=build_citations(chunks))

    async def stream(
        self, repository_id: str, question: str
    ) -> AsyncIterator[str]:
        """Stream answer tokens grounded in the indexed repository."""
        chunks = await self._rag.retrieve(question, repo_collection(repository_id))
        if not chunks:
            yield _NO_CONTEXT_MESSAGE
            return
        messages = prompts.build_repo_qa_messages(question, chunks)
        async for token in self._llm.stream(messages):
            yield token
