"""Structure-aware document chunking.

Prose is split with a recursive character splitter; source code is split with a
language-aware splitter when the language can be inferred (best-effort, falling back
to recursive splitting). Each :class:`Chunk` gets a deterministic id and, when the
chunk text can be located in its parent document, a derived ``start_line``/``end_line``.
"""

from __future__ import annotations

import hashlib
import os
from typing import TYPE_CHECKING

from app.schemas.rag import Chunk, Document, SourceType

if TYPE_CHECKING:
    from langchain_text_splitters import RecursiveCharacterTextSplitter

# Map common file extensions to ``langchain_text_splitters.Language`` member names.
# Resolved lazily against the installed enum so unknown members degrade gracefully.
_EXTENSION_LANGUAGE: dict[str, str] = {
    ".py": "PYTHON",
    ".js": "JS",
    ".jsx": "JS",
    ".mjs": "JS",
    ".cjs": "JS",
    ".ts": "TS",
    ".tsx": "TS",
    ".java": "JAVA",
    ".go": "GO",
    ".rs": "RUST",
    ".rb": "RUBY",
    ".php": "PHP",
    ".c": "C",
    ".h": "C",
    ".cpp": "CPP",
    ".cc": "CPP",
    ".cxx": "CPP",
    ".hpp": "CPP",
    ".cs": "CSHARP",
    ".scala": "SCALA",
    ".swift": "SWIFT",
    ".kt": "KOTLIN",
    ".kts": "KOTLIN",
    ".sol": "SOL",
    ".lua": "LUA",
    ".pl": "PERL",
    ".hs": "HASKELL",
    ".md": "MARKDOWN",
    ".markdown": "MARKDOWN",
    ".rst": "RST",
    ".tex": "LATEX",
    ".html": "HTML",
    ".htm": "HTML",
}

_CODE_SOURCE_TYPES = {SourceType.CODE, SourceType.GITHUB}


class Chunker:
    """Split :class:`Document` objects into :class:`Chunk` objects.

    Construction is cheap: the heavy ``langchain_text_splitters`` import is deferred to
    the first :meth:`chunk` call.
    """

    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def chunk_documents(self, documents: list[Document]) -> list[Chunk]:
        """Chunk every document, concatenating the results in order."""
        chunks: list[Chunk] = []
        for document in documents:
            chunks.extend(self.chunk(document))
        return chunks

    def chunk(self, document: Document) -> list[Chunk]:
        """Split a single document into chunks."""
        content = document.content
        if not content.strip():
            return []

        splitter = self._build_splitter(document)
        pieces = [p for p in splitter.split_text(content) if p.strip()]

        chunks: list[Chunk] = []
        cursor = 0
        for index, piece in enumerate(pieces):
            start_line, end_line, cursor = self._locate(content, piece, cursor)
            chunks.append(
                Chunk(
                    id=self._chunk_id(document.source_id, index),
                    document_id=document.source_id,
                    content=piece,
                    source_type=document.source_type,
                    source_id=document.source_id,
                    title=document.title,
                    uri=document.uri,
                    start_line=start_line,
                    end_line=end_line,
                    metadata={**document.metadata, "chunk_index": index},
                )
            )
        return chunks

    # ── Internals ────────────────────────────────────────────────
    def _build_splitter(self, document: Document) -> RecursiveCharacterTextSplitter:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        if document.source_type in _CODE_SOURCE_TYPES:
            language = self._infer_language(document)
            if language is not None:
                splitter = self._language_splitter(language)
                if splitter is not None:
                    return splitter
        return RecursiveCharacterTextSplitter(
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
            length_function=len,
        )

    def _language_splitter(
        self, language_name: str
    ) -> RecursiveCharacterTextSplitter | None:
        from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

        language = getattr(Language, language_name, None)
        if language is None:
            return None
        try:
            return RecursiveCharacterTextSplitter.from_language(
                language=language,
                chunk_size=self._chunk_size,
                chunk_overlap=self._chunk_overlap,
            )
        except (ValueError, KeyError):
            return None

    def _infer_language(self, document: Document) -> str | None:
        explicit = document.metadata.get("language")
        if isinstance(explicit, str):
            mapped = _EXTENSION_LANGUAGE.get(explicit.lower())
            if mapped is not None:
                return mapped
            return explicit.upper()
        for candidate in (document.uri, document.source_id):
            if not candidate:
                continue
            ext = os.path.splitext(candidate.split(":")[-1])[1].lower()
            if ext in _EXTENSION_LANGUAGE:
                return _EXTENSION_LANGUAGE[ext]
        return None

    @staticmethod
    def _locate(
        content: str, piece: str, cursor: int
    ) -> tuple[int | None, int | None, int]:
        """Return ``(start_line, end_line, next_cursor)`` for ``piece`` in ``content``."""
        pos = content.find(piece, cursor)
        if pos == -1:
            pos = content.find(piece)
        if pos == -1:
            return None, None, cursor
        start_line = content.count("\n", 0, pos) + 1
        end_line = start_line + piece.count("\n")
        return start_line, end_line, pos + len(piece)

    @staticmethod
    def _chunk_id(source_id: str, index: int) -> str:
        digest = hashlib.sha256(f"{source_id}:{index}".encode()).hexdigest()
        return digest[:32]
