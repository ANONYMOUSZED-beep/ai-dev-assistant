"""Semantic code search service (pure retrieval, no generation)."""

from __future__ import annotations

from app.rag.pipeline import RagPipeline
from app.schemas.chat import CodeSearchHit, CodeSearchResponse
from app.services.repository_service import repo_collection


class SearchService:
    """Natural-language semantic search over indexed code."""

    def __init__(self, rag: RagPipeline) -> None:
        self._rag = rag

    async def search(
        self, query: str, repository_id: str | None = None, top_k: int = 10
    ) -> CodeSearchResponse:
        collection = repo_collection(repository_id) if repository_id else "code"
        chunks = await self._rag.retrieve(query, collection, top_k=top_k)
        hits = [
            CodeSearchHit(
                path=rc.chunk.uri or rc.chunk.source_id,
                snippet=rc.chunk.content,
                start_line=rc.chunk.start_line,
                end_line=rc.chunk.end_line,
                score=rc.rerank_score if rc.rerank_score is not None else rc.score,
                symbol=(
                    str(rc.chunk.metadata.get("symbol"))
                    if rc.chunk.metadata.get("symbol")
                    else None
                ),
            )
            for rc in chunks
        ]
        return CodeSearchResponse(query=query, hits=hits)
