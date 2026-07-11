"""Chat history endpoints: list, fetch, rename, and delete conversations."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.deps import CurrentUserDep, SessionDep
from app.core.exceptions import NotFoundError
from app.schemas.conversation import (
    ConversationDetail,
    ConversationKind,
    ConversationSummary,
    RenameConversationRequest,
)
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationSummary])
async def list_conversations(
    session: SessionDep,
    current_user: CurrentUserDep,
    kind: ConversationKind | None = Query(default=None),
) -> list[ConversationSummary]:
    """List the current user's conversations, newest first (optionally by kind)."""
    service = ConversationService(session)
    return await service.list_summaries(current_user.id, kind)


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str, session: SessionDep, current_user: CurrentUserDep
) -> ConversationDetail:
    """Return one conversation with its full message history."""
    service = ConversationService(session)
    detail = await service.get_detail(current_user.id, conversation_id)
    if detail is None:
        raise NotFoundError(f"Conversation {conversation_id} not found")
    return detail


@router.patch("/{conversation_id}", response_model=ConversationSummary)
async def rename_conversation(
    conversation_id: str,
    req: RenameConversationRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ConversationSummary:
    """Rename a conversation."""
    service = ConversationService(session)
    summary = await service.rename(current_user.id, conversation_id, req.title)
    if summary is None:
        raise NotFoundError(f"Conversation {conversation_id} not found")
    return summary


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str, session: SessionDep, current_user: CurrentUserDep
) -> dict[str, str]:
    """Delete a conversation and its messages."""
    service = ConversationService(session)
    ok = await service.delete(current_user.id, conversation_id)
    if not ok:
        raise NotFoundError(f"Conversation {conversation_id} not found")
    return {"deleted": conversation_id}
