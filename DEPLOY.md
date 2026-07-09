# Deploying (Hugging Face Spaces + Vercel)

A simple split deploy: the FastAPI backend runs as a Docker **Hugging Face Space**,
the Next.js frontend runs on **Vercel**.

---

## 1. Backend → Hugging Face Space (Docker)

1. Create a new Space → **SDK: Docker** → Blank.
2. Push the **`backend/`** folder as the Space repo root (its `Dockerfile` and
   `README.md` — with the `app_port: 8000` metadata — must be at the root).
   ```bash
   # from a clone of your Space repo
   cp -r <this-repo>/backend/* .
   git add . && git commit -m "backend" && git push
   ```
3. In the Space → **Settings → Variables and secrets**, add:
   - `LLM_PROVIDER` = `groq` (or openai / anthropic / gemini)
   - `LLM_MODEL` = a model id for that provider
   - `GROQ_API_KEY` (or the matching provider key)
   - `API_KEYS` = `["choose-a-strong-key"]`
   - `BACKEND_CORS_ORIGINS` = `["https://<your-app>.vercel.app"]`
   - *(optional, lighter/faster on free CPU)* `EMBEDDING_MODEL=BAAI/bge-small-en-v1.5`,
     `RERANKER_MODEL=BAAI/bge-reranker-base`
4. Wait for the build (first build is slow — it installs the ML stack). When it's up:
   - API docs: `https://<user>-<space>.hf.space/docs`
   - Health: `https://<user>-<space>.hf.space/api/v1/health`

> No Postgres/Redis needed for the demo. Docs Chat, Code Search, Debug, and Pair
> Programmer work out of the box. The FAISS index is ephemeral on the free tier
> (re-ingest after a restart). Repo Chat needs a hosted `DATABASE_URL` to persist.

---

## 2. Frontend → Vercel

1. Import the GitHub repo in Vercel.
2. **Project Settings → Root Directory → `frontend`**.
3. **Environment Variables** (Production + Preview):
   - `NEXT_PUBLIC_API_BASE_URL` = `https://<user>-<space>.hf.space/api/v1`
   - `NEXT_PUBLIC_API_KEY` = the same value you put inside `API_KEYS`
4. Deploy. Vercel runs `next build` automatically.

> `NEXT_PUBLIC_*` values are inlined at build time — set them **before** deploying.
> If you change them later, trigger a redeploy.

---

## 3. Connect the two

- Make sure `BACKEND_CORS_ORIGINS` on the Space includes your exact Vercel URL
  (production domain, and any custom domain you add).
- The frontend sends `X-API-Key`; it must match one entry in the Space's `API_KEYS`.

---

## Quick verification

```bash
# backend up?
curl https://<user>-<space>.hf.space/api/v1/health

# auth working? (should be 401 without the key, 200 with it)
curl -X POST https://<user>-<space>.hf.space/api/v1/chat \
  -H "Content-Type: application/json" -H "X-API-Key: <your-key>" \
  -d '{"question":"How does FastAPI dependency injection work?"}'
```

Then open your Vercel URL and try Docs Chat.
