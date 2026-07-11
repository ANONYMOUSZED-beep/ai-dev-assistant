"""Documentation chat endpoints."""

from __future__ import annotations

import orjson
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.core.deps import CurrentUserDep, LLMDep, RagDep, SessionDep
from app.schemas.chat import Answer, ChatRequest
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/chat", tags=["chat"])

_KIND = "docs"


@router.post("", response_model=Answer)
async def chat(
    req: ChatRequest,
    rag: RagDep,
    llm: LLMDep,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Answer:
    """Answer a documentation question with grounded citations and persist the turn."""
    service = ChatService(rag, llm)
    answer = await service.answer(req.question, req.collection)

    convo = ConversationService(session)
    answer.conversation_id = await convo.record_turn(
        user_id=current_user.id,
        conversation_id=req.conversation_id,
        kind=_KIND,
        question=req.question,
        answer_text=answer.text,
        citations=answer.citations,
        collection=req.collection,
    )
    return answer


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    rag: RagDep,
    llm: LLMDep,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> EventSourceResponse:
    """Stream a documentation answer token-by-token, then emit citations.

    A ``meta`` event carrying the conversation id is emitted first so the client can
    track which conversation the streamed turn belongs to. The full turn is persisted
    once streaming completes.
    """
    service = ChatService(rag, llm)
    convo = ConversationService(session)

    # Resolve/create the conversation up front so the client learns its id immediately.
    conversation = await convo.resolve(
        user_id=current_user.id,
        conversation_id=req.conversation_id,
        kind=_KIND,
        first_message=req.question,
        collection=req.collection,
    )
    await session.commit()

    async def event_generator():
        yield {
            "event": "meta",
            "data": orjson.dumps({"conversation_id": conversation.id}).decode(),
        }
        citations = (
            await service.retrieve_citations(req.question, req.collection)
        ).citations
        yield {
            "event": "citations",
            "data": orjson.dumps([c.model_dump() for c in citations]).decode(),
        }
        acc = ""
        async for token in service.stream(req.question, req.collection):
            acc += token
            yield {"event": "token", "data": token}

        # Persist the completed turn.
        await convo.add_message(conversation, "user", req.question)
        await convo.add_message(conversation, "assistant", acc, citations)
        await session.commit()

        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())
