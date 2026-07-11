"""Error / stack-trace debugging endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUserDep, LLMDep, RagDep, SessionDep
from app.schemas.chat import Answer, DebugRequest
from app.services.conversation_service import ConversationService
from app.services.debug_service import DebugService

router = APIRouter(prefix="/debug", tags=["debug"])


@router.post("", response_model=Answer)
async def debug(
    req: DebugRequest,
    rag: RagDep,
    llm: LLMDep,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Answer:
    """Analyse an error/stack trace and return corrected code with citations."""
    service = DebugService(rag, llm)
    answer = await service.debug(
        req.error, req.language, req.code_context, req.repository_id
    )

    first_line = req.error.strip().splitlines()[0] if req.error.strip() else "Debug"
    convo = ConversationService(session)
    answer.conversation_id = await convo.record_turn(
        user_id=current_user.id,
        conversation_id=None,
        kind="debug",
        question=f"Debug: {first_line[:120]}",
        answer_text=answer.text,
        citations=answer.citations,
        repository_id=req.repository_id,
    )
    return answer
