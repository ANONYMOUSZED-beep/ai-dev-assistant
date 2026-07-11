"""AI pair-programmer endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUserDep, LLMDep, RagDep, SessionDep
from app.schemas.chat import Answer, PairRequest
from app.services.conversation_service import ConversationService
from app.services.pair_service import PairService

router = APIRouter(prefix="/pair", tags=["pair"])


@router.post("", response_model=Answer)
async def pair(
    req: PairRequest,
    rag: RagDep,
    llm: LLMDep,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Answer:
    """Run a pair-programming action (explain/refactor/test/document/optimize/security)."""
    service = PairService(rag, llm)
    answer = await service.run(req.action, req.code, req.language, req.instructions)

    title = f"Pair · {req.action}"
    if req.instructions:
        title += f": {req.instructions[:80]}"
    convo = ConversationService(session)
    answer.conversation_id = await convo.record_turn(
        user_id=current_user.id,
        conversation_id=None,
        kind="pair",
        question=title,
        answer_text=answer.text,
        citations=answer.citations,
    )
    return answer
