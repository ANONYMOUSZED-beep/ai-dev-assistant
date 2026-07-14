"""AI pair-programmer endpoint."""

from __future__ import annotations

import orjson
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.core.deps import CurrentUserDep, LLMDep, RagDep, SessionDep
from app.schemas.chat import Answer, PairRequest
from app.services.conversation_service import ConversationService
from app.services.enrich import generate_follow_ups
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


@router.post("/stream")
async def pair_stream(
    req: PairRequest,
    rag: RagDep,
    llm: LLMDep,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> EventSourceResponse:
    """Stream a pair-programming answer token-by-token, then persist the turn."""
    service = PairService(rag, llm)
    convo = ConversationService(session)

    title = f"Pair · {req.action}"
    if req.instructions:
        title += f": {req.instructions[:80]}"
    conversation = await convo.resolve(
        user_id=current_user.id,
        conversation_id=None,
        kind="pair",
        first_message=title,
    )
    await session.commit()

    async def event_generator():
        yield {
            "event": "meta",
            "data": orjson.dumps({"conversation_id": conversation.id}).decode(),
        }
        citations = (
            await service.retrieve_citations(
                req.action, req.code, req.language, req.instructions
            )
        ).citations
        yield {
            "event": "citations",
            "data": orjson.dumps([c.model_dump() for c in citations]).decode(),
        }
        acc = ""
        async for token in service.stream(
            req.action, req.code, req.language, req.instructions
        ):
            acc += token
            yield {"event": "token", "data": token}

        await convo.add_message(conversation, "user", title)
        await convo.add_message(conversation, "assistant", acc, citations)
        await session.commit()

        # Follow-ups are an extra LLM call; skip for guests to cap demo cost.
        if not current_user.is_guest:
            follow_ups = await generate_follow_ups(llm, f"{req.action} this code", acc)
            if follow_ups:
                yield {
                    "event": "followups",
                    "data": orjson.dumps(follow_ups).decode(),
                }
        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())
