"use client";

import {
  Bug,
  FileText,
  GitBranch,
  Search,
  Sparkles,
  Terminal,
  X,
} from "lucide-react";

import type { ChatMode } from "@/lib/types";

interface WelcomeGuideProps {
  open: boolean;
  onClose: () => void;
  onPick: (mode: ChatMode) => void;
}

const OPTIONS: {
  mode: ChatMode;
  title: string;
  desc: string;
  icon: typeof FileText;
}[] = [
  {
    mode: "docs",
    title: "Ask about documents",
    desc: "Upload PDFs, notes, or docs and ask questions in plain English.",
    icon: FileText,
  },
  {
    mode: "repo",
    title: "Understand a code project",
    desc: "Add a GitHub project and ask how it works.",
    icon: GitBranch,
  },
  {
    mode: "debug",
    title: "Fix an error",
    desc: "Paste an error message and get a clear explanation and fix.",
    icon: Bug,
  },
  {
    mode: "search",
    title: "Search code",
    desc: "Find where something lives in a project by describing it.",
    icon: Search,
  },
  {
    mode: "pair",
    title: "Improve code",
    desc: "Explain, refactor, test, or review a snippet of code.",
    icon: Sparkles,
  },
];

export default function WelcomeGuide({
  open,
  onClose,
  onPick,
}: WelcomeGuideProps) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[120] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="Welcome"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-2xl overflow-hidden rounded-2xl border border-ide-border bg-ide-panel shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-ide-border px-6 py-5">
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-ide-accent/10 text-ide-accent">
              <Terminal size={18} />
            </span>
            <div>
              <h2 className="font-display text-lg font-semibold text-ide-text">
                Welcome 👋 What would you like to do?
              </h2>
              <p className="text-xs text-ide-muted">
                Pick a starting point — you can switch anytime from the left bar.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded p-1 text-ide-muted hover:bg-ide-hover hover:text-ide-text"
          >
            <X size={18} />
          </button>
        </div>

        <div className="grid grid-cols-1 gap-3 p-6 sm:grid-cols-2">
          {OPTIONS.map((opt) => {
            const Icon = opt.icon;
            return (
              <button
                key={opt.mode}
                type="button"
                onClick={() => onPick(opt.mode)}
                className="group flex items-start gap-3 rounded-xl border border-ide-border bg-ide-bg p-4 text-left transition-colors hover:border-ide-accent/50 hover:bg-ide-accent/5"
              >
                <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-ide-border bg-ide-panel text-ide-accent transition-colors group-hover:border-ide-accent/40">
                  <Icon size={18} />
                </span>
                <span className="min-w-0">
                  <span className="block text-sm font-semibold text-ide-text">
                    {opt.title}
                  </span>
                  <span className="mt-0.5 block text-xs text-ide-muted">
                    {opt.desc}
                  </span>
                </span>
              </button>
            );
          })}
        </div>

        <div className="flex justify-end border-t border-ide-border px-6 py-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-4 py-1.5 text-xs font-medium text-ide-muted hover:bg-ide-hover hover:text-ide-text"
          >
            I'll explore on my own
          </button>
        </div>
      </div>
    </div>
  );
}
