"use client";

import {
  Bug,
  FileText,
  GitBranch,
  type LucideIcon,
  PanelLeft,
  PanelRight,
  Search,
  Sparkles,
  Terminal,
} from "lucide-react";

import type { ChatMode } from "@/lib/types";

interface TopBarProps {
  mode: ChatMode;
  sidebarOpen: boolean;
  rightOpen: boolean;
  onToggleSidebar: () => void;
  onToggleRight: () => void;
}

const MODE_META: Record<ChatMode, { label: string; icon: LucideIcon; hint: string }> = {
  docs: { label: "Docs Chat", icon: FileText, hint: "Grounded answers from documentation" },
  repo: { label: "Repo Chat", icon: GitBranch, hint: "Ask questions about an indexed repository" },
  search: { label: "Code Search", icon: Search, hint: "Semantic search across your code" },
  debug: { label: "Debug", icon: Bug, hint: "Root-cause analysis for stack traces" },
  pair: { label: "Pair Programmer", icon: Sparkles, hint: "Explain, refactor, test, and review" },
};

export default function TopBar({
  mode,
  sidebarOpen,
  rightOpen,
  onToggleSidebar,
  onToggleRight,
}: TopBarProps) {
  const meta = MODE_META[mode];
  const Icon = meta.icon;

  return (
    <header className="z-50 flex h-14 shrink-0 items-center justify-between px-4">
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          aria-label={sidebarOpen ? "Hide explorer" : "Show explorer"}
          aria-pressed={sidebarOpen}
          onClick={onToggleSidebar}
          className={`rounded-lg p-2 transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-ide-accent ${
            sidebarOpen
              ? "bg-ide-accent/10 text-ide-accent"
              : "text-ide-muted hover:bg-ide-hover hover:text-ide-text"
          }`}
        >
          <PanelLeft size={18} />
        </button>

        <div className="flex items-center gap-2 text-ide-text">
          <Terminal size={18} className="text-ide-accent" />
          <span className="font-display text-base font-semibold">
            AI Developer Assistant
          </span>
        </div>
      </div>

      {/* Current mode context — a title, not a redundant control set. */}
      <div className="flex min-w-0 items-center gap-2 rounded-full border border-ide-border bg-ide-elevated px-3.5 py-1.5">
        <Icon size={15} className="shrink-0 text-ide-accent" />
        <span className="truncate text-sm font-medium text-ide-text">
          {meta.label}
        </span>
        <span className="hidden truncate text-xs text-ide-muted md:inline">
          · {meta.hint}
        </span>
      </div>

      <div className="flex items-center gap-1">
        <button
          type="button"
          aria-label={rightOpen ? "Hide source & citations" : "Show source & citations"}
          aria-pressed={rightOpen}
          onClick={onToggleRight}
          className={`rounded-lg p-2 transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-ide-accent ${
            rightOpen
              ? "bg-ide-accent/10 text-ide-accent"
              : "text-ide-muted hover:bg-ide-hover hover:text-ide-text"
          }`}
        >
          <PanelRight size={18} />
        </button>
      </div>
    </header>
  );
}
