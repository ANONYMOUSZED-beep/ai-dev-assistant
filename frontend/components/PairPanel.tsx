"use client";

import { Loader2, Sparkles } from "lucide-react";
import { useState } from "react";

import type { PairAction, PairRequest } from "@/lib/types";

interface PairPanelProps {
  busy: boolean;
  onSubmit: (req: PairRequest) => void;
}

const ACTIONS: { id: PairAction; label: string }[] = [
  { id: "explain", label: "Explain" },
  { id: "refactor", label: "Refactor" },
  { id: "test", label: "Generate Tests" },
  { id: "document", label: "Document" },
  { id: "optimize", label: "Optimize" },
  { id: "security", label: "Security Review" },
];

export default function PairPanel({ busy, onSubmit }: PairPanelProps) {
  const [action, setAction] = useState<PairAction>("explain");
  const [code, setCode] = useState("");
  const [language, setLanguage] = useState("");
  const [instructions, setInstructions] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = code.trim();
    if (!trimmed || busy) return;
    onSubmit({
      action,
      code: trimmed,
      language: language.trim() || null,
      instructions: instructions.trim() || null,
    });
  };

  return (
    <form onSubmit={submit} className="space-y-2 p-3">
      <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label="Action">
        {ACTIONS.map((a) => {
          const active = a.id === action;
          return (
            <button
              key={a.id}
              type="button"
              role="radio"
              aria-checked={active}
              onClick={() => setAction(a.id)}
              className={`rounded-md border px-2.5 py-1 text-xs font-medium transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-ide-accent ${
                active
                  ? "border-ide-accent/60 bg-ide-accent/10 text-ide-text"
                  : "border-ide-border bg-ide-panel text-ide-muted hover:bg-ide-hover hover:text-ide-text"
              }`}
            >
              {a.label}
            </button>
          );
        })}
      </div>
      <div>
        <label
          htmlFor="pair-code"
          className="mb-1 block text-[0.7rem] font-semibold uppercase tracking-wide text-ide-muted"
        >
          Code
        </label>
        <textarea
          id="pair-code"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          rows={6}
          required
          placeholder="Paste the code you want to work on…"
          className="w-full resize-y rounded-md border border-ide-border bg-ide-bg px-2.5 py-2 font-mono text-xs text-ide-text placeholder:text-ide-muted focus:border-ide-accent focus:outline-none"
        />
      </div>
      <div className="flex gap-2">
        <div className="w-32 shrink-0">
          <label
            htmlFor="pair-language"
            className="mb-1 block text-[0.7rem] font-semibold uppercase tracking-wide text-ide-muted"
          >
            Language
          </label>
          <input
            id="pair-language"
            type="text"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            placeholder="typescript"
            className="w-full rounded-md border border-ide-border bg-ide-bg px-2 py-1.5 text-xs text-ide-text placeholder:text-ide-muted focus:border-ide-accent focus:outline-none"
          />
        </div>
        <div className="flex-1">
          <label
            htmlFor="pair-instructions"
            className="mb-1 block text-[0.7rem] font-semibold uppercase tracking-wide text-ide-muted"
          >
            Instructions (optional)
          </label>
          <input
            id="pair-instructions"
            type="text"
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            placeholder="e.g. target Python 3.12, prefer async"
            className="w-full rounded-md border border-ide-border bg-ide-bg px-2 py-1.5 text-xs text-ide-text placeholder:text-ide-muted focus:border-ide-accent focus:outline-none"
          />
        </div>
      </div>
      <button
        type="submit"
        disabled={busy || code.trim().length === 0}
        className="flex items-center gap-1.5 rounded-md bg-ide-accentMuted px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-ide-accent disabled:cursor-not-allowed disabled:opacity-50"
      >
        {busy ? (
          <Loader2 size={14} className="animate-spin" />
        ) : (
          <Sparkles size={14} />
        )}
        Run
      </button>
    </form>
  );
}
