"use client";

import { ExternalLink } from "lucide-react";
import { useEffect, useRef } from "react";

import type { Citation } from "@/lib/types";

interface CitationsListProps {
  citations: Citation[];
  activeIndex: number | null;
  onSelect: (citation: Citation) => void;
}

export default function CitationsList({
  citations,
  activeIndex,
  onSelect,
}: CitationsListProps) {
  const containerRef = useRef<HTMLUListElement | null>(null);
  const itemRefs = useRef<Map<number, HTMLLIElement>>(new Map());

  // Scroll the active citation into view when it changes.
  useEffect(() => {
    if (activeIndex == null) return;
    const el = itemRefs.current.get(activeIndex);
    el?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [activeIndex]);

  if (citations.length === 0) {
    return (
      <div className="px-3 py-4 text-xs text-ide-muted">
        Citations from the latest answer will appear here.
      </div>
    );
  }

  return (
    <ul
      ref={containerRef}
      className="list-stagger flex flex-col gap-1.5 p-2"
      aria-label="Citations"
    >
      {citations.map((citation) => {
        const isActive = citation.index === activeIndex;
        return (
          <li
            key={citation.index}
            ref={(node) => {
              if (node) itemRefs.current.set(citation.index, node);
              else itemRefs.current.delete(citation.index);
            }}
          >
            <button
              type="button"
              onClick={() => onSelect(citation)}
              aria-current={isActive ? "true" : undefined}
              className={`w-full rounded-md border px-2.5 py-2 text-left transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-ide-accent ${
                isActive
                  ? "border-ide-accent/60 bg-ide-accent/10"
                  : "border-ide-border bg-ide-panel hover:bg-ide-hover"
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-ide-accent/20 font-mono text-[0.7rem] font-semibold text-ide-accent">
                  {citation.index}
                </span>
                <span
                  className="min-w-0 flex-1 truncate text-xs font-medium text-ide-text"
                  title={citation.title}
                >
                  {citation.title}
                </span>
                {citation.score != null ? (
                  <span className="shrink-0 font-mono text-[0.65rem] text-ide-muted">
                    {citation.score.toFixed(2)}
                  </span>
                ) : null}
              </div>
              {citation.snippet ? (
                <p className="mt-1 line-clamp-2 font-mono text-[0.7rem] leading-snug text-ide-muted">
                  {citation.snippet.trim().slice(0, 160)}
                </p>
              ) : null}
              <div className="mt-1 flex items-center gap-1 text-[0.65rem] text-ide-muted">
                <span className="rounded bg-ide-elevated px-1 py-0.5 uppercase tracking-wide">
                  {citation.source_type}
                </span>
                {citation.uri ? (
                  <span className="inline-flex min-w-0 items-center gap-0.5">
                    <ExternalLink size={10} className="shrink-0" aria-hidden="true" />
                    <span className="truncate" title={citation.uri}>
                      {citation.uri}
                    </span>
                  </span>
                ) : null}
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
