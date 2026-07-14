// TypeScript types mirroring the FastAPI backend schemas.

export type SourceType =
  | "pdf"
  | "markdown"
  | "html"
  | "docx"
  | "txt"
  | "code"
  | "github"
  | "web";

export interface Citation {
  index: number;
  title: string;
  source_type: SourceType;
  uri: string | null;
  snippet: string;
  start_line: number | null;
  end_line: number | null;
  score: number | null;
}

export interface Answer {
  text: string;
  citations: Citation[];
  model: string | null;
  provider: string | null;
  conversation_id: string | null;
  follow_ups?: string[];
}

export interface ChatRequest {
  question: string;
  collection: string;
  conversation_id?: string | null;
  stream?: boolean;
}

export interface IngestRequest {
  collection: string;
  uri?: string | null;
  source_type?: SourceType | null;
  text?: string | null;
  title?: string | null;
}

export interface IngestResponse {
  document_id: string;
  collection: string;
  chunks_indexed: number;
}

export type IndexStatus = "pending" | "indexing" | "ready" | "failed";

export interface RepositoryResponse {
  id: string;
  url: string;
  branch: string | null;
  status: IndexStatus;
  files_indexed: number;
  chunks_indexed: number;
  error: string | null;
}

export interface RepositoryCreateRequest {
  url: string;
  branch?: string | null;
}

export interface RepoChatRequest {
  question: string;
  conversation_id?: string | null;
  stream?: boolean;
}

export interface CodeSearchRequest {
  query: string;
  repository_id?: string | null;
  top_k: number;
}

export interface CodeSearchHit {
  path: string;
  snippet: string;
  start_line: number | null;
  end_line: number | null;
  score: number;
  symbol: string | null;
}

export interface CodeSearchResponse {
  query: string;
  hits: CodeSearchHit[];
}

export interface DebugRequest {
  error: string;
  language?: string | null;
  code_context?: string | null;
  repository_id?: string | null;
}

export type PairAction =
  | "explain"
  | "refactor"
  | "test"
  | "document"
  | "optimize"
  | "security";

export interface PairRequest {
  action: PairAction;
  code: string;
  language?: string | null;
  instructions?: string | null;
}

// ── UI domain models ──────────────────────────────────────────────

export type ChatMode = "docs" | "repo" | "search" | "debug" | "pair";

// Persisted chat history. `kind` drives the type badge in the sidebar.
export type ConversationKind = "docs" | "repo" | "debug" | "pair";

export interface ConversationSummary {
  id: string;
  kind: ConversationKind;
  title: string | null;
  collection: string | null;
  repository_id: string | null;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface StoredMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  created_at: string;
}

export interface ConversationDetail extends ConversationSummary {
  messages: StoredMessage[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  model?: string | null;
  provider?: string | null;
  pending?: boolean;
  error?: boolean;
  followUps?: string[];
  confidence?: number | null;
  previousContent?: string;
}

export interface DocCollection {
  id: string;
  label: string;
}

// A source rendered in the right-hand code/source viewer.
export interface ViewerSource {
  title: string;
  uri: string | null;
  language: string;
  content: string;
  startLine: number | null;
  endLine: number | null;
}
