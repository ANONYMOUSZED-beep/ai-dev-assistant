"use client";

import type { Citation } from "@/lib/types";

interface CitationChipProps {
  citation: Citation;
  onSelect: (citation: Citation) => void;
}

export default function CitationChip({ citation, onSelect }: CitationChipProps) {
  const label = citation.title || citation.uri || `Source ${citation.index}`;
  return (
    <button
      type="button"
      onClick={() => onSelect(citation)}
      title={label}
      aria-label={`Open citation ${citation.index}: ${label}`}
      className="mx-0.5 inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded border border-ide-accent/40 bg-ide-accent/15 px-1 align-middle font-mono text-[0.7rem] font-medium text-ide-accent transition-colors hover:bg-ide-accent/30 focus:outline-none focus-visible:ring-1 focus-visible:ring-ide-accent"
    >
      {citation.index}
    </button>
  );
}
