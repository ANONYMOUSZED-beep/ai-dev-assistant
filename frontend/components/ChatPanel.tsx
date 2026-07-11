"use client";

import {
  Bug,
  CornerDownLeft,
  FileText,
  GitBranch,
  Loader2,
  type LucideIcon,
  Search,
  Sparkles,
  Square,
  Trash2,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { DOC_COLLECTIONS } from "@/lib/collections";
import type {
  ChatMessage,
  ChatMode,
  Citation,
  DebugRequest,
  PairRequest,
  RepositoryResponse,
} from "@/lib/types";
import DebugPanel from "./DebugPanel";
import MessageBubble from "./MessageBubble";
import PairPanel from "./PairPanel";

interface ChatPanelProps {
  mode: ChatMode;
  messages: ChatMessage[];
  isBusy: boolean;
  collection: string;
  repositories: RepositoryResponse[];
  selectedRepoId: string | null;
  onSelectCitation: (citation: Citation) => void;
  onStop: () => void;
  onClear: () => void;
  onSendDocs: (question: string, collection: string) => void;
  onSendRepo: (question: string, repositoryId: string) => void;
  onSendSearch: (
    query: string,
    topK: number,
    repositoryId: string | null,
  ) => void;
  onSendDebug: (req: DebugRequest) => void;
  onSendPair: (req: PairRequest) => void;
}

const MODE_HINTS: Record<ChatMode, string> = {
  docs: "Ask a question about the selected documentation collection.",
  repo: "Ask a question about the selected repository.",
  search: "Search code semantically across an indexed repository.",
  debug: "Paste an error or stack trace to get a diagnosis.",
  pair: "Select an action and paste code to pair-program.",
};

const MODE_ICON: Record<ChatMode, LucideIcon> = {
  docs: FileText,
  repo: GitBranch,
  search: Search,
  debug: Bug,
  pair: Sparkles,
};

const MODE_TITLE: Record<ChatMode, string> = {
  docs: "Chat with documentation",
  repo: "Chat with a repository",
  search: "Search code semantically",
  debug: "Debug an error",
  pair: "Pair-program with AI",
};

const SUGGESTIONS: Record<ChatMode, string[]> = {
  docs: [
    "How does dependency injection work?",
    "Explain async request handling",
    "Show a minimal working example",
  ],
  repo: [
    "Summarize this repository's architecture",
    "Where is authentication handled?",
    "Explain the main entry point",
  ],
  search: [
    "where is JWT auth implemented",
    "database connection setup",
    "error handling middleware",
  ],
  debug: [],
  pair: [],
};

function QuestionComposer({
  busy,
  disabled,
  placeholder,
  onSend,
}: {
  busy: boolean;
  disabled?: boolean;
  placeholder: string;
  onSend: (value: string) => void;
}) {
  const [value, setValue] = useState("");

  const send = () => {
    const trimmed = value.trim();
    if (!trimmed || busy || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  return (
    <div className="flex items-end gap-2 p-3">
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            send();
          }
        }}
        rows={1}
        disabled={disabled}
        placeholder={placeholder}
        aria-label={placeholder}
        className="max-h-40 min-h-[2.5rem] flex-1 resize-none rounded-md border border-ide-border bg-ide-bg px-3 py-2 text-sm text-ide-text placeholder:text-ide-muted focus:border-ide-accent focus:outline-none disabled:opacity-50"
      />
      <button
        type="button"
        onClick={send}
        disabled={busy || disabled || value.trim().length === 0}
        aria-label="Send message"
        className="flex h-10 items-center gap-1.5 rounded-md bg-ide-accentMuted px-3 text-xs font-medium text-white transition-colors hover:bg-ide-accent disabled:cursor-not-allowed disabled:opacity-50"
      >
        {busy ? (
          <Loader2 size={15} className="animate-spin" />
        ) : (
          <CornerDownLeft size={15} />
        )}
        Send
      </button>
    </div>
  );
}

function SearchComposer({
  busy,
  repoOnly,
  hasRepo,
  onToggleRepoOnly,
  onSend,
}: {
  busy: boolean;
  repoOnly: boolean;
  hasRepo: boolean;
  onToggleRepoOnly: (value: boolean) => void;
  onSend: (query: string, topK: number) => void;
}) {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(10);

  const send = () => {
    const trimmed = query.trim();
    if (!trimmed || busy) return;
    onSend(trimmed, topK);
    setQuery("");
  };

  return (
    <div className="space-y-2 p-3">
      <div className="flex items-end gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              send();
            }
          }}
          placeholder="Search code, e.g. 'jwt token validation'"
          aria-label="Code search query"
          className="h-10 flex-1 rounded-md border border-ide-border bg-ide-bg px-3 text-sm text-ide-text placeholder:text-ide-muted focus:border-ide-accent focus:outline-none"
        />
        <div className="w-20">
          <label htmlFor="search-topk" className="sr-only">
            Number of results
          </label>
          <input
            id="search-topk"
            type="number"
            min={1}
            max={50}
            value={topK}
            onChange={(e) =>
              setTopK(Math.min(50, Math.max(1, Number(e.target.value) || 1)))
            }
            className="h-10 w-full rounded-md border border-ide-border bg-ide-bg px-2 text-sm text-ide-text focus:border-ide-accent focus:outline-none"
          />
        </div>
        <button
          type="button"
          onClick={send}
          disabled={busy || query.trim().length === 0}
          aria-label="Search code"
          className="flex h-10 items-center gap-1.5 rounded-md bg-ide-accentMuted px-3 text-xs font-medium text-white transition-colors hover:bg-ide-accent disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? (
            <Loader2 size={15} className="animate-spin" />
          ) : (
            <Search size={15} />
          )}
          Search
        </button>
      </div>
      <label className="flex items-center gap-1.5 text-[0.7rem] text-ide-muted">
        <input
          type="checkbox"
          checked={repoOnly}
          disabled={!hasRepo}
          onChange={(e) => onToggleRepoOnly(e.target.checked)}
          className="accent-ide-accent"
        />
        Limit to selected repository {hasRepo ? "" : "(none selected)"}
      </label>
    </div>
  );
}

