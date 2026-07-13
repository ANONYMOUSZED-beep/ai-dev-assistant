"use client";

import { useState } from "react";

import type { Citation } from "@/lib/types";

interface CitationChipProps {
  citation: Citation;
  onSelect: (citation: Citation) => void;
}

function buildLocation(citation: Citation): string | null {
  if (!citation.uri) {
    return null;
  }
  if (citation.start_line != null && citation.end_line != null) {
    return `${citation.uri}:${citation.start_line}-${citation.end_line}`;
  }
  if (citation.start_line != null) {
    return `${citation.uri}:${citation.start_line}`;
  }
  return citation.uri;
}

export default function CitationChip({ citation, onSelect }: CitationChipProps) {
  const [open, setOpen] = useState(false);
  const label = citation.title || citation.uri || `Source ${citation.index}`;
  const location = buildLocation(citation);
  const popoverId = `citation-popover-${citation.index}`;

  const show = () => setOpen(true);
  const hide = () => setOpen(false);

  return (
    <span
      className="relative inline-block"
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      <button
        type="button"
        onClick={() => onSelect(citation)}
        title={label}
        aria-label={`Open citation ${citation.index}: ${label}`}
        aria-describedby={open ? popoverId : undefined}
        className="mx-0.5 inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded border border-ide-accent/40 bg-ide-accent/15 px-1 align-middle font-mono text-[0.7rem] font-medium text-ide-accent transition-colors hover:bg-ide-accent/30 focus:outline-none focus-visible:ring-1 focus-visible:ring-ide-accent"
      >
        {citation.index}
      </button>
      {open && (
        <span
          id={popoverId}
          role="tooltip"
          className="absolute bottom-full left-0 z-50 mb-1 block w-max max-w-[20rem] rounded-md border border-ide-border bg-ide-panel p-3 text-left shadow-lg"
        >
          <span className="block text-xs font-semibold text-ide-text">
            {label}
          </span>
          {location && (
            <span className="mt-0.5 block break-all font-mono text-[0.65rem] text-ide-muted">
              {location}
            </span>
          )}
          {citation.snippet && (
            <span className="mt-2 block overflow-hidden text-[0.7rem] leading-snug text-ide-muted [display:-webkit-box] [-webkit-box-orient:vertical] [-webkit-line-clamp:4]">
              {citation.snippet}
            </span>
          )}
        </span>
      )}
    </span>
  );
}
