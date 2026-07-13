"use client";

import {
  Bug,
  ChevronDown,
  Download,
  FileText,
  GitBranch,
  HelpCircle,
  LogOut,
  type LucideIcon,
  PanelLeft,
  PanelRight,
  Search,
  Sparkles,
  Terminal,
  Trash2,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/AuthGate";
import { deleteAccount, exportMyData } from "@/lib/api";
import { humanizeError } from "@/lib/errors";
import type { ChatMode } from "@/lib/types";

interface TopBarProps {
  mode: ChatMode;
  sidebarOpen: boolean;
  rightOpen: boolean;
  onToggleSidebar: () => void;
  onToggleRight: () => void;
  onOpenGuide: () => void;
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
  onOpenGuide,
}: TopBarProps) {
  const meta = MODE_META[mode];
  const Icon = meta.icon;
  const { user, logout } = useAuth();

  return (
    <header className="z-50 flex h-14 shrink-0 items-center justify-between px-4">
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          aria-label={sidebarOpen ? "Hide explorer" : "Show explorer"}
          aria-pressed={sidebarOpen}
          onClick={onToggleSidebar}
          className={`rounded-lg p-2.5 transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-ide-accent md:p-2 ${
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
          aria-label="How to use this app"
          title="How to use this app"
          onClick={onOpenGuide}
          className="rounded-lg p-2 text-ide-muted transition-colors hover:bg-ide-hover hover:text-ide-text focus:outline-none focus-visible:ring-1 focus-visible:ring-ide-accent"
        >
          <HelpCircle size={18} />
        </button>
        <button
          type="button"
          aria-label={rightOpen ? "Hide source & citations" : "Show source & citations"}
          aria-pressed={rightOpen}
          onClick={onToggleRight}
          className={`rounded-lg p-2.5 transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-ide-accent md:p-2 ${
            rightOpen
              ? "bg-ide-accent/10 text-ide-accent"
              : "text-ide-muted hover:bg-ide-hover hover:text-ide-text"
          }`}
        >
          <PanelRight size={18} />
        </button>

        {user ? <AccountMenu username={user.username} onLogout={logout} /> : null}
      </div>
    </header>
  );
}

function AccountMenu({
  username,
  onLogout,
}: {
  username: string;
  onLogout: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
        setConfirmDelete(false);
        setError(null);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const handleExport = async () => {
    setBusy(true);
    setError(null);
    try {
      const data = await exportMyData();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "ai-developer-assistant-data.json";
      a.click();
      URL.revokeObjectURL(url);
      setOpen(false);
    } catch (err) {
      setError(humanizeError(err));
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async () => {
    setBusy(true);
    setError(null);
    try {
      await deleteAccount();
      onLogout();
    } catch (err) {
      setError(humanizeError(err));
      setBusy(false);
    }
  };

  return (
    <div className="relative ml-1 border-l border-ide-border pl-2" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Account menu"
        className="flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs text-ide-muted transition-colors hover:bg-ide-hover hover:text-ide-text focus:outline-none focus-visible:ring-1 focus-visible:ring-ide-accent"
      >
        <span className="max-w-[10rem] truncate" title={username}>
          {username}
        </span>
        <ChevronDown size={13} aria-hidden="true" />
      </button>

      {open ? (
        <div
          role="menu"
          className="absolute right-0 top-full z-50 mt-1 w-56 overflow-hidden rounded-lg border border-ide-border bg-ide-panel py-1 shadow-xl"
        >
          <button
            type="button"
            role="menuitem"
            onClick={handleExport}
            disabled={busy}
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-ide-text hover:bg-ide-hover disabled:opacity-50"
          >
            <Download size={14} aria-hidden="true" /> Export my data
          </button>
          <button
            type="button"
            role="menuitem"
            onClick={onLogout}
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-ide-text hover:bg-ide-hover"
          >
            <LogOut size={14} aria-hidden="true" /> Sign out
          </button>

          <div className="my-1 border-t border-ide-border" />

          {confirmDelete ? (
            <div className="px-3 py-2">
              <p className="mb-1.5 text-[0.7rem] text-ide-muted">
                {"This permanently deletes your account and all data."}
              </p>
              <div className="flex gap-1.5">
                <button
                  type="button"
                  onClick={handleDelete}
                  disabled={busy}
                  className="flex-1 rounded-md bg-ide-danger px-2 py-1 text-[0.7rem] font-medium text-white hover:opacity-90 disabled:opacity-50"
                >
                  {busy ? "Deleting…" : "Delete forever"}
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmDelete(false)}
                  className="rounded-md border border-ide-border px-2 py-1 text-[0.7rem] text-ide-muted hover:bg-ide-hover"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              role="menuitem"
              onClick={() => setConfirmDelete(true)}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-ide-danger hover:bg-ide-danger/10"
            >
              <Trash2 size={14} aria-hidden="true" /> Delete account
            </button>
          )}

          {error ? (
            <p className="px-3 py-1.5 text-[0.7rem] text-ide-danger">{error}</p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
