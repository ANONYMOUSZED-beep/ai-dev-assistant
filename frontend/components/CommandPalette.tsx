"use client";

import {
  Book,
  Bug,
  FileText,
  GitBranch,
  HelpCircle,
  MessageSquarePlus,
  MessagesSquare,
  Search,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import type {
  ChatMode,
  ConversationSummary,
  DocCollection,
  RepositoryResponse,
} from "@/lib/types";

interface CommandPaletteProps {
  mode: ChatMode;
  onModeChange: (mode: ChatMode) => void;
  collections: DocCollection[];
  onSelectCollection: (id: string) => void;
  repositories: RepositoryResponse[];
  onSelectRepo: (id: string) => void;
  conversations: ConversationSummary[];
  onSelectConversation: (summary: ConversationSummary) => void;
  onNewChat: () => void;
  onOpenGuide: () => void;
}

// A single runnable entry in the palette. `group` labels the section it belongs
// to and `run` performs the action (the palette closes right after).
interface Command {
  id: string;
  label: string;
  group: string;
  icon: LucideIcon;
  run: () => void;
}

const MODES: { id: ChatMode; label: string; icon: LucideIcon }[] = [
  { id: "docs", label: "Docs", icon: FileText },
  { id: "repo", label: "Repo", icon: GitBranch },
  { id: "search", label: "Search", icon: Search },
  { id: "debug", label: "Debug", icon: Bug },
  { id: "pair", label: "Pair", icon: Sparkles },
];

export default function CommandPalette({
  mode,
  onModeChange,
  collections,
  onSelectCollection,
  repositories,
  onSelectRepo,
  conversations,
  onSelectConversation,
  onNewChat,
  onOpenGuide,
}: CommandPaletteProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [highlight, setHighlight] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const close = useCallback(() => {
    setOpen(false);
    setQuery("");
    setHighlight(0);
  }, []);

  // Global shortcut: Cmd+K (mac) / Ctrl+K (win) toggles the palette.
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  // Focus the input whenever the palette opens.
  useEffect(() => {
    if (open) {
      // Defer to ensure the input is mounted before focusing.
      const id = window.setTimeout(() => inputRef.current?.focus(), 0);
      return () => window.clearTimeout(id);
    }
  }, [open]);

  // Build the full command set from the current props.
  const commands = useMemo<Command[]>(() => {
    const list: Command[] = [];

    for (const m of MODES) {
      list.push({
        id: `mode:${m.id}`,
        label: `Switch mode: ${m.label}`,
        group: "Modes",
        icon: m.icon,
        run: () => onModeChange(m.id),
      });
    }

    for (const c of collections) {
      list.push({
        id: `collection:${c.id}`,
        label: `Knowledge base: ${c.label}`,
        group: "Knowledge bases",
        icon: Book,
        run: () => onSelectCollection(c.id),
      });
    }

    for (const r of repositories) {
      if (r.status !== "ready") continue;
      list.push({
        id: `repo:${r.id}`,
        label: `Repository: ${r.url}`,
        group: "Repositories",
        icon: GitBranch,
        run: () => onSelectRepo(r.id),
      });
    }

    for (const conv of conversations) {
      list.push({
        id: `conversation:${conv.id}`,
        label: `Open chat: ${conv.title ?? "Untitled conversation"}`,
        group: "Recent conversations",
        icon: MessagesSquare,
        run: () => onSelectConversation(conv),
      });
    }

    list.push({
      id: "action:new-chat",
      label: "New chat",
      group: "Actions",
      icon: MessageSquarePlus,
      run: onNewChat,
    });
    list.push({
      id: "action:help",
      label: "Show help guide",
      group: "Actions",
      icon: HelpCircle,
      run: onOpenGuide,
    });

    return list;
  }, [
    collections,
    conversations,
    onModeChange,
    onNewChat,
    onOpenGuide,
    onSelectCollection,
    onSelectConversation,
    onSelectRepo,
    repositories,
  ]);

  // Case-insensitive substring filter across labels.
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return commands;
    return commands.filter((c) => c.label.toLowerCase().includes(q));
  }, [commands, query]);

  // Keep the highlighted index within the (possibly shrunk) filtered list.
  useEffect(() => {
    setHighlight((h) => {
      if (filtered.length === 0) return 0;
      return Math.min(h, filtered.length - 1);
    });
  }, [filtered.length]);

  const runAt = useCallback(
    (index: number) => {
      const cmd = filtered[index];
      if (!cmd) return;
      cmd.run();
      close();
    },
    [filtered, close],
  );

  const onInputKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Escape") {
        e.preventDefault();
        close();
        return;
      }
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setHighlight((h) => (filtered.length ? (h + 1) % filtered.length : 0));
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setHighlight((h) =>
          filtered.length ? (h - 1 + filtered.length) % filtered.length : 0,
        );
        return;
      }
      if (e.key === "Enter") {
        e.preventDefault();
        runAt(highlight);
      }
    },
    [filtered.length, highlight, runAt, close],
  );

  // Scroll the highlighted row into view as the selection moves.
  useEffect(() => {
    if (!open) return;
    const container = listRef.current;
    const active = container?.querySelector<HTMLElement>(
      `[data-index="${highlight}"]`,
    );
    active?.scrollIntoView({ block: "nearest" });
  }, [highlight, open]);

  if (!open) return null;

  // Track a running row index so highlighting works across grouped sections.
  let rowIndex = -1;
  let lastGroup: string | null = null;

  return (
    <div
      className="fixed inset-0 z-[130] flex items-start justify-center bg-black/60 p-4 pt-[12vh] backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
      onClick={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      <div className="flex max-h-[70vh] w-full max-w-xl flex-col overflow-hidden rounded-2xl border border-ide-border bg-ide-panel shadow-2xl">
        <div className="flex items-center gap-2.5 border-b border-ide-border px-4 py-3">
          <Search size={16} className="shrink-0 text-ide-muted" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setHighlight(0);
            }}
            onKeyDown={onInputKeyDown}
            placeholder="Type a command or search..."
            aria-label="Search commands"
            className="flex-1 bg-transparent text-sm text-ide-text placeholder:text-ide-muted focus:outline-none"
          />
          <kbd className="hidden shrink-0 rounded border border-ide-border bg-ide-bg px-1.5 py-0.5 font-mono text-[0.65rem] text-ide-muted sm:inline">
            Esc
          </kbd>
        </div>

        <div ref={listRef} className="min-h-0 flex-1 overflow-y-auto py-1.5">
          {filtered.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-ide-muted">
              No matching commands
            </div>
          ) : (
            filtered.map((cmd) => {
              rowIndex += 1;
              const index = rowIndex;
              const Icon = cmd.icon;
              const isActive = index === highlight;
              const showGroup = cmd.group !== lastGroup;
              lastGroup = cmd.group;
              const isCurrentMode = cmd.id === `mode:${mode}`;
              return (
                <div key={cmd.id}>
                  {showGroup ? (
                    <div className="px-4 pb-1 pt-2 text-[0.65rem] font-semibold uppercase tracking-wide text-ide-muted">
                      {cmd.group}
                    </div>
                  ) : null}
                  <button
                    type="button"
                    data-index={index}
                    onMouseEnter={() => setHighlight(index)}
                    onClick={() => runAt(index)}
                    className={`flex w-full items-center gap-3 px-4 py-2 text-left text-sm transition-colors ${
                      isActive
                        ? "bg-ide-accent/10 text-ide-text"
                        : "text-ide-muted hover:bg-ide-hover hover:text-ide-text"
                    }`}
                  >
                    <Icon
                      size={16}
                      className={`shrink-0 ${
                        isActive ? "text-ide-accent" : ""
                      }`}
                    />
                    <span className="min-w-0 flex-1 truncate">{cmd.label}</span>
                    {isCurrentMode ? (
                      <span className="shrink-0 rounded-full bg-ide-accent/10 px-2 py-0.5 text-[0.65rem] font-medium text-ide-accent">
                        current
                      </span>
                    ) : null}
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
