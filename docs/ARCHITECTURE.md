# Architecture

## 1. Goals & Principles

- **Grounded, cited answers** — every LLM response is backed by retrieved context with
  source attribution to minimise hallucination.
- **Modular & swappable** — embedding model, vector store, and LLM provider are all behind
  interfaces and selected via configuration.
- **Async-first** — the API, DB, and cache layers are fully async to handle concurrent
  retrieval + generation efficiently.
- **Production-ready** — typed, dependency-injected, containerised, tested, and CI-gated.

## 2. High-Level Diagram

```
┌──────────────┐      HTTP/JSON + SSE      ┌──────────────────────────────────────────┐
│   Frontend   │ ────────────────────────► │                Backend (FastAPI)          │
│  Next.js UI  │ ◄──────────────────────── │                                            │
│ Monaco/Tailwind                          │   api/v1  ──►  services  ──►  engines       │
└──────────────┘                           │     │             │            │           │
                                           │  chat,docs,     orchestration  RAG  +  LLM  │
                                           │  repos,search,        │         │      │     │
                                           │  debug,pair           ▼         ▼      ▼     │
                                           │                 ┌──────────┐ ┌──────┐ ┌────┐ │
                                           │                 │ Postgres │ │FAISS/│ │LLM │ │
                                           │                 │  Redis   │ │Chroma│ │APIs│ │
                                           │                 └──────────┘ └──────┘ └────┘ │
                                           └──────────────────────────────────────────────┘
```

## 3. Backend Layers

| Layer | Package | Responsibility |
|-------|---------|----------------|
| API | `app/api/v1` | HTTP routing, request/response schemas, SSE streaming. No business logic. |
| Services | `app/services` | Orchestrate RAG + LLM + persistence for each feature. |
| RAG engine | `app/rag` | Ingestion, chunking, embeddings, vector store, hybrid retrieval, reranking, citations. |
| LLM engine | `app/llm` | Provider abstraction + prompt templates + context-aware prompting. |
| Persistence | `app/db`, `app/cache` | Async SQLAlchemy (Postgres) + Redis cache/session store. |
| Core | `app/core` | Settings, logging, DI providers, exceptions. |

### Dependency Injection
FastAPI's `Depends` wires singletons (settings, DB session, Redis, RAG pipeline, LLM
provider) into routes and services. Engines are constructed once at startup
(`app/core/lifespan.py`) and shared.

## 4. RAG Pipeline

```
ingest → load → chunk → embed → index ──┐
                                         ▼
query → embed → hybrid retrieve (dense + BM25) → rerank (cross-encoder) → build context
      → prompt (context-aware template) → LLM generate → answer + citations
```

- **Loaders** (`rag/ingestion`): PDF, Markdown, HTML, DOCX, TXT, code files, GitHub repos,
  documentation websites. Each yields normalised `Document` objects with metadata.
- **Chunking** (`rag/chunking`): structure-aware splitting — recursive for prose,
  language-aware (function/class boundaries) for code.
- **Embeddings** (`rag/embeddings`): BGE-M3 via sentence-transformers, batched, cached.
- **Vector store** (`rag/vectorstore`): `VectorStore` interface with FAISS and Chroma
  backends; per-collection isolation (docs vs. each repo).
- **Retrieval** (`rag/retrieval`): hybrid dense + sparse (BM25) with score fusion, then
  cross-encoder reranking. Returns scored `RetrievedChunk`s.
- **Citations** (`rag/citation`): maps retrieved chunks to human-readable sources
  (title, url/path, line range) attached to every answer.

## 5. LLM Abstraction

`BaseLLMProvider` defines `generate()` and `stream()`. Concrete providers: Claude,
GPT (OpenAI), Gemini, DeepSeek, Qwen. A `ProviderFactory` selects the provider from
settings. Prompt templates live in `llm/prompts` per feature (docs QA, repo QA, code
search, debugging, pair-programming) and inject retrieved context + citation instructions.

## 6. Data Model (Postgres)

- `documents` — ingested source documents (collection, source type, uri, metadata).
- `chunks` — chunk text + metadata + vector reference.
- `repositories` — connected GitHub repos and index status.
- `conversations` / `messages` — chat history with attached citations.

Redis stores embedding/query caches and ingestion job status.

## 7. API Surface (`/api/v1`)

| Endpoint | Purpose |
|----------|---------|
| `POST /chat` | Documentation chat (RAG over doc collections), SSE streaming. |
| `POST /documents/ingest` | Ingest a document/url into a collection. |
| `POST /repositories` | Connect & index a GitHub repository. |
| `GET  /repositories/{id}` | Index status + repo tree. |
| `POST /repositories/{id}/chat` | Chat over a specific repo. |
| `POST /search/code` | Semantic code search. |
| `POST /debug` | Stack-trace / error analysis. |
| `POST /pair` | Pair-programmer actions (explain/refactor/test/docs/optimize/security). |
| `GET  /health` | Liveness/readiness. |

## 8. Frontend

Cursor/VS-Code-style three-pane layout:
- **Left**: Repository explorer + document collections.
- **Center**: Chat panel (streamed answers) with inline citations + Monaco code blocks.
- **Right**: Retrieved-document / code viewer (Monaco read-only with line highlights).

## 9. Cross-Cutting

- **Config**: pydantic-settings, env-driven, validated at startup.
- **Logging**: structured JSON logs with request IDs.
- **Errors**: typed exceptions mapped to consistent HTTP error responses.
- **Testing**: pytest + httpx async client; engines mockable via DI overrides.
- **CI**: GitHub Actions — lint (ruff), type-check (mypy), backend tests, frontend build.