export default function ChatPanel({
  mode,
  messages,
  isBusy,
  collection,
  repositories,
  selectedRepoId,
  onSelectCitation,
  onStop,
  onClear,
  onSendDocs,
  onSendRepo,
  onSendSearch,
  onSendDebug,
  onSendPair,
}: ChatPanelProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [repoOnlySearch, setRepoOnlySearch] = useState(true);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  const selectedRepo =
    repositories.find((r) => r.id === selectedRepoId) ?? null;
  const repoReady = selectedRepo?.status === "ready";
  const collectionLabel =
    DOC_COLLECTIONS.find((c) => c.id === collection)?.label ?? collection;

  const EmptyIcon = MODE_ICON[mode];
  const suggestions = SUGGESTIONS[mode];
  const canSuggest =
    mode === "docs" ||
    mode === "search" ||
    (mode === "repo" && repoReady && Boolean(selectedRepoId));

  const runSuggestion = (text: string) => {
    if (mode === "docs") onSendDocs(text, collection);
    else if (mode === "repo" && selectedRepoId) onSendRepo(text, selectedRepoId);
    else if (mode === "search")
      onSendSearch(text, 10, repoOnlySearch ? selectedRepoId : null);
  };

  return (
    <section
      className="flex h-full min-w-0 flex-1 flex-col bg-ide-bg"
      aria-label="Conversation"
    >
      <div className="flex items-center justify-between border-b border-ide-border bg-ide-panel/40 px-4 py-2 text-[0.7rem] text-ide-muted">
        <span className="truncate">{MODE_HINTS[mode]}</span>
        <div className="flex items-center gap-2">
          {isBusy && mode === "docs" ? (
            <button
              type="button"
              onClick={onStop}
              className="flex items-center gap-1 rounded px-1.5 py-0.5 text-ide-danger hover:bg-ide-hover"
            >
              <Square size={11} /> Stop
            </button>
          ) : null}
          <button
            type="button"
            onClick={onClear}
            disabled={messages.length === 0}
            className="flex items-center gap-1 rounded px-1.5 py-0.5 hover:bg-ide-hover hover:text-ide-text disabled:opacity-40"
          >
            <Trash2 size={11} /> Clear
          </button>
        </div>
      </div>

      <div
        id="chat-panel-body"
        ref={scrollRef}
        role="list"
        aria-label="Messages"
        className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4"
      >
        {messages.length === 0 ? (
          <div className="msg-in flex h-full flex-col items-center justify-center gap-5 px-6 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-ide-border bg-ide-elevated text-ide-accent shadow-[0_8px_24px_rgba(30,50,90,0.08)]">
              <EmptyIcon size={28} />
            </div>
            <div className="space-y-1.5">
              <h2 className="font-display text-xl font-semibold text-ide-text">
                {MODE_TITLE[mode]}
              </h2>
              <p className="mx-auto max-w-sm text-sm text-ide-muted">
                {MODE_HINTS[mode]}
              </p>
            </div>
            {canSuggest && suggestions.length > 0 ? (
              <div className="flex max-w-md flex-wrap justify-center gap-2 pt-1">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => runSuggestion(s)}
                    disabled={isBusy}
                    className="suggestion-chip rounded-full border border-ide-border bg-ide-panel px-3.5 py-1.5 text-xs text-ide-text hover:border-ide-accent/50 hover:bg-ide-accent/5 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {s}
                  </button>
                ))}
              </div>
            ) : null}
          </div>
        ) : (
          messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              onSelectCitation={onSelectCitation}
            />
          ))
        )}
      </div>

      <div className="border-t border-ide-border bg-ide-panel">
        <div key={mode} className="msg-in">
        {mode === "docs" ? (
          <QuestionComposer
            busy={isBusy}
            placeholder={`Ask about ${collectionLabel} docs…`}
            onSend={(q) => onSendDocs(q, collection)}
          />
        ) : mode === "repo" ? (
          repoReady && selectedRepoId ? (
            <QuestionComposer
              busy={isBusy}
              placeholder="Ask about the selected repository…"
              onSend={(q) => onSendRepo(q, selectedRepoId)}
            />
          ) : (
            <div className="p-3 text-xs text-ide-muted">
              Select a repository with status{" "}
              <span className="text-ide-success">Ready</span> in the explorer to
              start a repository chat.
            </div>
          )
        ) : mode === "search" ? (
          <SearchComposer
            busy={isBusy}
            repoOnly={repoOnlySearch && Boolean(selectedRepoId)}
            hasRepo={Boolean(selectedRepoId)}
            onToggleRepoOnly={setRepoOnlySearch}
            onSend={(q, topK) =>
              onSendSearch(
                q,
                topK,
                repoOnlySearch ? selectedRepoId : null,
              )
            }
          />
        ) : mode === "debug" ? (
          <DebugPanel
            busy={isBusy}
            repositoryId={selectedRepoId}
            onSubmit={onSendDebug}
          />
        ) : (
          <PairPanel busy={isBusy} onSubmit={onSendPair} />
        )}
        </div>
      </div>
    </section>
  );
}
