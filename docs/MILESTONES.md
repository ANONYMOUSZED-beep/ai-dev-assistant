# Milestones

The project is delivered module-by-module. Each module is complete, typed, and tested
before the next begins.

| # | Milestone | Deliverable |
|---|-----------|-------------|
| M0 | Architecture & scaffold | Folder structure, docs, root config, docker-compose, CI. |
| M1 | Backend core | Settings, logging, FastAPI app, async Postgres + Redis, DI, lifespan, health. |
| M2 | RAG pipeline | Loaders (PDF/MD/HTML/DOCX/TXT/code/github/web), chunking, BGE-M3 embeddings, FAISS/Chroma store, hybrid retrieval + reranking, citations. |
| M3 | LLM abstraction | Provider interface + Claude/GPT/Gemini/DeepSeek/Qwen + prompt templates. |
| M4 | Services & API | Documentation chat, repo indexing/chat, semantic code search, error debugging, pair programmer. |
| M5 | Frontend | Next.js + Tailwind + Monaco UI: chat, citations, doc viewer, code viewer, repo explorer. |
| M6 | Quality & infra | pytest suite, Docker images, GitHub Actions CI, docs polish. |

## Definition of Done (per module)
- Type hints throughout, no placeholder code or `TODO` comments.
- Unit tests where logic is non-trivial; engines mockable.
- Importable without side effects; configuration validated.
- Lint (ruff) and type-check (mypy) clean.
