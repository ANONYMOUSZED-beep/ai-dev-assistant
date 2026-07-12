"use client";

import {
  Bug,
  Check,
  FileText,
  GitBranch,
  History,
  type LucideIcon,
  Plus,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { useState } from "react";

import type { ConversationKind, ConversationSummary } from "@/lib/types";

interface ChatHistoryProps {
  conversations: ConversationSummary[];
  activeId: string | null;
  loading: boolean;
  onSelect: (conversation: ConversationSummary) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
}

/** Per-kind badge presentation: icon, short label, and colour classes. */
const KIND_META: Record<
  ConversationKind,
  { icon: LucideIcon; label: string; badge: string }
> = {
  docs: {
    icon: FileText,
    label: "Docs",
    badge: "bg-sky-100 text-sky-700",
  },
  repo: {
    icon: GitBranch,
    label: "Repo",
    badge: "bg-violet-100 text-violet-700",
  },
  debug: {
    icon: Bug,
    label: "Debug",
    badge: "bg-rose-100 text-rose-700",
  },
  pair: {
    icon: Sparkles,
    label: "Pair",
    badge: "bg-amber-100 text-amber-700",
  },
};

function KindBadge({ kind }: { kind: ConversationKind }) {
  const meta = KIND_META[kind] ?? KIND_META.docs;
  const Icon = meta.icon;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[0.6rem] font-semibold uppercase tracking-wide ${meta.badge}`}
    >
      <Icon size={10} />
      {meta.label}
    </span>
  );
}

export default function ChatHistory({
  conversations,
  activeId,
  loading,
  onSelect,
  onNew,
  onDelete,
}: ChatHistoryProps) {
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  return (
    <section aria-label="Chat history" className="px-3 pt-3">
      <div className="mb-2 flex items-center justify-between px-1">
        <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-ide-muted">
          <History size={13} className="text-ide-accent" />
          History
        </div>
        <button
          type="button"
          onClick={onNew}
          className="flex items-center gap-1 rounded-md border border-ide-border px-1.5 py-0.5 text-[0.7rem] text-ide-text transition-colors hover:border-ide-accent/50 hover:bg-ide-accent/5"
          title="Start a new chat"
        >
          <Plus size={12} /> New
        </button>
      </div>

      {conversations.length === 0 ? (
        <p className="px-1 pb-2 text-[0.7rem] text-ide-muted">
          {loading ? "Loading…" : "No saved chats yet."}
        </p>
      ) : (
        <ul className="space-y-1">
          {conversations.map((c) => {
            const active = c.id === activeId;
            return (
              <li key={c.id}>
                <div
                  className={`group flex items-start gap-2 rounded-md border px-2 py-1.5 transition-colors ${
                    active
                      ? "border-ide-accent/50 bg-ide-accent/5"
                      : "border-transparent hover:border-ide-border hover:bg-ide-hover"
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => onSelect(c)}
                    className="min-w-0 flex-1 text-left"
                    title={c.title ?? "Untitled chat"}
                  >
                    <div className="mb-0.5 flex items-center gap-1.5">
                      <KindBadge kind={c.kind} />
                    </div>
                    <p className="truncate text-xs text-ide-text">
                      {c.title ?? "Untitled chat"}
                    </p>
                  </button>
                  {confirmDeleteId === c.id ? (
                    <div className="mt-0.5 flex items-center gap-0.5">
                      <button
                        type="button"
                        onClick={() => {
                          onDelete(c.id);
                          setConfirmDeleteId(null);
                        }}
                        aria-label="Confirm delete"
                        title="Delete"
                        className="rounded p-0.5 text-ide-danger hover:bg-ide-hover"
                      >
                        <Check size={13} />
                      </button>
                      <button
                        type="button"
                        onClick={() => setConfirmDeleteId(null)}
                        aria-label="Cancel"
                        title="Keep"
                        className="rounded p-0.5 text-ide-muted hover:bg-ide-hover hover:text-ide-text"
                      >
                        <X size={13} />
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setConfirmDeleteId(c.id)}
                      aria-label="Delete conversation"
                      title="Delete conversation"
                      className="mt-0.5 rounded p-0.5 text-ide-muted opacity-0 transition-opacity hover:text-ide-danger group-hover:opacity-100"
                    >
                      <Trash2 size={13} />
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
