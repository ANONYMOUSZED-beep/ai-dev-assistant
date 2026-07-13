// Typed API client for the AI Developer Assistant FastAPI backend.

import type {
  Answer,
  ChatRequest,
  CodeSearchRequest,
  CodeSearchResponse,
  Citation,
  ConversationDetail,
  ConversationKind,
  ConversationSummary,
  DebugRequest,
  IngestRequest,
  IngestResponse,
  PairRequest,
  RepoChatRequest,
  RepositoryCreateRequest,
  RepositoryResponse,
} from "./types";

// Backend base URL.
// - Local dev sets NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 in
//   frontend/.env.local (which is git-ignored, so it never ships to Vercel).
// - On Vercel, .env.local is absent, so we fall back to the deployed Hugging Face
//   Space rather than localhost — otherwise the browser would try to reach a
//   backend on the visitor's own machine. You can still override this per
//   environment by setting NEXT_PUBLIC_API_BASE_URL in the Vercel dashboard.
const PRODUCTION_API_BASE_URL =
  "https://arun103-ai-dev-assistant-api.hf.space/api/v1";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? PRODUCTION_API_BASE_URL;

const TOKEN_KEY = "rivr_token";

/** JWT access token, persisted in localStorage after login/register. */
export function getToken(): string {
  if (typeof window === "undefined") return "";
  try {
    return window.localStorage.getItem(TOKEN_KEY) ?? "";
  } catch {
    return "";
  }
}

export function setToken(token: string): void {
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* ignore */
  }
}

export function clearToken(): void {
  try {
    window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
}

/** Merge the Authorization bearer header (when logged in) into a headers object. */
function withHeaders(headers: HeadersInit = {}): HeadersInit {
  const merged: Record<string, string> = { ...(headers as Record<string, string>) };
  const token = getToken();
  if (token) merged["Authorization"] = `Bearer ${token}`;
  return merged;
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: withHeaders({
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      }),
    });
  } catch (err) {
    throw new ApiError(
      0,
      `Network error contacting backend at ${API_BASE_URL}: ${
        err instanceof Error ? err.message : String(err)
      }`,
    );
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (body.detail) {
        detail = JSON.stringify(body.detail);
      }
    } catch {
      // body was not JSON; keep statusText.
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

function jsonBody(data: unknown): RequestInit {
  return { method: "POST", body: JSON.stringify(data) };
}

// ── Chat ──────────────────────────────────────────────────────────
export function chat(req: ChatRequest): Promise<Answer> {
  return request<Answer>("/chat", jsonBody({ stream: false, ...req }));
}

export interface StreamHandlers {
  onMeta?: (meta: { conversation_id: string }) => void;
  onCitations?: (citations: Citation[]) => void;
  onToken?: (token: string) => void;
  onDone?: () => void;
  onError?: (error: Error) => void;
  signal?: AbortSignal;
}

/**
 * Stream a documentation answer from POST /chat/stream.
 *
 * Parses the SSE response body manually via fetch + ReadableStream so it works
 * with POST requests (the native EventSource only supports GET).
 */
export function chatStream(
  req: ChatRequest,
  handlers: StreamHandlers,
): Promise<void> {
  return streamSSE("/chat/stream", req, handlers);
}

/** Stream a repository answer from POST /repositories/{id}/chat/stream. */
export function repositoryChatStream(
  id: string,
  req: RepoChatRequest,
  handlers: StreamHandlers,
): Promise<void> {
  return streamSSE(
    `/repositories/${encodeURIComponent(id)}/chat/stream`,
    req,
    handlers,
  );
}

async function streamSSE(
  path: string,
  body: unknown,
  handlers: StreamHandlers,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: withHeaders({
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      }),
      body: JSON.stringify(body),
      signal: handlers.signal,
    });
  } catch (err) {
    if ((err as Error)?.name === "AbortError") return;
    handlers.onError?.(
      new ApiError(
        0,
        `Network error contacting backend at ${API_BASE_URL}: ${
          err instanceof Error ? err.message : String(err)
        }`,
      ),
    );
    return;
  }

  if (!res.ok || !res.body) {
    handlers.onError?.(new ApiError(res.status, res.statusText || "Stream failed"));
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const dispatch = (rawEvent: string) => {
    let eventName = "message";
    const dataLines: string[] = [];
    for (const line of rawEvent.split("\n")) {
      if (line.startsWith(":")) continue; // comment / keep-alive
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        // Preserve exact content after "data:" (strip a single leading space).
        dataLines.push(line.slice(5).replace(/^ /, ""));
      }
    }
    const data = dataLines.join("\n");

    switch (eventName) {
      case "meta": {
        try {
          const parsed = JSON.parse(data) as { conversation_id: string };
          handlers.onMeta?.(parsed);
        } catch {
          // Ignore malformed meta payloads.
        }
        break;
      }
      case "citations": {
        try {
          const parsed = JSON.parse(data) as Citation[];
          handlers.onCitations?.(parsed);
        } catch {
          // Ignore malformed citation payloads.
        }
        break;
      }
      case "token":
        handlers.onToken?.(data);
        break;
      case "done":
        handlers.onDone?.();
        break;
      default:
        break;
    }
  };

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      // Normalise CRLF -> LF: SSE servers (e.g. sse-starlette) terminate
      // lines with "\r\n", so events are separated by "\r\n\r\n". Without
      // this, the "\n\n" boundary below never matches and no events fire.
      buffer = (buffer + decoder.decode(value, { stream: true })).replace(
        /\r\n/g,
        "\n",
      );

      let sepIndex: number;
      // SSE events are separated by a blank line.
      while ((sepIndex = buffer.indexOf("\n\n")) !== -1) {
        const rawEvent = buffer.slice(0, sepIndex);
        buffer = buffer.slice(sepIndex + 2);
        if (rawEvent.trim().length > 0) dispatch(rawEvent);
      }
    }
    if (buffer.trim().length > 0) dispatch(buffer);
    handlers.onDone?.();
  } catch (err) {
    if ((err as Error)?.name === "AbortError") return;
    handlers.onError?.(err instanceof Error ? err : new Error(String(err)));
  }
}

