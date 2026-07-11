"use client";

import { BookOpen, X } from "lucide-react";

import { DOC_COLLECTIONS } from "@/lib/collections";
import type { DocCollection } from "@/lib/types";
import IngestDocs from "./IngestDocs";

interface CollectionSelectorProps {
  value: string;
  onChange: (collection: string) => void;
  customCollections: DocCollection[];
  onIngested: (collection: string) => void;
  onRemoveCustom: (id: string) => void;
}

function CollectionButton({
  collection,
  active,
  custom,
  onSelect,
  onRemove,
}: {
  collection: DocCollection;
  active: boolean;
  custom?: boolean;
  onSelect: () => void;
  onRemove?: () => void;
}) {
  return (
    <div className="group relative">
      <button
        type="button"
        aria-pressed={active}
        onClick={onSelect}
        className={`flex w-full items-center gap-1.5 truncate rounded-md border px-2 py-1.5 text-left text-xs transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-ide-accent ${
          active
            ? "border-ide-accent/60 bg-ide-accent/10 text-ide-text"
            : "border-ide-border bg-ide-panel text-ide-muted hover:bg-ide-hover hover:text-ide-text"
        }`}
        title={
          custom
            ? `${collection.label} — your uploaded documents`
            : collection.label
        }
      >
        {custom ? (
          <span
            className="h-1.5 w-1.5 shrink-0 rounded-full bg-ide-success"
            aria-hidden="true"
          />
        ) : null}
        <span className="truncate">{collection.label}</span>
      </button>
      {custom && onRemove ? (
        <button
          type="button"
          onClick={onRemove}
          aria-label={`Remove ${collection.label} from the list`}
          title="Remove from list"
          className="absolute right-1 top-1/2 -translate-y-1/2 rounded p-0.5 text-ide-muted opacity-0 transition-opacity hover:text-ide-danger group-hover:opacity-100"
        >
          <X size={11} />
        </button>
      ) : null}
    </div>
  );
}

export default function CollectionSelector({
  value,
  onChange,
  customCollections,
  onIngested,
  onRemoveCustom,
}: CollectionSelectorProps) {
  return (
    <div className="px-3 py-2">
      <div className="mb-1.5 flex items-center justify-between">
        <span className="flex items-center gap-1.5 text-[0.7rem] font-semibold uppercase tracking-wide text-ide-muted">
          <BookOpen size={12} />
          Documentation
        </span>
        <IngestDocs collection={value} onIngested={onIngested} />
      </div>

      <div className="grid grid-cols-2 gap-1.5">
        {DOC_COLLECTIONS.map((collection) => (
          <CollectionButton
            key={collection.id}
            collection={collection}
            active={collection.id === value}
            onSelect={() => onChange(collection.id)}
          />
        ))}
      </div>

      {customCollections.length > 0 ? (
        <>
          <div className="mb-1.5 mt-3 flex items-center gap-1.5 text-[0.65rem] font-semibold uppercase tracking-wide text-ide-muted">
            <span className="h-1.5 w-1.5 rounded-full bg-ide-success" />
            Your uploads
          </div>
          <div className="grid grid-cols-2 gap-1.5">
            {customCollections.map((collection) => (
              <CollectionButton
                key={collection.id}
                collection={collection}
                active={collection.id === value}
                custom
                onSelect={() => onChange(collection.id)}
                onRemove={() => onRemoveCustom(collection.id)}
              />
            ))}
          </div>
        </>
      ) : null}

      <p className="mt-2 text-[0.7rem] text-ide-muted">
        Active collection:{" "}
        <span className="font-mono text-ide-text">{value}</span>
      </p>
    </div>
  );
}
