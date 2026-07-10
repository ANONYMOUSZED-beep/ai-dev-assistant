"""Unit tests for citation building, prompt construction, config, and schemas."""

from __future__ import annotations

from app.core.config import Settings
from app.llm import prompts
from app.rag.contracts import build_citations
from app.schemas.chat import PairAction
from app.schemas.rag import Chunk, RetrievedChunk, SourceType


def _chunk(content: str = "x" * 300) -> RetrievedChunk:
    chunk = Chunk(
        id="c1",
        document_id="d1",
        content=content,
        source_type=SourceType.CODE,
        source_id="repo/app.py",
        title="app.py",
        uri="repo/app.py",
        start_line=10,
        end_line=20,
    )
    return RetrievedChunk(chunk=chunk, score=0.5, rerank_score=0.8)


def test_build_citations_indexes_and_truncates() -> None:
    citations = build_citations([_chunk(), _chunk()])
    assert [c.index for c in citations] == [1, 2]
    # long snippets are truncated with an ellipsis
    assert citations[0].snippet.endswith("...")
    # rerank score preferred over base score
    assert citations[0].score == 0.8


def test_build_citations_empty() -> None:
    assert build_citations([]) == []


def test_format_context_numbers_blocks() -> None:
    text = prompts.format_context([_chunk("hello")])
    assert "[1]" in text
    assert "app.py" in text
    assert "10-20" in text


def test_format_context_empty() -> None:
    assert prompts.format_context([]) == "(no context retrieved)"


def test_doc_qa_prompt_has_system_and_user() -> None:
    msgs = prompts.build_doc_qa_messages("What is DI?", [_chunk("ctx")])
    assert len(msgs) == 2
    assert msgs[0].role.value == "system"
    assert "What is DI?" in msgs[1].content


def test_pair_prompt_includes_action_instruction() -> None:
    msgs = prompts.build_pair_messages(PairAction.TEST, "def f(): ...", [])
    joined = " ".join(m.content for m in msgs)
    assert "unit test" in joined.lower()


def test_settings_computed_urls() -> None:
    s = Settings(
        database_url=None,
        postgres_user="u",
        postgres_password="p",
        postgres_host="h",
        postgres_port=5432,
        postgres_db="d",
        redis_host="r",
        redis_port=6379,
        redis_db=2,
    )
    assert s.async_database_url == "postgresql+asyncpg://u:p@h:5432/d"
    assert s.redis_url == "redis://r:6379/2"
    assert s.is_production is False
