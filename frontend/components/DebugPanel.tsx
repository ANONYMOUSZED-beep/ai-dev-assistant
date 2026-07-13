"use client";

import { Bug, Loader2 } from "lucide-react";
import { useState } from "react";

import type { DebugRequest } from "@/lib/types";

interface DebugPanelProps {
  busy: boolean;
  repositoryId: string | null;
  onSubmit: (req: DebugRequest) => void;
}

export default function DebugPanel({
  busy,
  repositoryId,
  onSubmit,
}: DebugPanelProps) {
  const [error, setError] = useState("");
  const [language, setLanguage] = useState("");
  const [codeContext, setCodeContext] = useState("");
  const [useRepo, setUseRepo] = useState(true);

  const fillExample = () => {
    setError(
      [
        "Traceback (most recent call last):",
        '  File "app/orders.py", line 42, in total_price',
        "    return prices[item] * quantity",
        "KeyError: 'widget'",
      ].join("\n"),
    );
    setLanguage("python");
    setCodeContext(
      [
        "def total_price(prices, item, quantity):",
        "    return prices[item] * quantity",
      ].join("\n"),
    );
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = error.trim();
    if (!trimmed || busy) return;
    onSubmit({
      error: trimmed,
      language: language.trim() || null,
      code_context: codeContext.trim() || null,
      repository_id: useRepo ? repositoryId : null,
    });
    setError("");
    setCodeContext("");
  };

  return (
    <form onSubmit={submit} className="space-y-2 p-3">
      <div>
        <div className="mb-1 flex items-center justify-between gap-2">
          <label
            htmlFor="debug-error"
            className="block text-[0.7rem] font-semibold uppercase tracking-wide text-ide-muted"
          >
            Error / stack trace
          </label>
          <button
            type="button"
            onClick={fillExample}
            className="rounded text-[0.7rem] font-medium text-ide-muted underline decoration-dotted underline-offset-2 transition-colors hover:text-ide-accent focus:outline-none focus-visible:ring-1 focus-visible:ring-ide-accent"
          >
            {"Try an example"}
          </button>
        </div>
        <textarea
          id="debug-error"
          value={error}
          onChange={(e) => setError(e.target.value)}
          rows={4}
          required
          placeholder="Paste the error message or stack trace…"
          className="w-full resize-y rounded-md border border-ide-border bg-ide-bg px-2.5 py-2 font-mono text-xs text-ide-text placeholder:text-ide-muted focus:border-ide-accent focus:outline-none"
        />
      </div>
      <div className="flex gap-2">
        <div className="w-32 shrink-0">
          <label
            htmlFor="debug-language"
            className="mb-1 block text-[0.7rem] font-semibold uppercase tracking-wide text-ide-muted"
          >
            Language
          </label>
          <input
            id="debug-language"
            type="text"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            placeholder="python"
            className="w-full rounded-md border border-ide-border bg-ide-bg px-2 py-1.5 text-xs text-ide-text placeholder:text-ide-muted focus:border-ide-accent focus:outline-none"
          />
        </div>
        <label className="flex flex-1 items-end gap-1.5 pb-1.5 text-[0.7rem] text-ide-muted">
          <input
            type="checkbox"
            checked={useRepo}
            disabled={!repositoryId}
            onChange={(e) => setUseRepo(e.target.checked)}
            className="accent-ide-accent"
          />
          Use selected repository{" "}
          {repositoryId ? "" : "(none selected)"}
        </label>
      </div>
      <div>
        <label
          htmlFor="debug-context"
          className="mb-1 block text-[0.7rem] font-semibold uppercase tracking-wide text-ide-muted"
        >
          Code context (optional)
        </label>
        <textarea
          id="debug-context"
          value={codeContext}
          onChange={(e) => setCodeContext(e.target.value)}
          rows={3}
          placeholder="Relevant code around the error…"
          className="w-full resize-y rounded-md border border-ide-border bg-ide-bg px-2.5 py-2 font-mono text-xs text-ide-text placeholder:text-ide-muted focus:border-ide-accent focus:outline-none"
        />
      </div>
      <button
        type="submit"
        disabled={busy || error.trim().length === 0}
        className="flex items-center gap-1.5 rounded-md bg-ide-accentMuted px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-ide-accent focus:outline-none focus-visible:ring-1 focus-visible:ring-ide-accent disabled:cursor-not-allowed disabled:opacity-50"
      >
        {busy ? (
          <Loader2 size={14} className="animate-spin" aria-hidden="true" />
        ) : (
          <Bug size={14} aria-hidden="true" />
        )}
        Diagnose
      </button>
    </form>
  );
}
