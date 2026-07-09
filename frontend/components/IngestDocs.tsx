"use client";

import {
  CheckCircle2,
  FileUp,
  Link2,
  Loader2,
  Plus,
  Type,
  X,
} from "lucide-react";
import { useState } from "react";

import { ApiError, ingestDocument, uploadDocument } from "@/lib/api";

interface IngestDocsProps {
  collection: string;
  onIngested?: (collection: string) => void;
}

type Tab = "text" | "url" | "file";

const TABS: { id: Tab; label: string; icon: typeof Type }[] = [
  { id: "text", label: "Paste text", icon: Type },
  { id: "url", label: "From URL", icon: Link2 },
  { id: "file", label: "Upload file", icon: FileUp },
];

export default function IngestDocs({ collection, onIngested }: IngestDocsProps) {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<Tab>("text");

  const [coll, setColl] = useState(collection);
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const openModal = () => {
    setColl(collection);
    setTitle("");
    setText("");
    setUrl("");
    setFile(null);
    setError(null);
    setResult(null);
    setTab("text");
    setOpen(true);
  };

  const canSubmit =
    coll.trim().length > 0 &&
    !busy &&
    ((tab === "text" && text.trim().length > 0) ||
      (tab === "url" && url.trim().length > 0) ||
      (tab === "file" && file != null));

  const submit = async () => {
    if (!canSubmit) return;
    setBusy(true);
    setError(null);
    setResult(null);
    const target = coll.trim();
    try {
      let chunks = 0;
      if (tab === "text") {
        const res = await ingestDocument({
          collection: target,
          text: text.trim(),
          title: title.trim() || "Pasted document",
          source_type: "txt",
        });
        chunks = res.chunks_indexed;
      } else if (tab === "url") {
        const res = await ingestDocument({
          collection: target,
          uri: url.trim(),
          title: title.trim() || undefined,
        });
        chunks = res.chunks_indexed;
      } else if (file) {
        const res = await uploadDocument(
          target,
          file,
          title.trim() || undefined,
        );
        chunks = res.chunks_indexed;
      }
      setResult(`Indexed ${chunks} chunk(s) into "${target}".`);
      setText("");
      setUrl("");
      setFile(null);
      onIngested?.(target);
    } catch (err) {
      setError(
        err instanceof ApiError || err instanceof Error
          ? err.message
          : String(err),
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={openModal}
        className="flex items-center gap-1 rounded p-1 text-ide-muted transition-colors hover:bg-ide-hover hover:text-ide-text focus:outline-none focus-visible:ring-1 focus-visible:ring-ide-accent"
        title="Add documents"
        aria-label="Add documents"
      >
        <Plus size={14} />
      </button>

      {open ? (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-label="Add documents"
          onClick={(e) => {
            if (e.target === e.currentTarget) setOpen(false);
          }}
        >
          <div className="w-full max-w-lg overflow-hidden rounded-xl border border-ide-border bg-ide-panel shadow-2xl">
            <div className="flex items-center justify-between border-b border-ide-border px-4 py-3">
              <h2 className="text-sm font-semibold text-ide-text">
                Add documents
              </h2>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded p-1 text-ide-muted hover:bg-ide-hover hover:text-ide-text"
                aria-label="Close"
              >
                <X size={16} />
              </button>
            </div>

            <div className="space-y-4 p-4">
              <div>
                <label
                  htmlFor="ingest-collection"
                  className="mb-1 block text-[0.7rem] font-semibold uppercase tracking-wide text-ide-muted"
                >
                  Collection
                </label>
                <input
                  id="ingest-collection"
                  type="text"
                  value={coll}
                  onChange={(e) => setColl(e.target.value)}
                  placeholder="e.g. python, my-project-docs"
                  className="w-full rounded-md border border-ide-border bg-ide-bg px-2.5 py-1.5 text-sm text-ide-text placeholder:text-ide-muted focus:border-ide-accent focus:outline-none"
                />
                <p className="mt-1 text-[0.7rem] text-ide-muted">
                  Answers in Docs Chat are grounded in the active collection.
                </p>
              </div>

              <div className="flex gap-1 rounded-md border border-ide-border bg-ide-bg p-1">
                {TABS.map((t) => {
                  const Icon = t.icon;
                  const active = t.id === tab;
                  return (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => {
                        setTab(t.id);
                        setError(null);
                      }}
                      className={`flex flex-1 items-center justify-center gap-1.5 rounded px-2 py-1.5 text-xs font-medium transition-colors ${
                        active
                          ? "bg-ide-accent/15 text-ide-accent"
                          : "text-ide-muted hover:text-ide-text"
                      }`}
                    >
                      <Icon size={13} />
                      {t.label}
                    </button>
                  );
                })}
              </div>

              <div>
                <label
                  htmlFor="ingest-title"
                  className="mb-1 block text-[0.7rem] font-semibold uppercase tracking-wide text-ide-muted"
                >
                  Title (optional)
                </label>
                <input
                  id="ingest-title"
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Shown in citations"
                  className="w-full rounded-md border border-ide-border bg-ide-bg px-2.5 py-1.5 text-sm text-ide-text placeholder:text-ide-muted focus:border-ide-accent focus:outline-none"
                />
              </div>

              {tab === "text" ? (
                <textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  rows={6}
                  placeholder="Paste documentation, notes, or any text to index…"
                  aria-label="Document text"
                  className="w-full resize-none rounded-md border border-ide-border bg-ide-bg px-2.5 py-2 text-sm text-ide-text placeholder:text-ide-muted focus:border-ide-accent focus:outline-none"
                />
              ) : tab === "url" ? (
                <input
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://example.com/docs/page (web, .md, .pdf, .txt)"
                  aria-label="Document URL"
                  className="w-full rounded-md border border-ide-border bg-ide-bg px-2.5 py-1.5 text-sm text-ide-text placeholder:text-ide-muted focus:border-ide-accent focus:outline-none"
                />
              ) : (
                <div>
                  <input
                    type="file"
                    accept=".pdf,.docx,.md,.markdown,.mdx,.txt,.rst,.html,.htm"
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                    aria-label="Document file"
                    className="block w-full text-xs text-ide-muted file:mr-3 file:rounded-md file:border-0 file:bg-ide-accentMuted file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-white hover:file:bg-ide-accent"
                  />
                  <p className="mt-1 text-[0.7rem] text-ide-muted">
                    PDF, DOCX, Markdown, HTML, or text · up to 10 MB
                  </p>
                </div>
              )}

              {error ? (
                <p className="rounded-md border border-ide-danger/40 bg-ide-danger/10 px-2.5 py-2 text-xs text-ide-danger">
                  {error}
                </p>
              ) : null}
              {result ? (
                <p className="flex items-center gap-1.5 rounded-md border border-ide-success/40 bg-ide-success/10 px-2.5 py-2 text-xs text-ide-success">
                  <CheckCircle2 size={14} />
                  {result}
                </p>
              ) : null}
            </div>

            <div className="flex justify-end gap-2 border-t border-ide-border px-4 py-3">
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded-md px-3 py-1.5 text-xs font-medium text-ide-muted hover:bg-ide-hover hover:text-ide-text"
              >
                Close
              </button>
              <button
                type="button"
                onClick={submit}
                disabled={!canSubmit}
                className="flex items-center gap-1.5 rounded-md bg-ide-accentMuted px-4 py-1.5 text-xs font-medium text-white transition-colors hover:bg-ide-accent disabled:cursor-not-allowed disabled:opacity-50"
              >
                {busy ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Plus size={14} />
                )}
                Add to collection
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
