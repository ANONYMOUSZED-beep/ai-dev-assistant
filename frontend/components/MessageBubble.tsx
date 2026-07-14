"use client";

import { diffWords } from "diff";
import { Bot, Check, Copy, GitCompare, User } from "lucide-react";
import { isValidElement, useMemo, useState, type ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import type { ChatMessage, Citation } from "@/lib/types";
import CitationChip from "./CitationChip";
import MermaidDiagram from "./MermaidDiagram";

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

/** Map a [0,1] grounding confidence to a labelled, colour-coded tier. */
function groundingTier(confidence: number): {
  label: string;
  className: string;
} {
  if (confidence >= 0.66) {
    return {
      label: "Well grounded",
      className: "border-ide-success/40 bg-ide-success/15 text-ide-success",
    };
  }
  if (confidence >= 0.4) {
    return {
      label: "Moderately grounded",
      className: "border-ide-warning/40 bg-ide-warning/15 text-ide-warning",
    };
  }
  return {
    label: "Thin evidence",
    className: "border-ide-danger/40 bg-ide-danger/15 text-ide-danger",
  };
}

/** Recursively pull the raw text out of a react-markdown code node. */
function extractCodeText(node: ReactNode): string {
  if (typeof node === "string") return node;
  if (Array.isArray(node)) return node.map(extractCodeText).join("");
  if (isValidElement(node)) {
    return extractCodeText((node.props as { children?: ReactNode }).children);
  }
  return "";
}

export default function MessageBubble({
  message,
  onSelectCitation,
}: MessageBubbleProps) {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);
  const [showDiff, setShowDiff] = useState(false);

  const diffParts = useMemo(() => {
    if (!message.previousContent) return null;
    return diffWords(message.previousContent, message.content);
  }, [message.previousContent, message.content]);

  const copyMessage = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  };

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
      pre({ children, ...props }) {
        const child = Array.isArray(children) ? children[0] : children;
        if (isValidElement(child)) {
          const codeProps = child.props as {
            className?: string;
            children?: ReactNode;
          };
          if (/\blanguage-mermaid\b/.test(codeProps.className ?? "")) {
            return <MermaidDiagram code={extractCodeText(codeProps.children)} />;
          }
        }
        return <pre {...props}>{children}</pre>;
      },
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
            {showDiff && diffParts ? (
              <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                {diffParts.map((part, i) => (
                  <span
                    key={i}
                    className={
                      part.added
                        ? "rounded bg-ide-success/20 text-ide-success"
                        : part.removed
                          ? "rounded bg-ide-danger/20 text-ide-danger line-through"
                          : "text-ide-text"
                    }
                  >
                    {part.value}
                  </span>
                ))}
              </p>
            ) : (
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
                {processed}
              </ReactMarkdown>
            )}
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
            {!message.pending && !message.error && message.content.length > 0 ? (
              <div className="mt-2 flex items-center gap-2 border-t border-ide-border pt-1.5 text-[0.7rem] text-ide-muted">
                <button
                  type="button"
                  onClick={copyMessage}
                  aria-label={copied ? "Copied" : "Copy answer"}
                  className="flex items-center gap-1 rounded px-1 py-0.5 transition-colors hover:bg-ide-hover hover:text-ide-text focus:outline-none focus-visible:ring-1 focus-visible:ring-ide-accent"
                >
                  {copied ? <Check size={12} /> : <Copy size={12} />}
                  {copied ? "Copied" : "Copy"}
                </button>
                {diffParts ? (
                  <button
                    type="button"
                    onClick={() => setShowDiff((v) => !v)}
                    aria-pressed={showDiff}
                    className={`flex items-center gap-1 rounded px-1 py-0.5 transition-colors hover:bg-ide-hover hover:text-ide-text focus:outline-none focus-visible:ring-1 focus-visible:ring-ide-accent ${showDiff ? "text-ide-accent" : ""}`}
                  >
                    <GitCompare size={12} />
                    {showDiff ? "Hide changes" : "Show changes"}
                  </button>
                ) : null}
                {typeof message.confidence === "number" ? (
                  (() => {
                    const tier = groundingTier(message.confidence);
                    return (
                      <span
                        className={`ml-auto inline-flex items-center rounded border px-1.5 py-0.5 font-medium ${tier.className}`}
                        title={`Grounding confidence: ${Math.round(
                          message.confidence * 100,
                        )}%`}
                      >
                        {tier.label}
                      </span>
                    );
                  })()
                ) : null}
                {message.model || message.provider ? (
                  <span
                    className={`truncate ${typeof message.confidence === "number" ? "" : "ml-auto"}`}
                  >
                    {message.provider ? `${message.provider} · ` : ""}
                    {message.model ?? ""}
                  </span>
                ) : null}
              </div>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
