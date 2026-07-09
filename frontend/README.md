# AI Developer Assistant — Frontend

A Cursor / VS Code–style dark IDE built with **Next.js 14 (App Router)**,
**TypeScript**, **Tailwind CSS**, and the **Monaco Editor**. It is the frontend
for the AI Developer Assistant FastAPI backend and provides documentation chat,
repository Q&A, semantic code search, error debugging, and an AI pair
programmer — all with grounded citations rendered against their source.

## Features

- **Three-pane IDE layout**
  - **Left** — Repository explorer (connect a repo by URL, live index status,
    file tree populated from search results) and a documentation collection
    selector (Python, FastAPI, React, Next.js, Django, Flask, TensorFlow,
    PyTorch, LangChain, LlamaIndex, Docker, Kubernetes, AWS).
  - **Center** — Chat panel with mode tabs (Docs Chat, Repo Chat, Code Search,
    Debug, Pair Programmer), streaming Markdown answers with syntax-highlighted
    code blocks and inline citation chips `[1] [2]`.
  - **Right** — Read-only Monaco source viewer with line highlighting, plus a
    scrollable citations list. Clicking a citation chip opens its source and
    scrolls the list to it.
- **Token streaming** for documentation chat via `POST /chat/stream` (SSE parsed
  from a `fetch` + `ReadableStream`).
- **Typed API client** covering every backend endpoint.
- Fully keyboard accessible with ARIA roles/labels and a cohesive dark theme.

## Getting started

```bash
npm install
cp .env.local.example .env.local   # adjust NEXT_PUBLIC_API_BASE_URL if needed
npm run dev
```

Open http://localhost:3000.

## Configuration

| Variable                   | Default                          | Description                  |
| -------------------------- | -------------------------------- | ---------------------------- |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000/api/v1`   | Base URL of the FastAPI API. |

## Scripts

| Command         | Description                       |
| --------------- | --------------------------------- |
| `npm run dev`   | Start the dev server.             |
| `npm run build` | Production build.                 |
| `npm run start` | Serve the production build.       |
| `npm run lint`  | Run ESLint (Next.js core rules).  |

## Docker

```bash
docker build -t ai-dev-assistant-frontend .
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 \
  ai-dev-assistant-frontend
```

## Project structure

```
app/            # App Router entry (layout, globals, main page)
components/     # UI components (chat, explorer, viewer, panels)
hooks/          # useChat — chat/streaming state machine
lib/            # api client, types, helpers (collections, language)
```
