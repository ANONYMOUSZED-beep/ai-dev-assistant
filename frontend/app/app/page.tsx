"use client";

import { ListTree } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import ActivityBar from "@/components/ActivityBar";
import AuthGate from "@/components/AuthGate";
import ChatPanel from "@/components/ChatPanel";
import CitationsList from "@/components/CitationsList";
import CodeViewer from "@/components/CodeViewer";
import Sidebar from "@/components/Sidebar";
import TopBar from "@/components/TopBar";
import WelcomeGuide from "@/components/WelcomeGuide";
import { useChat } from "@/hooks/useChat";
import {
  createRepository,
  deleteConversation,
  deleteRepository,
  getConversation,
  listConversations,
  listRepositories,
} from "@/lib/api";
import { citationToSource } from "@/lib/lang";
import { humanizeError } from "@/lib/errors";
import {
  addCustomCollection,
  loadCustomCollections,
  removeCustomCollection,
} from "@/lib/customCollections";
import type {
  ChatMode,
  Citation,
  ConversationSummary,
  DocCollection,
  IndexStatus,
  RepositoryResponse,
  ViewerSource,
} from "@/lib/types";

const TERMINAL: IndexStatus[] = ["ready", "failed"];

function Workspace() {
  const [mode, setMode] = useState<ChatMode>("docs");
  const [collection, setCollection] = useState("python");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);
  // Mobile/tablet (below md) drawer state — independent of the desktop
  // collapse booleans so the drawers start closed and the chat is full-width.
  const [mobileLeftOpen, setMobileLeftOpen] = useState(false);
  const [mobileRightOpen, setMobileRightOpen] = useState(false);

  const isDesktop = useCallback(
    () =>
      typeof window !== "undefined" &&
      window.matchMedia("(min-width: 768px)").matches,
    [],
  );

  // TopBar toggles: collapse in-flow panels on desktop, open drawers on mobile.
  const handleToggleSidebar = useCallback(() => {
    if (isDesktop()) {
      setSidebarOpen((v) => !v);
    } else {
      setMobileLeftOpen((v) => !v);
      setMobileRightOpen(false);
    }
  }, [isDesktop]);

  const handleToggleRight = useCallback(() => {
    if (isDesktop()) {
      setRightOpen((v) => !v);
    } else {
      setMobileRightOpen((v) => !v);
      setMobileLeftOpen(false);
    }
  }, [isDesktop]);

  const closeMobileDrawers = useCallback(() => {
    setMobileLeftOpen(false);
    setMobileRightOpen(false);
  }, []);

  const [repositories, setRepositories] = useState<RepositoryResponse[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);

  const [activeCitations, setActiveCitations] = useState<Citation[]>([]);
  const [activeCitationIndex, setActiveCitationIndex] = useState<number | null>(
    null,
  );
  const [viewerSource, setViewerSource] = useState<ViewerSource | null>(null);
  const [repoFiles, setRepoFiles] = useState<Record<string, ViewerSource[]>>({});

  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [conversationsLoading, setConversationsLoading] = useState(true);

  const [customCollections, setCustomCollections] = useState<DocCollection[]>(
    [],
  );

  const [guideOpen, setGuideOpen] = useState(false);

  // Show the welcome guide on the very first visit (per browser).
  useEffect(() => {
    try {
      if (window.localStorage.getItem("rivr_onboarded") !== "1") {
        setGuideOpen(true);
      }
    } catch {
      /* ignore */
    }
  }, []);

  const dismissGuide = useCallback(() => {
    setGuideOpen(false);
    try {
      window.localStorage.setItem("rivr_onboarded", "1");
    } catch {
      /* ignore */
    }
  }, []);

  // Load persisted custom collections (from previous uploads) on mount.
  useEffect(() => {
    setCustomCollections(loadCustomCollections());
  }, []);

  // After a successful ingest: remember any new collection and make it active.
  const handleIngested = useCallback((ingestedCollection: string) => {
    setCustomCollections(addCustomCollection(ingestedCollection));
    setCollection(ingestedCollection);
  }, []);

  const handleRemoveCustomCollection = useCallback(
    (id: string) => {
      setCustomCollections(removeCustomCollection(id));
      setCollection((cur) => (cur === id ? "python" : cur));
    },
    [],
  );

  // Refs to read current values inside stable callbacks without stale closures.
  const modeRef = useRef(mode);
  const selectedRepoIdRef = useRef(selectedRepoId);
  const repositoriesRef = useRef(repositories);
  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);
  useEffect(() => {
    selectedRepoIdRef.current = selectedRepoId;
  }, [selectedRepoId]);
  useEffect(() => {
    repositoriesRef.current = repositories;
  }, [repositories]);

  const handleCitations = useCallback((citations: Citation[]) => {
    setActiveCitations(citations);
    setActiveCitationIndex(null);

    const repoId = selectedRepoIdRef.current;
    if (modeRef.current === "search" && repoId) {
      const sources = citations
        .filter((c) => c.source_type === "code")
        .map(citationToSource);
      if (sources.length > 0) {
        setRepoFiles((prev) => {
          const existing = prev[repoId] ?? [];
          const byUri = new Map<string, ViewerSource>();
          for (const s of existing) byUri.set(s.uri ?? s.title, s);
          for (const s of sources) byUri.set(s.uri ?? s.title, s);
          return { ...prev, [repoId]: Array.from(byUri.values()) };
        });
      }
    }
  }, []);

  const refreshConversations = useCallback(async () => {
    try {
      const list = await listConversations();
      setConversations(list);
    } catch {
      // Backend may be unavailable; keep the current list.
    } finally {
      setConversationsLoading(false);
    }
  }, []);

  const chat = useChat({
    onCitations: handleCitations,
    onTurnPersisted: () => {
      void refreshConversations();
    },
  });

  // Load chat history on mount.
  useEffect(() => {
    void refreshConversations();
  }, [refreshConversations]);

  // Switching mode starts a fresh conversation for that surface.
  const handleModeChange = useCallback(
    (next: ChatMode) => {
      setMode(next);
      chat.newChat();
    },
    [chat],
  );

  const handleSelectConversation = useCallback(
    async (summary: ConversationSummary) => {
      try {
        const detail = await getConversation(summary.id);
        setMode(summary.kind as ChatMode);
        if (summary.kind === "repo" && summary.repository_id) {
          setSelectedRepoId(summary.repository_id);
        }
        chat.loadConversation(detail);
      } catch {
        // Ignore load failures; the conversation may have been deleted.
      }
    },
    [chat],
  );

  const handleDeleteConversation = useCallback(
    async (id: string) => {
      try {
        await deleteConversation(id);
      } catch {
        return;
      }
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (chat.conversationId === id) chat.newChat();
    },
    [chat],
  );

  const refreshRepositories = useCallback(async () => {
    try {
      const repos = await listRepositories();
      setRepositories(repos);
    } catch {
      // Backend may be unavailable; keep the current list.
    }
  }, []);

  // Initial load + polling while any repository is still indexing.
  useEffect(() => {
    void refreshRepositories();
    const interval = setInterval(() => {
      const pending = repositoriesRef.current.some(
        (r) => !TERMINAL.includes(r.status),
      );
      if (pending) void refreshRepositories();
    }, 4000);
    return () => clearInterval(interval);
  }, [refreshRepositories]);

  const handleConnect = useCallback(
    async (url: string, branch: string | undefined) => {
      setConnecting(true);
      setConnectError(null);
      try {
        const repo = await createRepository({ url, branch: branch ?? null });
        setRepositories((prev) => {
          const without = prev.filter((r) => r.id !== repo.id);
          return [repo, ...without];
        });
        setSelectedRepoId(repo.id);
        if (!TERMINAL.includes(repo.status)) {
          void refreshRepositories();
        }
      } catch (err) {
        setConnectError(humanizeError(err));
      } finally {
        setConnecting(false);
      }
    },
    [refreshRepositories],
  );

  const handleSelectCitation = useCallback(
    (citation: Citation) => {
      setViewerSource(citationToSource(citation));
      setActiveCitationIndex(citation.index);
      setRightOpen(true);
      if (!isDesktop()) {
        setMobileRightOpen(true);
        setMobileLeftOpen(false);
      }
    },
    [isDesktop],
  );

  const handleDeleteRepo = useCallback(async (id: string) => {
    try {
      await deleteRepository(id);
    } catch {
      // If the delete failed (e.g. DB down) leave the list as-is.
      return;
    }
    setRepositories((prev) => prev.filter((r) => r.id !== id));
    setSelectedRepoId((cur) => (cur === id ? null : cur));
  }, []);

  const handleOpenFile = useCallback(
    (source: ViewerSource) => {
      setViewerSource(source);
      setRightOpen(true);
      if (!isDesktop()) {
        setMobileRightOpen(true);
        setMobileLeftOpen(false);
      }
    },
    [isDesktop],
  );

  const files = useMemo(
    () => (selectedRepoId ? repoFiles[selectedRepoId] ?? [] : []),
    [repoFiles, selectedRepoId],
  );

  // Shared Explorer content — rendered in the in-flow desktop panel and in the
  // mobile slide-over drawer.
  const sidebarNode = (
    <Sidebar
      collection={collection}
      onCollectionChange={setCollection}
      customCollections={customCollections}
      onIngested={handleIngested}
      onRemoveCustomCollection={handleRemoveCustomCollection}
      repositories={repositories}
      selectedRepoId={selectedRepoId}
      connecting={connecting}
      connectError={connectError}
      files={files}
      onConnect={handleConnect}
      onSelectRepo={setSelectedRepoId}
      onDeleteRepo={handleDeleteRepo}
      onOpenFile={handleOpenFile}
      conversations={conversations}
      activeConversationId={chat.conversationId}
      conversationsLoading={conversationsLoading}
      onSelectConversation={handleSelectConversation}
      onNewChat={chat.newChat}
      onDeleteConversation={handleDeleteConversation}
    />
  );

  // Shared source-viewer + citations content.
  const rightPanelInner = (
    <>
      <div className="min-h-0 flex-[3] border-b border-ide-border">
        <CodeViewer source={viewerSource} />
      </div>
      <div className="flex min-h-0 flex-[2] flex-col">
        <div className="flex items-center gap-2 border-b border-ide-border px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-ide-muted">
          <ListTree size={14} className="text-ide-accent" />
          Citations
          {activeCitations.length > 0 ? (
            <span className="ml-auto rounded-full bg-ide-accent/10 px-2 py-0.5 font-mono text-[0.7rem] normal-case text-ide-accent">
              {activeCitations.length}
            </span>
          ) : null}
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto">
          <CitationsList
            citations={activeCitations}
            activeIndex={activeCitationIndex}
            onSelect={handleSelectCitation}
          />
        </div>
      </div>
    </>
  );

  const anyDrawerOpen = mobileLeftOpen || mobileRightOpen;

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-ide-bg">
      <WelcomeGuide
        open={guideOpen}
        onClose={dismissGuide}
        onPick={(pickedMode) => {
          handleModeChange(pickedMode);
          dismissGuide();
        }}
      />

      <TopBar
        mode={mode}
        sidebarOpen={sidebarOpen}
        rightOpen={rightOpen}
        onToggleSidebar={handleToggleSidebar}
        onToggleRight={handleToggleRight}
        onOpenGuide={() => setGuideOpen(true)}
      />

      <div className="app-grid flex min-h-0 flex-1 gap-3 px-3 pb-3">
        {/* Mode rail */}
        <div className="panel-card flex w-16 shrink-0 overflow-hidden">
          <ActivityBar mode={mode} onModeChange={handleModeChange} />
        </div>

        {/* Explorer (collapsible on desktop; a drawer below md) */}
        <div
          className={`panel-collapse hidden shrink-0 overflow-hidden md:block ${
            sidebarOpen ? "md:w-[288px] md:opacity-100" : "md:w-0 md:opacity-0"
          }`}
        >
          <div className="panel-card h-full w-[288px] overflow-hidden">
            {sidebarNode}
          </div>
        </div>

        {/* Conversation */}
        <div className="panel-card flex min-w-0 flex-1 overflow-hidden">
          <ChatPanel
            mode={mode}
            messages={chat.messages}
            isBusy={chat.isBusy}
            collection={collection}
            repositories={repositories}
            selectedRepoId={selectedRepoId}
            onSelectCitation={handleSelectCitation}
            onStop={chat.stop}
            onClear={chat.clear}
            onSendDocs={chat.sendDocs}
            onSendRepo={chat.sendRepo}
            onSendSearch={chat.sendSearch}
            onSendDebug={chat.sendDebug}
            onSendPair={chat.sendPair}
          />
        </div>

        {/* Source viewer + citations (collapsible on desktop; a drawer below md) */}
        <div
          className={`panel-collapse hidden shrink-0 overflow-hidden md:block ${
            rightOpen ? "md:w-[420px] md:opacity-100" : "md:w-0 md:opacity-0"
          }`}
        >
          <aside
            className="panel-card flex h-full w-[420px] flex-col overflow-hidden"
            aria-label="Source viewer and citations"
          >
            {rightPanelInner}
          </aside>
        </div>
      </div>

      {/* ── Mobile / tablet drawers (below md only) ───────────────────── */}
      {/* Backdrop: tap to dismiss the open drawer. */}
      <div
        onClick={closeMobileDrawers}
        aria-hidden={!anyDrawerOpen}
        className={`fixed inset-0 top-14 z-40 bg-black/50 transition-opacity duration-300 md:hidden ${
          anyDrawerOpen
            ? "opacity-100"
            : "pointer-events-none opacity-0"
        }`}
      />

      {/* Left Explorer drawer — slides in from the left, past the mode rail. */}
      <div
        role="dialog"
        aria-label="Explorer"
        aria-hidden={!mobileLeftOpen}
        className={`fixed bottom-2 left-16 top-16 z-50 w-[288px] max-w-[80vw] transition-transform duration-300 ease-out md:hidden ${
          mobileLeftOpen ? "translate-x-0" : "-translate-x-[130%]"
        }`}
      >
        <div className="panel-card h-full w-full overflow-hidden">
          {sidebarNode}
        </div>
      </div>

      {/* Right source/citations drawer — slides in from the right. */}
      <div
        role="dialog"
        aria-label="Source viewer and citations"
        aria-hidden={!mobileRightOpen}
        className={`fixed bottom-2 right-2 top-16 z-50 w-[420px] max-w-[92vw] transition-transform duration-300 ease-out md:hidden ${
          mobileRightOpen ? "translate-x-0" : "translate-x-[130%]"
        }`}
      >
        <aside
          className="panel-card flex h-full w-full flex-col overflow-hidden"
          aria-label="Source viewer and citations"
        >
          {rightPanelInner}
        </aside>
      </div>
    </div>
  );
}

export default function AppPage() {
  return (
    <AuthGate>
      <Workspace />
    </AuthGate>
  );
}
