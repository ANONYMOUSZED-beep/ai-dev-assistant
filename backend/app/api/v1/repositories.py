"""GitHub repository endpoints: connect/index, status, and chat.

Repositories are persisted in the database and scoped to the authenticated user,
so each account only sees its own — and they survive restarts.
"""

from __future__ import annotations

import orjson
from fastapi import APIRouter, BackgroundTasks
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse

from app.core.deps import CurrentUserDep, LLMDep, RagDep, SessionDep
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
from app.services.conversation_service import ConversationService
from app.services.enrich import generate_follow_ups
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
        succeeded = False
        try:
            files, chunks = await service.index(repository_id, url, branch)
            repo.files_indexed, repo.chunks_indexed = files, chunks
            repo.status = IndexStatus.READY.value
            succeeded = True
        except Exception as exc:  # noqa: BLE001 - network/IO dependent
            logger.exception("Repository indexing failed")
            repo.status = IndexStatus.FAILED.value
            repo.error = str(exc)
        await session.commit()

        if not succeeded:
            return

        # Best-effort: generate a one-page architecture tour and save it as a
        # conversation so it shows up in the user's History. A failure here must
        # not flip the repo status — indexing already succeeded.
        try:
            overview = await service.generate_overview(repository_id)
            if overview.text:
                convo = ConversationService(session)
                conversation = await convo.create(
                    user_id=repo.user_id,
                    kind="repo",
                    title="Repository overview",
                    collection=repo.collection,
                    repository_id=repo.id,
                )
                await convo.add_message(
                    conversation, "user", "Give me an overview of this repository"
                )
                await convo.add_message(
                    conversation, "assistant", overview.text, overview.citations
                )
                await session.commit()
        except Exception:  # noqa: BLE001 - overview is best-effort, never break indexing
            logger.warning("Repository overview generation failed", exc_info=True)


@router.post("", response_model=RepositoryResponse, status_code=202)
async def create_repository(
    req: RepositoryCreateRequest,
    background: BackgroundTasks,
    session: SessionDep,
    rag: RagDep,
    llm: LLMDep,
    current_user: CurrentUserDep,
) -> RepositoryResponse:
    """Register a repository for the current user and index it in the background."""
    repo = Repository(
        user_id=current_user.id,
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
async def get_repository(
    repository_id: str, session: SessionDep, current_user: CurrentUserDep
) -> RepositoryResponse:
    """Return indexing status for one of the current user's repositories."""
    repo = await session.get(Repository, repository_id)
    if repo is None or repo.user_id != current_user.id:
        raise NotFoundError(f"Repository {repository_id} not found")
    return _to_response(repo)


@router.delete("/{repository_id}")
async def delete_repository(
    repository_id: str, session: SessionDep, current_user: CurrentUserDep
) -> dict[str, str]:
    """Remove one of the current user's repositories."""
    repo = await session.get(Repository, repository_id)
    if repo is None or repo.user_id != current_user.id:
        raise NotFoundError(f"Repository {repository_id} not found")
    await session.delete(repo)
    await session.commit()
    return {"deleted": repository_id}


@router.get("", response_model=list[RepositoryResponse])
async def list_repositories(
    session: SessionDep, current_user: CurrentUserDep
) -> list[RepositoryResponse]:
    """List the current user's repositories."""
    result = await session.execute(
        select(Repository).where(Repository.user_id == current_user.id)
    )
    return [_to_response(r) for r in result.scalars().all()]


@router.post("/{repository_id}/chat", response_model=Answer)
async def repository_chat(
    repository_id: str,
    req: RepoChatRequest,
    session: SessionDep,
    rag: RagDep,
    llm: LLMDep,
    current_user: CurrentUserDep,
) -> Answer:
    """Chat over one of the current user's indexed repositories and persist the turn."""
    repo = await session.get(Repository, repository_id)
    if repo is None or repo.user_id != current_user.id:
        raise NotFoundError(f"Repository {repository_id} not found")
    service = RepositoryService(rag, llm)
    answer = await service.answer(repository_id, req.question)

    convo = ConversationService(session)
    answer.conversation_id = await convo.record_turn(
        user_id=current_user.id,
        conversation_id=req.conversation_id,
        kind="repo",
        question=req.question,
        answer_text=answer.text,
        citations=answer.citations,
        collection=repo.collection,
        repository_id=repository_id,
    )
    return answer


@router.post("/{repository_id}/chat/stream")
async def repository_chat_stream(
    repository_id: str,
    req: RepoChatRequest,
    session: SessionDep,
    rag: RagDep,
    llm: LLMDep,
    current_user: CurrentUserDep,
) -> EventSourceResponse:
    """Stream a repository answer token-by-token, then persist the turn."""
    repo = await session.get(Repository, repository_id)
    if repo is None or repo.user_id != current_user.id:
        raise NotFoundError(f"Repository {repository_id} not found")

    service = RepositoryService(rag, llm)
    convo = ConversationService(session)
    conversation = await convo.resolve(
        user_id=current_user.id,
        conversation_id=req.conversation_id,
        kind="repo",
        first_message=req.question,
        collection=repo.collection,
        repository_id=repository_id,
    )
    await session.commit()

    async def event_generator():
        yield {
            "event": "meta",
            "data": orjson.dumps({"conversation_id": conversation.id}).decode(),
        }
        citations = (
            await service.retrieve_citations(repository_id, req.question)
        ).citations
        yield {
            "event": "citations",
            "data": orjson.dumps([c.model_dump() for c in citations]).decode(),
        }
        acc = ""
        async for token in service.stream(repository_id, req.question):
            acc += token
            yield {"event": "token", "data": token}

        if acc:
            try:
                follow_ups = await service.follow_ups(req.question, acc)
            except Exception:  # noqa: BLE001 - best-effort, never break the stream
                follow_ups = []
            yield {"event": "followups", "data": orjson.dumps(follow_ups).decode()}

        await convo.add_message(conversation, "user", req.question)
        await convo.add_message(conversation, "assistant", acc, citations)
        await session.commit()

        follow_ups = await generate_follow_ups(llm, req.question, acc)
        if follow_ups:
            yield {
                "event": "followups",
                "data": orjson.dumps(follow_ups).decode(),
            }

        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())
