"""Error / stack-trace debugging endpoint."""

from __future__ import annotations

import orjson
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.core.deps import CurrentUserDep, LLMDep, RagDep, SessionDep
from app.schemas.chat import Answer, DebugRequest
from app.services.conversation_service import ConversationService
from app.services.debug_service import DebugService
from app.services.enrich import generate_follow_ups

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


@router.post("/stream")
async def debug_stream(
    req: DebugRequest,
    rag: RagDep,
    llm: LLMDep,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> EventSourceResponse:
    """Stream a debug answer token-by-token, then persist the turn."""
    service = DebugService(rag, llm)
    convo = ConversationService(session)

    first_line = req.error.strip().splitlines()[0] if req.error.strip() else "Debug"
    summary = f"Debug: {first_line[:120]}"
    conversation = await convo.resolve(
        user_id=current_user.id,
        conversation_id=None,
        kind="debug",
        first_message=summary,
        repository_id=req.repository_id,
    )
    await session.commit()

    async def event_generator():
        yield {
            "event": "meta",
            "data": orjson.dumps({"conversation_id": conversation.id}).decode(),
        }
        citations = (
            await service.retrieve_citations(
                req.error, req.language, req.code_context, req.repository_id
            )
        ).citations
        yield {
            "event": "citations",
            "data": orjson.dumps([c.model_dump() for c in citations]).decode(),
        }
        acc = ""
        async for token in service.stream(
            req.error, req.language, req.code_context, req.repository_id
        ):
            acc += token
            yield {"event": "token", "data": token}

        await convo.add_message(conversation, "user", summary)
        await convo.add_message(conversation, "assistant", acc, citations)
        await session.commit()

        # Follow-ups are an extra LLM call; skip for guests to cap demo cost.
        if not current_user.is_guest:
            follow_ups = await generate_follow_ups(llm, req.error, acc)
            if follow_ups:
                yield {
                    "event": "followups",
                    "data": orjson.dumps(follow_ups).decode(),
                }
        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())
