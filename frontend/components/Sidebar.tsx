"use client";

import { Boxes } from "lucide-react";

import type { RepositoryResponse, ViewerSource } from "@/lib/types";
import CollectionSelector from "./CollectionSelector";
import RepositoryExplorer from "./RepositoryExplorer";

interface SidebarProps {
  collection: string;
  onCollectionChange: (collection: string) => void;
  repositories: RepositoryResponse[];
  selectedRepoId: string | null;
  connecting: boolean;
  connectError: string | null;
  files: ViewerSource[];
  onConnect: (url: string, branch: string | undefined) => void;
  onSelectRepo: (id: string) => void;
  onDeleteRepo: (id: string) => void;
  onOpenFile: (source: ViewerSource) => void;
}

export default function Sidebar({
  collection,
  onCollectionChange,
  repositories,
  selectedRepoId,
  connecting,
  connectError,
  files,
  onConnect,
  onSelectRepo,
  onDeleteRepo,
  onOpenFile,
}: SidebarProps) {
  return (
    <aside
      className="flex h-full w-[288px] flex-col overflow-hidden"
      aria-label="Explorer"
    >
      <div className="flex items-center gap-2 border-b border-ide-border px-4 py-3.5">
        <Boxes size={18} className="text-ide-accent" />
        <div className="min-w-0">
          <p className="font-display truncate text-sm font-semibold text-ide-text">
            Explorer
          </p>
          <p className="truncate text-xs text-ide-muted">Repositories & docs</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <RepositoryExplorer
          repositories={repositories}
          selectedRepoId={selectedRepoId}
          connecting={connecting}
          connectError={connectError}
          files={files}
          onConnect={onConnect}
          onSelect={onSelectRepo}
          onDelete={onDeleteRepo}
          onOpenFile={onOpenFile}
        />
        <div className="my-1 border-t border-ide-border" />
        <CollectionSelector value={collection} onChange={onCollectionChange} />
      </div>
    </aside>
  );
}
