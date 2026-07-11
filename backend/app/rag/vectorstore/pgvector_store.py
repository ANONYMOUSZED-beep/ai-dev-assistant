"""Postgres + pgvector vector store.

Persists chunk embeddings in the same Postgres database used for users/repositories,
so indexed content survives restarts with no extra infrastructure. Uses a synchronous
psycopg2 connection pool (the pipeline calls these methods inside ``asyncio.to_thread``)
and exact cosine KNN — dimension-agnostic, which keeps it embedder-independent at demo
scale.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from typing import TYPE_CHECKING, Any

from app.core.logging import get_logger
from app.schemas.rag import Chunk, RetrievedChunk, SourceType

if TYPE_CHECKING:
    from psycopg2.pool import ThreadedConnectionPool

logger = get_logger(__name__)

_TABLE = "vector_chunks"

# Fail fast instead of hanging forever if the managed DB is unreachable or a
# statement stalls (e.g. connecting to a suspended Neon endpoint). Without these,
# a stalled connection would block the request until the platform proxy drops it.
_CONNECT_TIMEOUT_SECONDS = 15
_STATEMENT_TIMEOUT_MS = 30000


def _to_vector_literal(vector: list[float]) -> str:
    """pgvector text form: ``[0.1,0.2,...]`` (cast to ::vector in SQL)."""
    return "[" + ",".join(f"{x:.7g}" for x in vector) + "]"


class PgVectorStore:
    """VectorStore implementation backed by Postgres + the pgvector extension."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: ThreadedConnectionPool | None = None
        # Reentrant: _ensure_schema() holds this lock and then calls _get_pool(),
        # which re-acquires it. A plain Lock would self-deadlock on first use.
        self._lock = threading.RLock()
        self._ready = False

    # ── Pool / schema ────────────────────────────────────────────
    def _get_pool(self) -> ThreadedConnectionPool:
        if self._pool is None:
            with self._lock:
                if self._pool is None:
                    from psycopg2.pool import ThreadedConnectionPool

                    logger.info("pgvector: creating connection pool")
                    # ``connect_timeout`` bounds the initial TCP/TLS handshake so an
                    # unreachable/suspended host fails fast instead of hanging.
                    #
                    # NOTE: we intentionally do NOT pass a libpq ``options`` startup
                    # parameter here. Neon's connection pooler (PgBouncer) can hang the
                    # connection handshake on startup options it doesn't recognise. We
                    # set ``statement_timeout`` per session with a plain ``SET`` after
                    # checkout instead (see ``_checkout``).
                    self._pool = ThreadedConnectionPool(
                        1,
                        8,
                        dsn=self._dsn,
                        connect_timeout=_CONNECT_TIMEOUT_SECONDS,
                    )
                    logger.info("pgvector: connection pool ready")
        return self._pool

    @contextmanager
    def _checkout(self, *, autocommit: bool = False) -> Iterator[Any]:
        """Check a connection out of the pool with a bounded statement timeout.

        Setting ``statement_timeout`` in-session (rather than as a libpq startup
        option) keeps us compatible with Neon's pooler while still ensuring a stalled
        statement can't block a request indefinitely. ``autocommit`` is used for DDL so
        ``CREATE EXTENSION``/``CREATE TABLE`` don't sit inside an open transaction.
        """
        conn = self._get_pool().getconn()
        try:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(f"SET statement_timeout = {int(_STATEMENT_TIMEOUT_MS)}")
            conn.autocommit = autocommit
            yield conn
        finally:
            # Clear any open transaction (e.g. read-only SELECTs) before returning the
            # connection to the pool so the next borrower starts clean.
            with suppress(Exception):
                if not conn.autocommit:
                    conn.rollback()
            with suppress(Exception):
                conn.autocommit = False
            self._get_pool().putconn(conn)

    def warmup(self) -> None:
        """Create the schema at startup so the first request isn't on the DDL path."""
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        if self._ready:
            return
        with self._lock:
            if self._ready:
                return
            logger.info("pgvector: ensuring schema (extension + table)")
            # autocommit=True: run each DDL statement standalone so a slow/blocked one
            # can't leave an open transaction, and so CREATE EXTENSION applies cleanly.
            with self._checkout(autocommit=True) as conn, conn.cursor() as cur:
                logger.info("pgvector: creating extension 'vector'")
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                logger.info("pgvector: creating table %s", _TABLE)
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {_TABLE} (
                        id TEXT PRIMARY KEY,
                        collection TEXT NOT NULL,
                        embedding vector NOT NULL,
                        content TEXT NOT NULL,
                        document_id TEXT,
                        source_type TEXT,
                        source_id TEXT,
                        title TEXT,
                        uri TEXT,
                        start_line INTEGER,
                        end_line INTEGER,
                        metadata JSONB
                    )
                    """
                )
                logger.info("pgvector: creating index")
                cur.execute(
                    f"CREATE INDEX IF NOT EXISTS ix_{_TABLE}_collection "
                    f"ON {_TABLE} (collection)"
                )
            self._ready = True
            logger.info("pgvector: schema ready")

    # ── VectorStore protocol ─────────────────────────────────────
    def add(
        self, collection: str, chunks: list[Chunk], vectors: list[list[float]]
    ) -> None:
        if not chunks:
            return
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        self._ensure_schema()

        from psycopg2.extras import execute_values

        rows = [
            (
                c.id,
                collection,
                _to_vector_literal(v),
                c.content,
                c.document_id,
                c.source_type.value,
                c.source_id,
                c.title,
                c.uri,
                c.start_line,
                c.end_line,
                json.dumps(c.metadata),
            )
            for c, v in zip(chunks, vectors, strict=True)
        ]
        logger.info("pgvector: inserting %d rows into %s", len(rows), collection)
        with self._checkout() as conn, conn.cursor() as cur:
            execute_values(
                cur,
                f"""
                INSERT INTO {_TABLE}
                    (id, collection, embedding, content, document_id, source_type,
                     source_id, title, uri, start_line, end_line, metadata)
                VALUES %s
                ON CONFLICT (id) DO UPDATE SET
                    collection = EXCLUDED.collection,
                    embedding = EXCLUDED.embedding,
                    content = EXCLUDED.content,
                    metadata = EXCLUDED.metadata
                """,
                rows,
                template="(%s,%s,%s::vector,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)",
            )
            conn.commit()
            logger.info("pgvector: insert committed (%d rows)", len(rows))

    def search(
        self, collection: str, query_vector: list[float], top_k: int
    ) -> list[RetrievedChunk]:
        self._ensure_schema()
        qvec = _to_vector_literal(query_vector)
        with self._checkout() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, content, document_id, source_type, source_id, title, uri,
                       start_line, end_line, metadata,
                       1 - (embedding <=> %s::vector) AS score
                FROM {_TABLE}
                WHERE collection = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (qvec, collection, qvec, top_k),
            )
            rows = cur.fetchall()

        results: list[RetrievedChunk] = []
        for row in rows:
            score = float(row[10])
            results.append(
                RetrievedChunk(chunk=_row_to_chunk(row), score=score, dense_score=score)
            )
        return results

    def all_chunks(self, collection: str) -> list[Chunk]:
        self._ensure_schema()
        with self._checkout() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, content, document_id, source_type, source_id, title, uri,
                       start_line, end_line, metadata
                FROM {_TABLE}
                WHERE collection = %s
                """,
                (collection,),
            )
            rows = cur.fetchall()
        return [_row_to_chunk(row) for row in rows]

    def delete_collection(self, collection: str) -> None:
        self._ensure_schema()
        with self._checkout() as conn, conn.cursor() as cur:
            cur.execute(f"DELETE FROM {_TABLE} WHERE collection = %s", (collection,))
            conn.commit()


def _row_to_chunk(row: Any) -> Chunk:
    metadata = row[9]
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {}
    return Chunk(
        id=row[0],
        content=row[1],
        document_id=row[2] or row[0],
        source_type=SourceType(row[3]) if row[3] else SourceType.CODE,
        source_id=row[4] or row[0],
        title=row[5],
        uri=row[6],
        start_line=row[7],
        end_line=row[8],
        metadata=metadata or {},
    )
