"use client";

import { Terminal } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import MessageBubble from "@/components/MessageBubble";
import { getSharedConversation } from "@/lib/api";
import { humanizeError } from "@/lib/errors";
import type { ChatMessage, ConversationDetail } from "@/lib/types";

export default function SharedConversationPage() {
  const params = useParams<{ id: string }>();
  const shareId = params?.id ?? "";
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!shareId) return;
    getSharedConversation(shareId)
      .then(setDetail)
      .catch((err) => setError(humanizeError(err)))
      .finally(() => setLoading(false));
  }, [shareId]);

  const messages: ChatMessage[] = (detail?.messages ?? []).map((m) => ({
    id: m.id,
    role: m.role,
    content: m.content,
    citations: m.citations ?? [],
  }));

  return (
    <div className="min-h-screen bg-ide-bg text-ide-text">
      <header className="flex items-center justify-between border-b border-ide-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Terminal size={18} className="text-ide-accent" aria-hidden="true" />
          <span className="font-display text-sm font-semibold">
            AI Developer Assistant
          </span>
        </div>
        <Link
          href="/app"
          className="rounded-md bg-ide-accentMuted px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-ide-accent"
        >
          Try it yourself
        </Link>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-8">
        {detail?.title ? (
          <div className="mb-6">
            <p className="text-[0.7rem] uppercase tracking-wide text-ide-muted">
              Shared conversation
            </p>
            <h1 className="font-display text-2xl font-semibold text-ide-text">
              {detail.title}
            </h1>
          </div>
        ) : null}

        {loading ? (
          <p className="text-sm text-ide-muted">Loading…</p>
        ) : error ? (
          <div className="rounded-lg border border-ide-border bg-ide-panel p-6 text-center">
            <p className="text-sm text-ide-muted">{error}</p>
            <Link
              href="/app"
              className="mt-3 inline-block text-xs text-ide-accent underline underline-offset-2"
            >
              Go to the app
            </Link>
          </div>
        ) : (
          <div className="space-y-4 rounded-lg border border-ide-border bg-ide-panel p-4">
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                onSelectCitation={() => {}}
              />
            ))}
          </div>
        )}

        <p className="mt-8 text-center text-[0.7rem] text-ide-muted">
          {"Grounded, cited answers from your docs and code."}
        </p>
      </main>
    </div>
  );
}
