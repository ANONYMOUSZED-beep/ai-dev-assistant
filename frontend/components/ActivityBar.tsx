"use client";

import {
  Bug,
  FileText,
  GitBranch,
  type LucideIcon,
  Search,
  Sparkles,
} from "lucide-react";

import type { ChatMode } from "@/lib/types";

interface ActivityBarProps {
  mode: ChatMode;
  onModeChange: (mode: ChatMode) => void;
}

const ITEMS: { id: ChatMode; label: string; icon: LucideIcon }[] = [
  { id: "docs", label: "Docs", icon: FileText },
  { id: "repo", label: "Repo", icon: GitBranch },
  { id: "search", label: "Search", icon: Search },
  { id: "debug", label: "Debug", icon: Bug },
  { id: "pair", label: "Pair", icon: Sparkles },
];

export default function ActivityBar({ mode, onModeChange }: ActivityBarProps) {
  return (
    <nav
      role="tablist"
      aria-label="Assistant mode"
      className="flex h-full w-full flex-col items-center gap-1.5 py-3"
    >
      {ITEMS.map((item) => {
        const Icon = item.icon;
        const active = item.id === mode;
        return (
          <button
            key={item.id}
            role="tab"
            type="button"
            aria-selected={active}
            aria-controls="chat-panel-body"
            title={item.label}
            onClick={() => onModeChange(item.id)}
            className={`group flex w-14 flex-col items-center gap-1 rounded-xl px-1 py-2 transition-all duration-300 focus:outline-none focus-visible:ring-1 focus-visible:ring-ide-accent ${
              active
                ? "bg-ide-accentMuted text-white shadow-[0_6px_16px_rgba(30,50,90,0.25)]"
                : "text-ide-muted hover:bg-ide-hover hover:text-ide-text"
            }`}
          >
            <Icon
              size={20}
              className={`transition-transform duration-300 ${
                active ? "" : "group-hover:scale-110"
              }`}
            />
            <span className="text-[0.62rem] font-medium tracking-wide">
              {item.label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
