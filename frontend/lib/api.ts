// Typed API client for the AI Developer Assistant FastAPI backend.

import type {
  Answer,
  ChatRequest,
  CodeSearchRequest,
  CodeSearchResponse,
  Citation,
  DebugRequest,
  IngestRequest,
  IngestResponse,
  PairRequest,
  RepoChatRequest,
  RepositoryCreateRequest,
  RepositoryResponse,
} from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

// Optional client API key. When set, it is sent as X-API-Key on every request so
// the app works against a backend that has authentication enabled.
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";

/** Merge the API-key header (when configured) into a headers object. */
function withApiKey(headers: HeadersInit = {}): HeadersInit {
  return API_KEY ? { ...headers, "X-API-Key": API_KEY } : headers;
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
      headers: withApiKey({
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
export async function chatStream(
  req: ChatRequest,
  handlers: StreamHandlers,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/chat/stream`, {
      method: "POST",
      headers: withApiKey({
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      }),
      body: JSON.stringify(req),
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
      headers: withApiKey(),
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
