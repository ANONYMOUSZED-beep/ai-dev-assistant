"""Tests for AI-suggested follow-up questions."""

from __future__ import annotations

import pytest
from app.services.chat_service import ChatService, _clean_follow_ups
from app.services.repository_service import RepositoryService

from tests.conftest import FakeLLMProvider, FakeRagPipeline


def test_clean_follow_ups_strips_bullets_numbers_and_quotes() -> None:
    raw = (
        "1. How do I deploy this?\n"
        '- "What about testing?"\n'
        "* Can I scale it horizontally?\n"
        "\n"
        "4) One extra that should be dropped\n"
    )
    result = _clean_follow_ups(raw)
    assert result == [
        "How do I deploy this?",
        "What about testing?",
        "Can I scale it horizontally?",
    ]
    assert len(result) <= 3


def test_clean_follow_ups_empty() -> None:
    assert _clean_follow_ups("") == []


@pytest.mark.asyncio
async def test_chat_service_follow_ups_returns_list() -> None:
    service = ChatService(FakeRagPipeline(), FakeLLMProvider())
    follow_ups = await service.follow_ups("What is FastAPI?", "FastAPI is a web framework.")
    assert isinstance(follow_ups, list)
    assert len(follow_ups) <= 3


@pytest.mark.asyncio
async def test_chat_service_answer_populates_follow_ups() -> None:
    service = ChatService(FakeRagPipeline(), FakeLLMProvider())
    answer = await service.answer("What is FastAPI?", "docs")
    assert isinstance(answer.follow_ups, list)


@pytest.mark.asyncio
async def test_repository_service_follow_ups_returns_list() -> None:
    service = RepositoryService(FakeRagPipeline(), FakeLLMProvider())
    follow_ups = await service.follow_ups("Where is the entrypoint?", "It is in app/main.py.")
    assert isinstance(follow_ups, list)
    assert len(follow_ups) <= 3


@pytest.mark.asyncio
async def test_repository_service_answer_populates_follow_ups() -> None:
    service = RepositoryService(FakeRagPipeline(), FakeLLMProvider())
    answer = await service.answer("repo-1", "Where is the entrypoint?")
    assert isinstance(answer.follow_ups, list)
