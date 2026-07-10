"""Documentation chat endpoints."""

from __future__ import annotations

import orjson
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.core.deps import LLMDep, RagDep
from app.schemas.chat import Answer, ChatRequest
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=Answer)
async def chat(req: ChatRequest, rag: RagDep, llm: LLMDep) -> Answer:
    """Answer a documentation question with grounded citations.

    This is the non-streaming endpoint; use ``/chat/stream`` for token streaming.
    """
    service = ChatService(rag, llm)
    return await service.answer(req.question, req.collection)


@router.post("/stream")
async def chat_stream(req: ChatRequest, rag: RagDep, llm: LLMDep) -> EventSourceResponse:
    """Stream a documentation answer token-by-token, then emit citations."""
    service = ChatService(rag, llm)

    async def event_generator():
        citations = (await service.retrieve_citations(req.question, req.collection)).citations
        yield {
            "event": "citations",
            "data": orjson.dumps([c.model_dump() for c in citations]).decode(),
        }
        async for token in service.stream(req.question, req.collection):
            yield {"event": "token", "data": token}
        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())
