import type { Citation, SourceType, ViewerSource } from "./types";

const EXT_LANGUAGE: Record<string, string> = {
  ts: "typescript",
  tsx: "typescript",
  js: "javascript",
  jsx: "javascript",
  py: "python",
  rb: "ruby",
  go: "go",
  rs: "rust",
  java: "java",
  kt: "kotlin",
  c: "c",
  h: "c",
  cpp: "cpp",
  cc: "cpp",
  hpp: "cpp",
  cs: "csharp",
  php: "php",
  swift: "swift",
  scala: "scala",
  sh: "shell",
  bash: "shell",
  zsh: "shell",
  yml: "yaml",
  yaml: "yaml",
  json: "json",
  toml: "ini",
  ini: "ini",
  md: "markdown",
  markdown: "markdown",
  html: "html",
  htm: "html",
  css: "css",
  scss: "scss",
  sql: "sql",
  dockerfile: "dockerfile",
  tf: "hcl",
  proto: "protobuf",
};

const SOURCE_TYPE_LANGUAGE: Partial<Record<SourceType, string>> = {
  markdown: "markdown",
  html: "html",
  code: "typescript",
  github: "typescript",
};

/** Best-effort Monaco language id from a file path or URI. */
export function languageFromPath(path: string | null | undefined): string {
  if (!path) return "plaintext";
  const clean = path.split(/[?#]/)[0] ?? path;
  const base = clean.split(/[\\/]/).pop() ?? clean;
  if (base.toLowerCase() === "dockerfile") return "dockerfile";
  const dot = base.lastIndexOf(".");
  if (dot === -1) return "plaintext";
  const ext = base.slice(dot + 1).toLowerCase();
  return EXT_LANGUAGE[ext] ?? "plaintext";
}

/** Resolve a Monaco language from a path, falling back to source type. */
export function languageFor(
  path: string | null | undefined,
  sourceType?: SourceType | null,
): string {
  const fromPath = languageFromPath(path);
  if (fromPath !== "plaintext") return fromPath;
  if (sourceType && SOURCE_TYPE_LANGUAGE[sourceType]) {
    return SOURCE_TYPE_LANGUAGE[sourceType] as string;
  }
  return "plaintext";
}

/** Build a viewer source from a citation. */
export function citationToSource(citation: Citation): ViewerSource {
  return {
    title: citation.title || citation.uri || `Source ${citation.index}`,
    uri: citation.uri,
    language: languageFor(citation.uri, citation.source_type),
    content: citation.snippet ?? "",
    startLine: citation.start_line,
    endLine: citation.end_line,
  };
}
