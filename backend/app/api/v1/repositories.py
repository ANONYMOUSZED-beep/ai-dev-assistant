"""GitHub repository endpoints: connect/index, status, and chat."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks
from sqlalchemy import select

from app.core.deps import LLMDep, RagDep, SessionDep
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.db.models import Repository
from app.db.session import get_sessionmaker
from app.schemas.chat import (
    Answer,
    IndexStatus,
    RepoChatRequest,
    RepositoryCreateRequest,
    RepositoryResponse,
)
from app.services.repository_service import RepositoryService

logger = get_logger(__name__)
router = APIRouter(prefix="/repositories", tags=["repositories"])


def _to_response(repo: Repository) -> RepositoryResponse:
    return RepositoryResponse(
        id=repo.id,
        url=repo.url,
        branch=repo.branch,
        status=IndexStatus(repo.status),
        files_indexed=repo.files_indexed,
        chunks_indexed=repo.chunks_indexed,
        error=repo.error,
    )


async def _index_repo(
    repository_id: str, url: str, branch: str | None, service: RepositoryService
) -> None:
    """Background task: index a repository and persist its status."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        repo = await session.get(Repository, repository_id)
        if repo is None:
            return
        repo.status = IndexStatus.INDEXING.value
        await session.commit()
        try:
            files, chunks = await service.index(repository_id, url, branch)
            repo.files_indexed, repo.chunks_indexed = files, chunks
            repo.status = IndexStatus.READY.value
        except Exception as exc:  # pragma: no cover - network/IO dependent
            logger.exception("Repository indexing failed")
            repo.status = IndexStatus.FAILED.value
            repo.error = str(exc)
        await session.commit()


@router.post("", response_model=RepositoryResponse, status_code=202)
async def create_repository(
    req: RepositoryCreateRequest,
    background: BackgroundTasks,
    session: SessionDep,
    rag: RagDep,
    llm: LLMDep,
) -> RepositoryResponse:
    """Register a repository and index it in the background."""
    repo = Repository(
        url=req.url,
        branch=req.branch,
        status=IndexStatus.PENDING.value,
        collection="",
    )
    session.add(repo)
    await session.flush()
    repo.collection = f"repo:{repo.id}"
    await session.commit()

    service = RepositoryService(rag, llm)
    background.add_task(_index_repo, repo.id, req.url, req.branch, service)
    return _to_response(repo)


@router.get("/{repository_id}", response_model=RepositoryResponse)
async def get_repository(repository_id: str, session: SessionDep) -> RepositoryResponse:
    """Return indexing status for a repository."""
    repo = await session.get(Repository, repository_id)
    if repo is None:
        raise NotFoundError(f"Repository {repository_id} not found")
    return _to_response(repo)


@router.delete("/{repository_id}")
async def delete_repository(repository_id: str, session: SessionDep) -> dict[str, str]:
    """Remove a repository from the registry.

    Drops the database row so it no longer appears in the explorer. Any indexed
    vectors become orphaned but harmless (unreachable without the row).
    """
    repo = await session.get(Repository, repository_id)
    if repo is None:
        raise NotFoundError(f"Repository {repository_id} not found")
    await session.delete(repo)
    await session.commit()
    return {"deleted": repository_id}


@router.get("", response_model=list[RepositoryResponse])
async def list_repositories() -> list[RepositoryResponse]:
    """List all registered repositories.

    The repository feature depends on Postgres. When the database is unavailable
    (e.g. running the demo without Docker), this degrades gracefully to an empty
    list instead of raising a 500, so the rest of the app keeps working.
    """
    sessionmaker = get_sessionmaker()
    try:
        async with sessionmaker() as session:
            result = await session.execute(select(Repository))
            return [_to_response(r) for r in result.scalars().all()]
    except Exception:  # noqa: BLE001 - DB optional in demo mode
        logger.warning("Database unavailable; returning empty repository list")
        return []


@router.post("/{repository_id}/chat", response_model=Answer)
async def repository_chat(
    repository_id: str, req: RepoChatRequest, session: SessionDep, rag: RagDep, llm: LLMDep
) -> Answer:
    """Chat over an indexed repository."""
    repo = await session.get(Repository, repository_id)
    if repo is None:
        raise NotFoundError(f"Repository {repository_id} not found")
    service = RepositoryService(rag, llm)
    return await service.answer(repository_id, req.question)
