"""GitHub repository endpoints: connect/index, status, and chat.

Repository metadata is held in an in-memory registry (see
:mod:`app.services.repo_registry`), so this feature needs no database. The
indexed vectors live in the vector store under the ``repo:{id}`` collection.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks

from app.core.deps import LLMDep, RagDep, SessionIdDep
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.schemas.chat import (
    Answer,
    IndexStatus,
    RepoChatRequest,
    RepositoryCreateRequest,
    RepositoryResponse,
)
from app.services.repo_registry import RepoRecord, registry
from app.services.repository_service import RepositoryService

logger = get_logger(__name__)
router = APIRouter(prefix="/repositories", tags=["repositories"])


def _to_response(record: RepoRecord) -> RepositoryResponse:
    return RepositoryResponse(
        id=record.id,
        url=record.url,
        branch=record.branch,
        status=IndexStatus(record.status),
        files_indexed=record.files_indexed,
        chunks_indexed=record.chunks_indexed,
        error=record.error,
    )


async def _index_repo(
    session_id: str,
    repository_id: str,
    url: str,
    branch: str | None,
    service: RepositoryService,
) -> None:
    """Background task: index a repository and persist its status in the registry."""
    await registry.update(session_id, repository_id, status=IndexStatus.INDEXING.value)
    try:
        files, chunks = await service.index(repository_id, url, branch)
        await registry.update(
            session_id,
            repository_id,
            files_indexed=files,
            chunks_indexed=chunks,
            status=IndexStatus.READY.value,
        )
    except Exception as exc:  # noqa: BLE001 - network/IO dependent; surface as failed
        logger.exception("Repository indexing failed")
        await registry.update(
            session_id, repository_id, status=IndexStatus.FAILED.value, error=str(exc)
        )


@router.post("", response_model=RepositoryResponse, status_code=202)
async def create_repository(
    req: RepositoryCreateRequest,
    background: BackgroundTasks,
    rag: RagDep,
    llm: LLMDep,
    session_id: SessionIdDep,
) -> RepositoryResponse:
    """Register a repository and index it in the background (scoped to the session)."""
    record = await registry.create(session_id, req.url, req.branch)
    service = RepositoryService(rag, llm)
    background.add_task(_index_repo, session_id, record.id, req.url, req.branch, service)
    return _to_response(record)


@router.get("/{repository_id}", response_model=RepositoryResponse)
async def get_repository(
    repository_id: str, session_id: SessionIdDep
) -> RepositoryResponse:
    """Return indexing status for a repository in this session."""
    record = await registry.get(session_id, repository_id)
    if record is None:
        raise NotFoundError(f"Repository {repository_id} not found")
    return _to_response(record)


@router.delete("/{repository_id}")
async def delete_repository(
    repository_id: str, session_id: SessionIdDep
) -> dict[str, str]:
    """Remove a repository from this session's registry."""
    if not await registry.delete(session_id, repository_id):
        raise NotFoundError(f"Repository {repository_id} not found")
    return {"deleted": repository_id}


@router.get("", response_model=list[RepositoryResponse])
async def list_repositories(session_id: SessionIdDep) -> list[RepositoryResponse]:
    """List repositories registered in this session only."""
    return [_to_response(record) for record in await registry.list(session_id)]


@router.post("/{repository_id}/chat", response_model=Answer)
async def repository_chat(
    repository_id: str,
    req: RepoChatRequest,
    rag: RagDep,
    llm: LLMDep,
    session_id: SessionIdDep,
) -> Answer:
    """Chat over an indexed repository owned by this session."""
    record = await registry.get(session_id, repository_id)
    if record is None:
        raise NotFoundError(f"Repository {repository_id} not found")
    service = RepositoryService(rag, llm)
    return await service.answer(repository_id, req.question)
