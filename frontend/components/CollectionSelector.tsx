"use client";

import { BookOpen } from "lucide-react";

import { DOC_COLLECTIONS } from "@/lib/collections";
import IngestDocs from "./IngestDocs";

interface CollectionSelectorProps {
  value: string;
  onChange: (collection: string) => void;
}

export default function CollectionSelector({
  value,
  onChange,
}: CollectionSelectorProps) {
  return (
    <div className="px-3 py-2">
      <div className="mb-1.5 flex items-center justify-between">
        <span className="flex items-center gap-1.5 text-[0.7rem] font-semibold uppercase tracking-wide text-ide-muted">
          <BookOpen size={12} />
          Documentation
        </span>
        <IngestDocs collection={value} onIngested={onChange} />
      </div>
      <div className="grid grid-cols-2 gap-1.5">
        {DOC_COLLECTIONS.map((collection) => {
          const active = collection.id === value;
          return (
            <button
              key={collection.id}
              type="button"
              aria-pressed={active}
              onClick={() => onChange(collection.id)}
              className={`truncate rounded-md border px-2 py-1.5 text-left text-xs transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-ide-accent ${
                active
                  ? "border-ide-accent/60 bg-ide-accent/10 text-ide-text"
                  : "border-ide-border bg-ide-panel text-ide-muted hover:bg-ide-hover hover:text-ide-text"
              }`}
              title={collection.label}
            >
              {collection.label}
            </button>
          );
        })}
      </div>
      <p className="mt-2 text-[0.7rem] text-ide-muted">
        Active collection:{" "}
        <span className="font-mono text-ide-text">{value}</span>
      </p>
    </div>
  );
}
