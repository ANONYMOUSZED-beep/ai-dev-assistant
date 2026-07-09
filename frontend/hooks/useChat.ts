"use client";

import { useCallback, useRef, useState } from "react";

import {
  ApiError,
  chatStream,
  debugError,
  pairProgram,
  repositoryChat,
  searchCode,
} from "@/lib/api";
import type {
  Answer,
  ChatMessage,
  Citation,
  CodeSearchHit,
  DebugRequest,
  PairRequest,
} from "@/lib/types";

function uid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function hitsToCitations(hits: CodeSearchHit[]): Citation[] {
  return hits.map((hit, i) => ({
    index: i + 1,
    title: hit.symbol ? `${hit.path} · ${hit.symbol}` : hit.path,
    source_type: "code",
    uri: hit.path,
    snippet: hit.snippet,
    start_line: hit.start_line,
    end_line: hit.end_line,
    score: hit.score,
  }));
}

function hitsToMarkdown(query: string, hits: CodeSearchHit[]): string {
  if (hits.length === 0) {
    return `No code matches found for **${query}**.`;
  }
  const lines = [`Found **${hits.length}** match(es) for **${query}**:`, ""];
  hits.forEach((hit, i) => {
    const loc =
      hit.start_line != null
        ? `:${hit.start_line}${hit.end_line != null ? `-${hit.end_line}` : ""}`
        : "";
    const sym = hit.symbol ? ` — \`${hit.symbol}\`` : "";
    lines.push(`${i + 1}. \`${hit.path}${loc}\`${sym} [${i + 1}]`);
  });
  return lines.join("\n");
}

export interface UseChatOptions {
  // Called whenever an assistant message produces citations.
  onCitations?: (citations: Citation[]) => void;
}

export function useChat({ onCitations }: UseChatOptions = {}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isBusy, setIsBusy] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const updateMessage = useCallback(
    (id: string, patch: Partial<ChatMessage>) => {
      setMessages((prev) =>
        prev.map((m) => (m.id === id ? { ...m, ...patch } : m)),
      );
    },
    [],
  );

  const pushUser = useCallback((content: string) => {
    setMessages((prev) => [
      ...prev,
      { id: uid(), role: "user", content, citations: [] },
    ]);
  }, []);

  const clear = useCallback(() => {
    setMessages([]);
    onCitations?.([]);
  }, [onCitations]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsBusy(false);
  }, []);

  // Docs chat with token streaming.
  const sendDocs = useCallback(
    async (question: string, collection: string) => {
      pushUser(question);
      const assistantId = uid();
      setMessages((prev) => [
        ...prev,
        {
          id: assistantId,
          role: "assistant",
          content: "",
          citations: [],
          pending: true,
        },
      ]);
      setIsBusy(true);
      const controller = new AbortController();
      abortRef.current = controller;

      let acc = "";
      await chatStream(
        { question, collection, stream: true },
        {
          signal: controller.signal,
          onCitations: (citations) => {
            updateMessage(assistantId, { citations });
            onCitations?.(citations);
          },
          onToken: (token) => {
            acc += token;
            updateMessage(assistantId, { content: acc });
          },
          onError: (error) => {
            updateMessage(assistantId, {
              content: acc || `Error: ${error.message}`,
              error: true,
              pending: false,
            });
          },
        },
      );
      updateMessage(assistantId, { pending: false });
      setIsBusy(false);
      abortRef.current = null;
    },
    [onCitations, pushUser, updateMessage],
  );

  // Generic non-streaming Answer-producing request.
  const runAnswer = useCallback(
    async (
      userContent: string,
      run: () => Promise<Answer>,
    ) => {
      pushUser(userContent);
      const assistantId = uid();
      setMessages((prev) => [
        ...prev,
        {
          id: assistantId,
          role: "assistant",
          content: "",
          citations: [],
          pending: true,
        },
      ]);
      setIsBusy(true);
      try {
        const answer = await run();
        updateMessage(assistantId, {
          content: answer.text,
          citations: answer.citations,
          model: answer.model,
          provider: answer.provider,
          pending: false,
        });
        onCitations?.(answer.citations);
      } catch (err) {
        const message =
          err instanceof ApiError || err instanceof Error
            ? err.message
            : String(err);
        updateMessage(assistantId, {
          content: `Error: ${message}`,
          error: true,
          pending: false,
        });
      } finally {
        setIsBusy(false);
      }
    },
    [onCitations, pushUser, updateMessage],
  );

  const sendRepo = useCallback(
    (question: string, repositoryId: string) =>
      runAnswer(question, () => repositoryChat(repositoryId, { question })),
    [runAnswer],
  );

  const sendDebug = useCallback(
    (req: DebugRequest) => {
      const summary = `Debug: ${req.error.split("\n")[0].slice(0, 120)}`;
      return runAnswer(summary, () => debugError(req));
    },
    [runAnswer],
  );

  const sendPair = useCallback(
    (req: PairRequest) => {
      const summary = `Pair (${req.action})${
        req.instructions ? `: ${req.instructions}` : ""
      }`;
      return runAnswer(summary, () => pairProgram(req));
    },
    [runAnswer],
  );

  const sendSearch = useCallback(
    async (query: string, topK: number, repositoryId?: string | null) => {
      pushUser(`Search: ${query}`);
      const assistantId = uid();
      setMessages((prev) => [
        ...prev,
        {
          id: assistantId,
          role: "assistant",
          content: "",
          citations: [],
          pending: true,
        },
      ]);
      setIsBusy(true);
      try {
        const res = await searchCode({
          query,
          top_k: topK,
          repository_id: repositoryId ?? null,
        });
        const citations = hitsToCitations(res.hits);
        updateMessage(assistantId, {
          content: hitsToMarkdown(res.query, res.hits),
          citations,
          pending: false,
        });
        onCitations?.(citations);
      } catch (err) {
        const message =
          err instanceof ApiError || err instanceof Error
            ? err.message
            : String(err);
        updateMessage(assistantId, {
          content: `Error: ${message}`,
          error: true,
          pending: false,
        });
      } finally {
        setIsBusy(false);
      }
    },
    [onCitations, pushUser, updateMessage],
  );

  return {
    messages,
    isBusy,
    clear,
    stop,
    sendDocs,
    sendRepo,
    sendDebug,
    sendPair,
    sendSearch,
  };
}
