"""In-memory repository registry.

Repository metadata (id, url, indexing status, counts) is small and, for this
deployment model, ephemeral — the FAISS vectors it points at are themselves
rebuilt per process. Keeping the registry in memory removes the hard dependency
on Postgres so Repo Chat works on any host (e.g. a free Hugging Face Space)
without provisioning a database.

Access is guarded by an asyncio lock. This is process-local (single replica),
which matches the single-container deployment target.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass


@dataclass
class RepoRecord:
    """A tracked repository and its indexing state."""

    id: str
    url: str
    branch: str | None
    status: str
    files_indexed: int = 0
    chunks_indexed: int = 0
    error: str | None = None


class RepositoryRegistry:
    """Async-safe, in-memory store of :class:`RepoRecord` objects, per session.

    Records are bucketed by an opaque ``session_id`` so each client only sees the
    repositories they added. Repository ids are globally unique (UUIDs), so the
    vector-store collections keyed by id stay isolated too.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, RepoRecord]] = {}
        self._lock = asyncio.Lock()

    async def create(self, session_id: str, url: str, branch: str | None) -> RepoRecord:
        async with self._lock:
            record = RepoRecord(
                id=uuid.uuid4().hex[:12],
                url=url,
                branch=branch,
                status="pending",
            )
            self._sessions.setdefault(session_id, {})[record.id] = record
            return record

    async def get(self, session_id: str, repository_id: str) -> RepoRecord | None:
        async with self._lock:
            return self._sessions.get(session_id, {}).get(repository_id)

    async def list(self, session_id: str) -> list[RepoRecord]:
        async with self._lock:
            return list(self._sessions.get(session_id, {}).values())

    async def delete(self, session_id: str, repository_id: str) -> bool:
        async with self._lock:
            bucket = self._sessions.get(session_id)
            if bucket is not None and repository_id in bucket:
                del bucket[repository_id]
                return True
            return False

    async def update(
        self, session_id: str, repository_id: str, **changes: object
    ) -> RepoRecord | None:
        async with self._lock:
            record = self._sessions.get(session_id, {}).get(repository_id)
            if record is not None:
                for key, value in changes.items():
                    setattr(record, key, value)
            return record


#: Process-wide singleton registry.
registry = RepositoryRegistry()
