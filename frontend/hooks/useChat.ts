"use client";

import { useCallback, useRef, useState } from "react";

import {
  chatStream,
  debugError,
  pairProgram,
  repositoryChatStream,
  searchCode,
  type StreamHandlers,
} from "@/lib/api";
import { humanizeError } from "@/lib/errors";
import type {
  Answer,
  ChatMessage,
  Citation,
  CodeSearchHit,
  ConversationDetail,
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
  onCitations?: (citations: Citation[]) => void;
  onTurnPersisted?: (conversationId: string | null) => void;
}

export function useChat({ onCitations, onTurnPersisted }: UseChatOptions = {}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isBusy, setIsBusy] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const conversationIdRef = useRef<string | null>(null);
  // Replays just the assistant generation of the last turn (for "regenerate").
  const lastGenRef = useRef<(() => Promise<void>) | null>(null);

  const applyConversationId = useCallback((id: string | null) => {
    conversationIdRef.current = id;
    setConversationId(id);
  }, []);

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

  const addAssistantPlaceholder = useCallback((): string => {
    const id = uid();
    setMessages((prev) => [
      ...prev,
      { id, role: "assistant", content: "", citations: [], pending: true },
    ]);
    return id;
  }, []);

  const clear = useCallback(() => {
    setMessages([]);
    lastGenRef.current = null;
    onCitations?.([]);
  }, [onCitations]);

  const newChat = useCallback(() => {
    applyConversationId(null);
    setMessages([]);
    lastGenRef.current = null;
    onCitations?.([]);
  }, [applyConversationId, onCitations]);

  const loadConversation = useCallback(
    (detail: ConversationDetail) => {
      applyConversationId(detail.id);
      lastGenRef.current = null;
      const loaded: ChatMessage[] = detail.messages.map((m) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        citations: m.citations ?? [],
      }));
      setMessages(loaded);
      const lastAssistant = [...loaded]
        .reverse()
        .find((m) => m.role === "assistant");
      onCitations?.(lastAssistant?.citations ?? []);
    },
    [applyConversationId, onCitations],
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsBusy(false);
  }, []);

  // ── Streaming generation (docs + repo) ───────────────────────────
  const runStream = useCallback(
    async (invoke: (handlers: StreamHandlers) => Promise<void>) => {
      const assistantId = addAssistantPlaceholder();
      setIsBusy(true);
      const controller = new AbortController();
      abortRef.current = controller;
      let acc = "";
      await invoke({
        signal: controller.signal,
        onMeta: (meta) => applyConversationId(meta.conversation_id),
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
            content: acc || humanizeError(error),
            error: true,
            pending: false,
          });
        },
      });
      updateMessage(assistantId, { pending: false });
      setIsBusy(false);
      abortRef.current = null;
      onTurnPersisted?.(conversationIdRef.current);
    },
    [addAssistantPlaceholder, applyConversationId, onCitations, onTurnPersisted, updateMessage],
  );

  const generateDocs = useCallback(
    (question: string, collection: string) =>
      runStream((handlers) =>
        chatStream(
          {
            question,
            collection,
            stream: true,
            conversation_id: conversationIdRef.current,
          },
          handlers,
        ),
      ),
    [runStream],
  );

  const generateRepo = useCallback(
    (question: string, repositoryId: string) =>
      runStream((handlers) =>
        repositoryChatStream(
          repositoryId,
          { question, conversation_id: conversationIdRef.current },
          handlers,
        ),
      ),
    [runStream],
  );

  // ── Non-streaming generation (debug + pair) ──────────────────────
  const generateAnswer = useCallback(
    async (run: () => Promise<Answer>) => {
      const assistantId = addAssistantPlaceholder();
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
        if (answer.conversation_id) applyConversationId(answer.conversation_id);
        onTurnPersisted?.(answer.conversation_id ?? conversationIdRef.current);
      } catch (err) {
        updateMessage(assistantId, {
          content: humanizeError(err),
          error: true,
          pending: false,
        });
      } finally {
        setIsBusy(false);
      }
    },
    [addAssistantPlaceholder, applyConversationId, onCitations, onTurnPersisted, updateMessage],
  );

  const generateSearch = useCallback(
    async (query: string, topK: number, repositoryId?: string | null) => {
      const assistantId = addAssistantPlaceholder();
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
        updateMessage(assistantId, {
          content: humanizeError(err),
          error: true,
          pending: false,
        });
      } finally {
        setIsBusy(false);
      }
    },
    [addAssistantPlaceholder, onCitations, updateMessage],
  );

  // ── Public send actions (push the user message, then generate) ───
  const sendDocs = useCallback(
    (question: string, collection: string) => {
      pushUser(question);
      lastGenRef.current = () => generateDocs(question, collection);
      return generateDocs(question, collection);
    },
    [generateDocs, pushUser],
  );

  const sendRepo = useCallback(
    (question: string, repositoryId: string) => {
      pushUser(question);
      lastGenRef.current = () => generateRepo(question, repositoryId);
      return generateRepo(question, repositoryId);
    },
    [generateRepo, pushUser],
  );

  const sendDebug = useCallback(
    (req: DebugRequest) => {
      const summary = `Debug: ${req.error.split("\n")[0].slice(0, 120)}`;
      pushUser(summary);
      lastGenRef.current = () => generateAnswer(() => debugError(req));
      return generateAnswer(() => debugError(req));
    },
    [generateAnswer, pushUser],
  );

  const sendPair = useCallback(
    (req: PairRequest) => {
      const summary = `Pair (${req.action})${
        req.instructions ? `: ${req.instructions}` : ""
      }`;
      pushUser(summary);
      lastGenRef.current = () => generateAnswer(() => pairProgram(req));
      return generateAnswer(() => pairProgram(req));
    },
    [generateAnswer, pushUser],
  );

  const sendSearch = useCallback(
    (query: string, topK: number, repositoryId?: string | null) => {
      pushUser(`Search: ${query}`);
      lastGenRef.current = () => generateSearch(query, topK, repositoryId);
      return generateSearch(query, topK, repositoryId);
    },
    [generateSearch, pushUser],
  );

  // Re-run the last turn's answer, replacing the previous assistant message.
  const regenerate = useCallback(() => {
    const gen = lastGenRef.current;
    if (!gen || isBusy) return;
    setMessages((prev) => {
      const copy = [...prev];
      for (let i = copy.length - 1; i >= 0; i--) {
        if (copy[i].role === "assistant") {
          copy.splice(i, 1);
          break;
        }
      }
      return copy;
    });
    void gen();
  }, [isBusy]);

  const canRegenerate = lastGenRef.current !== null;

  return {
    messages,
    isBusy,
    conversationId,
    canRegenerate,
    clear,
    newChat,
    loadConversation,
    regenerate,
    stop,
    sendDocs,
    sendRepo,
    sendDebug,
    sendPair,
    sendSearch,
  };
}
