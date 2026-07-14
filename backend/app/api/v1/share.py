"""Public, read-only share endpoint for published conversations.

This router is intentionally *unauthenticated*: anyone holding a conversation's
share token may view its full message history. It is mounted in the public section
of the API router (alongside health and auth), not behind the JWT guard.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import SessionDep
from app.core.exceptions import NotFoundError
from app.schemas.conversation import ConversationDetail
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/share", tags=["share"])


@router.get("/{share_id}", response_model=ConversationDetail)
async def get_shared_conversation(
    share_id: str, session: SessionDep
) -> ConversationDetail:
    """Return a shared conversation by its public token (no auth required)."""
    service = ConversationService(session)
    detail = await service.get_by_share_id(share_id)
    if detail is None:
        raise NotFoundError(f"Shared conversation {share_id} not found")
    return detail
