# AI Developer Assistant (RAG + LLM)

A production-ready, full-stack AI Developer Assistant that helps developers understand
documentation, APIs, and codebases using Retrieval-Augmented Generation (RAG).

It can answer programming questions from official documentation, index and chat with
entire GitHub repositories, perform semantic code search, debug stack traces, and act as
an AI pair programmer — always citing its sources to reduce hallucinations.

## Features

- **Documentation Chat** — Grounded answers over Python, FastAPI, React, Next.js, Django,
  Flask, TensorFlow, PyTorch, LangChain, LlamaIndex, Docker, Kubernetes, and AWS docs.
- **GitHub Repository Chat** — Connect a repo; the assistant indexes it, explains
  architecture, files, classes and functions, and suggests improvements.
- **Semantic Code Search** — Natural-language queries like *"Where is JWT auth implemented?"*.
- **Error Debugging** — Paste a stack trace; get root-cause analysis and corrected code.
- **AI Pair Programmer** — Explain, refactor, generate tests/docs, optimize, security review.

Every answer includes **source citations** pointing back to the original document or file.

## Tech Stack

| Layer    | Technology |
|----------|------------|
| Frontend | Next.js (App Router), TypeScript, Tailwind CSS, Monaco Editor |
| Backend  | FastAPI (async), Pydantic v2, Uvicorn |
| Data     | PostgreSQL (async SQLAlchemy), Redis |
| AI       | LangChain, FAISS / ChromaDB, Sentence-Transformers (BGE-M3), cross-encoder reranker |
| LLM      | Pluggable: Claude, GPT, Gemini, DeepSeek, Qwen |
| Infra    | Docker, docker-compose, pytest, GitHub Actions |

## Repository Layout

```
ai-dev-assistant/
├── backend/        # FastAPI service + RAG/LLM engines
├── frontend/       # Next.js developer UI (Cursor/VS Code style)
├── infra/          # Dockerfiles, docker-compose, deploy assets
├── docs/           # Architecture & milestones
└── docker-compose.yml
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design and
[`docs/MILESTONES.md`](docs/MILESTONES.md) for the delivery plan.

## Quick Start

### 1. Configure environment

```bash
cp .env.example .env
# edit .env and add at least one LLM API key (e.g. OPENAI_API_KEY or ANTHROPIC_API_KEY)
```

### 2. Run with Docker (recommended)

```bash
docker compose up --build
```

- API:      http://localhost:8000  (docs at `/docs`)
- Frontend: http://localhost:3000

### 3. Run locally (dev)

Backend:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Security

The API is protected by two layers, both configured via environment variables:

- **API-key authentication** — set `API_KEYS` (a JSON list) to require an
  `X-API-Key` header on every data endpoint. When it's empty, authentication is
  disabled for frictionless local development; in production the app logs a
  warning if no keys are set. The `/health` probe is always public.
- **Rate limiting** — `RATE_LIMIT_PER_MINUTE` (default `60`) applies a per-client
  fixed-window limit backed by Redis, keyed by API key or client IP. If Redis is
  unavailable the limiter degrades open, so a cache outage never takes the API down.

The frontend forwards `NEXT_PUBLIC_API_KEY` as the `X-API-Key` header when set.

CORS is restricted to the origins in `BACKEND_CORS_ORIGINS` with a scoped set of
methods and headers.

## Observability

- **Request IDs & timing** — every response carries `X-Request-ID` (honoring an
  inbound one for cross-service tracing) and `X-Response-Time-ms`, and each request
  emits a single structured JSON log line (method, path, status, duration).
- **Liveness vs readiness** — `GET /api/v1/health` is a liveness probe (always 200);
  `GET /api/v1/health/ready` verifies Redis and the database and returns 503 when a
  dependency is down, so orchestrators (Kubernetes, ECS) route traffic correctly.

## Testing & quality

Backend:

```bash
cd backend
ruff check app tests   # lint
mypy app               # type-check
pytest                 # unit + integration tests
```

Tests include a real end-to-end RAG integration suite (`tests/test_rag_integration.py`)
that exercises the actual chunker, FAISS vector store, hybrid dense+BM25 retrieval, and
citation building — with only a deterministic embedder and reranker substituted so it
runs fast and offline.

Frontend:

```bash
cd frontend
npm run lint
npm test               # Vitest unit tests
npm run build
```

Everything runs in CI (`.github/workflows/ci.yml`): backend lint + type-check + tests,
frontend lint + tests + build.

## Deployment

1. Provision PostgreSQL and Redis, and set `DATABASE_URL` / `REDIS_HOST` accordingly.
2. Set `ENVIRONMENT=production` and at least one `API_KEYS` value (auth is enforced only
   when keys are present; the app logs a warning if it boots in production without them).
3. Configure `BACKEND_CORS_ORIGINS` to your frontend origin(s) and set at least one LLM
   API key for the chosen `LLM_PROVIDER`.
4. Build and run with Docker: `docker compose up --build`, or deploy the `backend/` and
   `frontend/` images independently. Point the frontend at the API via
   `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_API_KEY`.
5. Wire container health checks to `/api/v1/health` (liveness) and
   `/api/v1/health/ready` (readiness).

## License

MIT
