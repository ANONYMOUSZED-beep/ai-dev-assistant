"""Public, read-only access to shared conversations.

This router is mounted WITHOUT the global auth guard so a shared link can be opened
by anyone. Publishing/revoking a share is done from the authenticated
``/conversations/{id}/share`` endpoints.
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
    """Public: fetch a shared conversation by its share token (no auth required)."""
    detail = await ConversationService(session).get_by_share_id(share_id)
    if detail is None:
        raise NotFoundError("This shared link was not found or has been removed")
    return detail