// ── Documents ─────────────────────────────────────────────────────
export function ingestDocument(req: IngestRequest): Promise<IngestResponse> {
  return request<IngestResponse>("/documents/ingest", jsonBody(req));
}

export async function uploadDocument(
  collection: string,
  file: File,
  title?: string,
): Promise<IngestResponse> {
  const form = new FormData();
  form.append("collection", collection);
  form.append("file", file);
  if (title) form.append("title", title);

  let res: Response;
  try {
    // Note: no Content-Type header — the browser sets the multipart boundary.
    res = await fetch(`${API_BASE_URL}/documents/upload`, {
      method: "POST",
      headers: withHeaders(),
      body: form,
    });
  } catch (err) {
    throw new ApiError(
      0,
      `Network error contacting backend at ${API_BASE_URL}: ${
        err instanceof Error ? err.message : String(err)
      }`,
    );
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as {
        detail?: unknown;
        error?: { message?: string };
      };
      if (body.error?.message) detail = body.error.message;
      else if (typeof body.detail === "string") detail = body.detail;
      else if (body.detail) detail = JSON.stringify(body.detail);
    } catch {
      // keep statusText
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as IngestResponse;
}

// ── Repositories ──────────────────────────────────────────────────
export function createRepository(
  req: RepositoryCreateRequest,
): Promise<RepositoryResponse> {
  return request<RepositoryResponse>("/repositories", jsonBody(req));
}

export function listRepositories(): Promise<RepositoryResponse[]> {
  return request<RepositoryResponse[]>("/repositories", { method: "GET" });
}

export function getRepository(id: string): Promise<RepositoryResponse> {
  return request<RepositoryResponse>(`/repositories/${encodeURIComponent(id)}`, {
    method: "GET",
  });
}

export function repositoryChat(
  id: string,
  req: RepoChatRequest,
): Promise<Answer> {
  return request<Answer>(
    `/repositories/${encodeURIComponent(id)}/chat`,
    jsonBody(req),
  );
}

export function deleteRepository(id: string): Promise<void> {
  return request<void>(`/repositories/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

// ── Code search ───────────────────────────────────────────────────
export function searchCode(
  req: CodeSearchRequest,
): Promise<CodeSearchResponse> {
  return request<CodeSearchResponse>("/search/code", jsonBody(req));
}

// ── Debug ─────────────────────────────────────────────────────────
export function debugError(req: DebugRequest): Promise<Answer> {
  return request<Answer>("/debug", jsonBody(req));
}

// ── Pair programmer ───────────────────────────────────────────────
export function pairProgram(req: PairRequest): Promise<Answer> {
  return request<Answer>("/pair", jsonBody(req));
}

// ── Conversations (chat history) ──────────────────────────────────
export function listConversations(
  kind?: ConversationKind,
): Promise<ConversationSummary[]> {
  const query = kind ? `?kind=${encodeURIComponent(kind)}` : "";
  return request<ConversationSummary[]>(`/conversations${query}`, {
    method: "GET",
  });
}

export function getConversation(id: string): Promise<ConversationDetail> {
  return request<ConversationDetail>(
    `/conversations/${encodeURIComponent(id)}`,
    { method: "GET" },
  );
}

export function renameConversation(
  id: string,
  title: string,
): Promise<ConversationSummary> {
  return request<ConversationSummary>(
    `/conversations/${encodeURIComponent(id)}`,
    { method: "PATCH", body: JSON.stringify({ title }) },
  );
}

export function deleteConversation(id: string): Promise<void> {
  return request<void>(`/conversations/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

// ── Auth ──────────────────────────────────────────────────────────
export interface AuthToken {
  access_token: string;
  token_type: string;
  username: string;
}

export interface CurrentUser {
  id: string;
  username: string;
}

export function register(username: string, password: string): Promise<AuthToken> {
  return request<AuthToken>("/auth/register", jsonBody({ username, password }));
}

export function login(username: string, password: string): Promise<AuthToken> {
  return request<AuthToken>("/auth/login", jsonBody({ username, password }));
}

// Google OAuth Web client id (set NEXT_PUBLIC_GOOGLE_CLIENT_ID to enable the button).
export const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? "";

/** Exchange a Google Identity Services ID token for our own access token. */
export function googleLogin(credential: string): Promise<AuthToken> {
  return request<AuthToken>("/auth/google", jsonBody({ credential }));
}

export function fetchMe(): Promise<CurrentUser> {
  return request<CurrentUser>("/auth/me", { method: "GET" });
}

/** Fetch a full export of the current user's data (account, repos, chats). */
export function exportMyData(): Promise<unknown> {
  return request<unknown>("/auth/me/export", { method: "GET" });
}

/** Permanently delete the current user's account and all their data. */
export function deleteAccount(): Promise<{ deleted: string }> {
  return request<{ deleted: string }>("/auth/me", { method: "DELETE" });
}
