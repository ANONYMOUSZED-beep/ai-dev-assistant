"""Tests for the in-memory, per-session repository registry."""

from __future__ import annotations

import pytest
from app.services.repo_registry import RepositoryRegistry

pytestmark = pytest.mark.asyncio


async def test_create_and_get() -> None:
    reg = RepositoryRegistry()
    rec = await reg.create("s1", "https://github.com/octocat/Hello-World", "main")
    assert rec.id
    assert rec.status == "pending"
    fetched = await reg.get("s1", rec.id)
    assert fetched is not None
    assert fetched.url == "https://github.com/octocat/Hello-World"
    assert fetched.branch == "main"


async def test_update_status_and_counts() -> None:
    reg = RepositoryRegistry()
    rec = await reg.create("s1", "https://github.com/x/y", None)
    await reg.update("s1", rec.id, status="ready", files_indexed=3, chunks_indexed=42)
    updated = await reg.get("s1", rec.id)
    assert updated is not None
    assert updated.status == "ready"
    assert updated.files_indexed == 3
    assert updated.chunks_indexed == 42


async def test_list_and_delete() -> None:
    reg = RepositoryRegistry()
    a = await reg.create("s1", "https://github.com/a/a", None)
    b = await reg.create("s1", "https://github.com/b/b", None)
    ids = {r.id for r in await reg.list("s1")}
    assert ids == {a.id, b.id}

    assert await reg.delete("s1", a.id) is True
    assert await reg.delete("s1", a.id) is False  # already gone
    remaining = {r.id for r in await reg.list("s1")}
    assert remaining == {b.id}


async def test_sessions_are_isolated() -> None:
    reg = RepositoryRegistry()
    a = await reg.create("alice", "https://github.com/alice/repo", None)
    b = await reg.create("bob", "https://github.com/bob/repo", None)

    # Each session only lists its own repositories.
    assert [r.id for r in await reg.list("alice")] == [a.id]
    assert [r.id for r in await reg.list("bob")] == [b.id]

    # Cross-session access is denied.
    assert await reg.get("bob", a.id) is None
    assert await reg.delete("bob", a.id) is False
    assert await reg.get("alice", a.id) is not None


async def test_update_missing_returns_none() -> None:
    reg = RepositoryRegistry()
    assert await reg.update("s1", "nope", status="ready") is None
    assert await reg.get("s1", "nope") is None
