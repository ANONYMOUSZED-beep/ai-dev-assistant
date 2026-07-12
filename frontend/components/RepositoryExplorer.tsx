"use client";

import {
  AlertCircle,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  File,
  Folder,
  FolderOpen,
  GitBranch,
  Loader2,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";

import type { IndexStatus, RepositoryResponse, ViewerSource } from "@/lib/types";

interface RepositoryExplorerProps {
  repositories: RepositoryResponse[];
  selectedRepoId: string | null;
  connecting: boolean;
  connectError: string | null;
  files: ViewerSource[];
  onConnect: (url: string, branch: string | undefined) => void;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onOpenFile: (source: ViewerSource) => void;
}

interface TreeNode {
  name: string;
  path: string;
  children: Map<string, TreeNode>;
  source: ViewerSource | null;
}

function buildTree(files: ViewerSource[]): TreeNode {
  const root: TreeNode = {
    name: "",
    path: "",
    children: new Map(),
    source: null,
  };
  for (const file of files) {
    const path = file.uri ?? file.title;
    const parts = path.split(/[\\/]/).filter(Boolean);
    let node = root;
    parts.forEach((part, i) => {
      let child = node.children.get(part);
      if (!child) {
        child = {
          name: part,
          path: parts.slice(0, i + 1).join("/"),
          children: new Map(),
          source: null,
        };
        node.children.set(part, child);
      }
      node = child;
    });
    node.source = file;
  }
  return root;
}

function StatusBadge({ status }: { status: IndexStatus }) {
  const map: Record<
    IndexStatus,
    { label: string; className: string; icon: React.ReactNode }
  > = {
    pending: {
      label: "Queued",
      className: "text-ide-warning",
      icon: <Loader2 size={11} className="animate-spin" />,
    },
    indexing: {
      label: "Reading…",
      className: "text-ide-accent",
      icon: <Loader2 size={11} className="animate-spin" />,
    },
    ready: {
      label: "Ready",
      className: "text-ide-success",
      icon: <CheckCircle2 size={11} />,
    },
    failed: {
      label: "Failed",
      className: "text-ide-danger",
      icon: <AlertCircle size={11} />,
    },
  };
  const cfg = map[status];
  return (
    <span
      className={`inline-flex items-center gap-1 text-[0.65rem] font-medium ${cfg.className}`}
    >
      {cfg.icon}
      {cfg.label}
    </span>
  );
}

function TreeView({
  node,
  depth,
  onOpenFile,
}: {
  node: TreeNode;
  depth: number;
  onOpenFile: (source: ViewerSource) => void;
}) {
  const entries = useMemo(
    () =>
      Array.from(node.children.values()).sort((a, b) => {
        const aDir = a.children.size > 0;
        const bDir = b.children.size > 0;
        if (aDir !== bDir) return aDir ? -1 : 1;
        return a.name.localeCompare(b.name);
      }),
    [node],
  );

  return (
    <ul role="group" className="list-none">
      {entries.map((child) => (
        <TreeItem
          key={child.path}
          node={child}
          depth={depth}
          onOpenFile={onOpenFile}
        />
      ))}
    </ul>
  );
}

function TreeItem({
  node,
  depth,
  onOpenFile,
}: {
  node: TreeNode;
  depth: number;
  onOpenFile: (source: ViewerSource) => void;
}) {
  const [open, setOpen] = useState(true);
  const isDir = node.children.size > 0;
  const indent = { paddingLeft: `${depth * 12 + 8}px` };

  if (isDir) {
    return (
      <li role="treeitem" aria-selected={false} aria-expanded={open}>
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          style={indent}
          className="flex w-full items-center gap-1 rounded py-1 pr-2 text-left text-xs text-ide-text hover:bg-ide-hover focus:outline-none focus-visible:ring-1 focus-visible:ring-ide-accent"
        >
          {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          {open ? (
            <FolderOpen size={13} className="text-ide-accent" />
          ) : (
            <Folder size={13} className="text-ide-accent" />
          )}
          <span className="truncate">{node.name}</span>
        </button>
        {open ? (
          <TreeView node={node} depth={depth + 1} onOpenFile={onOpenFile} />
        ) : null}
      </li>
    );
  }

  return (
    <li role="treeitem" aria-selected={false}>
      <button
        type="button"
        onClick={() => node.source && onOpenFile(node.source)}
        style={indent}
        className="flex w-full items-center gap-1 rounded py-1 pr-2 text-left text-xs text-ide-muted hover:bg-ide-hover hover:text-ide-text focus:outline-none focus-visible:ring-1 focus-visible:ring-ide-accent"
        title={node.path}
      >
        <span className="w-3" />
        <File size={13} className="shrink-0" />
        <span className="truncate">{node.name}</span>
      </button>
    </li>
  );
}

export default function RepositoryExplorer({
  repositories,
  selectedRepoId,
  connecting,
  connectError,
  files,
  onConnect,
  onSelect,
  onDelete,
  onOpenFile,
}: RepositoryExplorerProps) {
  const [url, setUrl] = useState("");
  const [branch, setBranch] = useState("");
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const tree = useMemo(() => buildTree(files), [files]);
  const selectedRepo = repositories.find((r) => r.id === selectedRepoId) ?? null;

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = url.trim();
    if (!trimmed || connecting) return;
    onConnect(trimmed, branch.trim() || undefined);
    setUrl("");
    setBranch("");
  };

  return (
    <div className="flex flex-col">
      <div className="px-3 py-2">
        <h2 className="mb-1.5 flex items-center gap-1.5 text-[0.7rem] font-semibold uppercase tracking-wide text-ide-muted">
          <GitBranch size={12} />
          Repositories
        </h2>
        <form onSubmit={submit} className="space-y-1.5">
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="github.com/owner/repo or owner/repo"
            aria-label="Repository URL"
            className="w-full rounded-md border border-ide-border bg-ide-bg px-2 py-1.5 text-xs text-ide-text placeholder:text-ide-muted focus:border-ide-accent focus:outline-none"
          />
          <div className="flex gap-1.5">
            <input
              type="text"
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              placeholder="branch (optional)"
              aria-label="Branch"
              className="min-w-0 flex-1 rounded-md border border-ide-border bg-ide-bg px-2 py-1.5 text-xs text-ide-text placeholder:text-ide-muted focus:border-ide-accent focus:outline-none"
            />
            <button
              type="submit"
              disabled={connecting || url.trim().length === 0}
              className="flex shrink-0 items-center gap-1 rounded-md bg-ide-accentMuted px-2.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-ide-accent disabled:cursor-not-allowed disabled:opacity-50"
            >
              {connecting ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <Plus size={13} />
              )}
              Add
            </button>
          </div>
        </form>
        {connectError ? (
          <p className="mt-1.5 text-[0.7rem] text-ide-danger">{connectError}</p>
        ) : null}
      </div>

      <ul className="space-y-1 px-2" aria-label="Connected repositories">
        {repositories.length === 0 ? (
          <li className="px-1 py-1 text-[0.7rem] text-ide-muted">
            No repositories connected yet.
          </li>
        ) : (
          repositories.map((repo) => {
            const active = repo.id === selectedRepoId;
            const name = repo.url.replace(/^https?:\/\/(www\.)?github\.com\//, "");
            return (
              <li key={repo.id} className="group relative">
                <button
                  type="button"
                  onClick={() => onSelect(repo.id)}
                  aria-pressed={active}
                  className={`w-full rounded-md border px-2 py-1.5 text-left transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-ide-accent ${
                    active
                      ? "border-ide-accent/60 bg-ide-accent/10"
                      : "border-ide-border bg-ide-panel hover:bg-ide-hover"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span
                      className="truncate text-xs font-medium text-ide-text"
                      title={repo.url}
                    >
                      {name}
                    </span>
                    <StatusBadge status={repo.status} />
                  </div>
                  <div className="mt-0.5 flex items-center gap-2 text-[0.65rem] text-ide-muted">
                    {repo.branch ? <span>{repo.branch}</span> : null}
                    <span>{repo.files_indexed} files</span>
                    <span>{repo.chunks_indexed} sections</span>
                  </div>
                  {repo.status === "pending" || repo.status === "indexing" ? (
                    <p className="mt-0.5 text-[0.65rem] text-ide-muted">
                      Reading your project — this can take a minute.
                    </p>
                  ) : null}
                  {repo.error ? (
                    <p className="mt-0.5 text-[0.65rem] text-ide-danger">
                      {"We couldn't finish reading this project. Please try again."}
                    </p>
                  ) : null}
                </button>
                {confirmDeleteId === repo.id ? (
                  <div className="absolute bottom-1.5 right-1.5 flex items-center gap-1 rounded-md border border-ide-border bg-ide-panel px-1.5 py-0.5 shadow-sm">
                    <span className="text-[0.6rem] text-ide-muted">Remove?</span>
                    <button
                      type="button"
                      onClick={() => {
                        onDelete(repo.id);
                        setConfirmDeleteId(null);
                      }}
                      aria-label={`Confirm remove ${name}`}
                      className="rounded p-0.5 text-ide-danger hover:bg-ide-hover"
                    >
                      <Check size={12} />
                    </button>
                    <button
                      type="button"
                      onClick={() => setConfirmDeleteId(null)}
                      aria-label="Cancel"
                      className="rounded p-0.5 text-ide-muted hover:bg-ide-hover hover:text-ide-text"
                    >
                      <X size={12} />
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => setConfirmDeleteId(repo.id)}
                    title="Remove repository"
                    aria-label={`Remove ${name}`}
                    className="absolute bottom-1.5 right-1.5 hidden rounded p-1 text-ide-muted transition-colors hover:bg-ide-hover hover:text-ide-danger focus:outline-none focus-visible:ring-1 focus-visible:ring-ide-accent group-hover:block"
                  >
                    <Trash2 size={12} />
                  </button>
                )}
              </li>
            );
          })
        )}
      </ul>

      {selectedRepo && selectedRepo.status === "ready" ? (
        <div className="mt-2 border-t border-ide-border pt-2">
          <h3 className="px-3 pb-1 text-[0.7rem] font-semibold uppercase tracking-wide text-ide-muted">
            Files
          </h3>
          {files.length === 0 ? (
            <p className="px-3 py-1 text-[0.7rem] text-ide-muted">
              Run a code search against this repository to populate discovered
              files here.
            </p>
          ) : (
            <div role="tree" aria-label="Repository files" className="pb-2">
              <TreeView node={tree} depth={0} onOpenFile={onOpenFile} />
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
