"use client";

import { Bot, User } from "lucide-react";
import { useMemo } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import type { ChatMessage, Citation } from "@/lib/types";
import CitationChip from "./CitationChip";

interface MessageBubbleProps {
  message: ChatMessage;
  onSelectCitation: (citation: Citation) => void;
}

/**
 * Rewrites bare `[n]` citation markers (outside code) into anchor links
 * `[n](#cite-n)` so they can be rendered as interactive chips, while leaving
 * fenced code blocks and inline code untouched.
 */
function linkifyCitations(text: string, validIndices: Set<number>): string {
  if (validIndices.size === 0) return text;

  const transformPlain = (segment: string): string =>
    segment.replace(/\[(\d+)\]/g, (match, digits: string) => {
      const n = Number(digits);
      return validIndices.has(n) ? `[${n}](#cite-${n})` : match;
    });

  // Split out fenced code blocks first, then inline code, transforming only prose.
  const fenced = text.split(/(```[\s\S]*?```)/g);
  return fenced
    .map((block) => {
      if (block.startsWith("```")) return block;
      const inline = block.split(/(`[^`]*`)/g);
      return inline
        .map((part) => (part.startsWith("`") ? part : transformPlain(part)))
        .join("");
    })
    .join("");
}

export default function MessageBubble({
  message,
  onSelectCitation,
}: MessageBubbleProps) {
  const isUser = message.role === "user";

  const citationByIndex = useMemo(() => {
    const map = new Map<number, Citation>();
    for (const c of message.citations) map.set(c.index, c);
    return map;
  }, [message.citations]);

  const processed = useMemo(
    () => linkifyCitations(message.content, new Set(citationByIndex.keys())),
    [message.content, citationByIndex],
  );

  const components: Components = useMemo(
    () => ({
      a({ href, children, ...props }) {
        const match = href?.match(/^#cite-(\d+)$/);
        if (match) {
          const idx = Number(match[1]);
          const citation = citationByIndex.get(idx);
          if (citation) {
            return (
              <CitationChip citation={citation} onSelect={onSelectCitation} />
            );
          }
        }
        return (
          <a href={href} target="_blank" rel="noreferrer noopener" {...props}>
            {children}
          </a>
        );
      },
    }),
    [citationByIndex, onSelectCitation],
  );

  return (
    <div
      className={`msg-in flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}
      role="listitem"
    >
      <div
        aria-hidden="true"
        className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border ${
          isUser
            ? "border-ide-accent/40 bg-ide-accent/15 text-ide-accent"
            : "border-ide-border bg-ide-elevated text-ide-muted"
        }`}
      >
        {isUser ? <User size={15} /> : <Bot size={15} />}
      </div>

      <div
        className={`min-w-0 max-w-[85%] rounded-lg border px-3 py-2 ${
          isUser
            ? "border-ide-accent/30 bg-ide-accent/10"
            : message.error
              ? "border-ide-danger/40 bg-ide-danger/10"
              : "border-ide-border bg-ide-panel"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap break-words text-sm text-ide-text">
            {message.content}
          </p>
        ) : (
          <div className="markdown-body min-w-0">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
              {processed}
            </ReactMarkdown>
            {message.pending && message.content.length === 0 ? (
              <span
                className="flex items-center gap-2 text-ide-muted"
                role="status"
                aria-label="Generating response"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src="/loader.webp"
                  alt=""
                  aria-hidden="true"
                  draggable={false}
                  className="h-12 w-12 select-none"
                />
                <span className="text-xs">Thinking…</span>
              </span>
            ) : message.pending ? (
              <span className="cursor-blink" aria-hidden="true" />
            ) : null}
            {!message.pending && (message.model || message.provider) ? (
              <div className="mt-2 border-t border-ide-border pt-1.5 text-[0.7rem] text-ide-muted">
                {message.provider ? `${message.provider} · ` : ""}
                {message.model ?? ""}
              </div>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
