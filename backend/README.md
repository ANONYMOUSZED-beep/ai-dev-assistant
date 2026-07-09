---
title: AI Developer Assistant API
emoji: 🤖
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# AI Developer Assistant — Backend (FastAPI + RAG)

This Space runs the FastAPI backend as a Docker container. Interactive API docs
are available at `/docs`; health at `/api/v1/health`.

## Required Space secrets (Settings → Variables and secrets)

| Key | Notes |
|-----|-------|
| `LLM_PROVIDER` | e.g. `groq`, `openai`, `anthropic`, `gemini` |
| `LLM_MODEL` | model id for the chosen provider |
| `GROQ_API_KEY` / `OPENAI_API_KEY` / … | key for the chosen provider |
| `API_KEYS` | JSON list, e.g. `["your-secret-key"]` — enables auth |
| `BACKEND_CORS_ORIGINS` | JSON list including your Vercel URL, e.g. `["https://your-app.vercel.app"]` |

## Optional (lighter models for the free CPU tier)

The defaults (`BAAI/bge-m3` + `bge-reranker-v2-m3`) are large. For a snappier
free-tier demo you can set smaller models:

```
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
RERANKER_MODEL=BAAI/bge-reranker-base
```

## Notes

- **No database/Redis required for the demo.** Docs Chat, Code Search, Debug, and
  Pair Programmer work with the local FAISS index + your LLM. Rate limiting degrades
  open without Redis; the repository registry returns empty without Postgres.
- **Storage is ephemeral** on the free tier — the FAISS index resets when the Space
  restarts, so re-ingest documents after a restart (or attach persistent storage).
- To enable **Repo Chat** persistently, add a hosted Postgres (`DATABASE_URL`) and
  Redis (`REDIS_HOST`/`REDIS_PORT`).
