"""Document ingestion endpoints."""

from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, File, Form, UploadFile

from app.core.deps import RagDep
from app.core.exceptions import IngestionError
from app.rag.ingestion import load_source
from app.rag.ingestion.loaders import load_by_uri
from app.schemas.chat import IngestRequest, IngestResponse

router = APIRouter(prefix="/documents", tags=["documents"])

# Cap uploads to keep memory/latency bounded (free-tier friendly).
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MiB


@router.post("/ingest", response_model=IngestResponse)
async def ingest(req: IngestRequest, rag: RagDep) -> IngestResponse:
    """Ingest a document (by URI or raw text) into a collection."""
    if not req.uri and not req.text:
        raise IngestionError("Either 'uri' or 'text' must be provided")
    documents = load_source(
        source_type=req.source_type,
        uri=req.uri,
        text=req.text,
        title=req.title,
    )
    if not documents:
        raise IngestionError("No content could be loaded from the source")
    chunks = await rag.ingest(documents, req.collection)
    return IngestResponse(
        document_id=documents[0].source_id,
        collection=req.collection,
        chunks_indexed=chunks,
    )


@router.post("/upload", response_model=IngestResponse)
async def upload(
    rag: RagDep,
    collection: str = Form(...),
    file: UploadFile = File(...),
    title: str | None = Form(None),
) -> IngestResponse:
    """Ingest an uploaded file (PDF, DOCX, Markdown, HTML, text, or code).

    The file is parsed in-process via the matching loader (inferred from its
    extension) and indexed into ``collection``.
    """
    if not collection.strip():
        raise IngestionError("A collection name is required")

    data = await file.read()
    if not data:
        raise IngestionError("The uploaded file is empty")
    if len(data) > _MAX_UPLOAD_BYTES:
        raise IngestionError("File too large (max 10 MB)")

    filename = file.filename or "upload"
    suffix = os.path.splitext(filename)[1]
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            loaded = load_by_uri(tmp_path, title=title or filename)
        except Exception as exc:  # noqa: BLE001 - surface parse failures cleanly
            raise IngestionError(f"Could not parse '{filename}': {exc}") from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    # Rewrite transient temp-file identifiers to the original filename.
    documents = [
        doc.model_copy(
            update={"source_id": filename, "uri": None, "title": title or filename}
        )
        for doc in loaded
    ]
    if not documents or not any(d.content.strip() for d in documents):
        raise IngestionError(f"No readable text found in '{filename}'")

    chunks = await rag.ingest(documents, collection)
    return IngestResponse(
        document_id=filename,
        collection=collection,
        chunks_indexed=chunks,
    )
