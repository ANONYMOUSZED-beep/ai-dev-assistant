"use client";

import Editor, { type OnMount } from "@monaco-editor/react";
import type { editor } from "monaco-editor";
import { FileCode2 } from "lucide-react";
import { useCallback, useRef } from "react";

import type { ViewerSource } from "@/lib/types";
import SplineRobot from "./SplineRobot";

interface CodeViewerProps {
  source: ViewerSource | null;
}

export default function CodeViewer({ source }: CodeViewerProps) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const decorationsRef = useRef<string[]>([]);

  const applyHighlight = useCallback(
    (ed: editor.IStandaloneCodeEditor, monaco: Parameters<OnMount>[1]) => {
      // The snippet content is standalone, so highlight relative to its own
      // first line (line 1) through the end of the snippet.
      const model = ed.getModel();
      if (!model) return;
      const totalLines = model.getLineCount();
      const start = 1;
      const end = totalLines;

      decorationsRef.current = ed.deltaDecorations(decorationsRef.current, [
        {
          range: new monaco.Range(start, 1, end, 1),
          options: {
            isWholeLine: true,
            className: "bg-ide-accent/10",
            linesDecorationsClassName: "border-l-2 border-ide-accent",
          },
        },
      ]);
      ed.revealLineNearTop(start);
    },
    [],
  );

  const handleMount: OnMount = useCallback(
    (ed, monaco) => {
      editorRef.current = ed;
      if (source) applyHighlight(ed, monaco);
    },
    [applyHighlight, source],
  );

  if (!source) {
    return (
      <div className="relative flex h-full flex-col overflow-hidden">
        <div className="min-h-0 flex-1">
          <SplineRobot />
        </div>
        <div className="pointer-events-none absolute inset-x-0 bottom-0 flex flex-col items-center gap-1 bg-gradient-to-t from-ide-panel via-ide-panel/80 to-transparent px-6 pb-5 pt-10 text-center">
          <p className="font-display text-sm font-semibold text-ide-text">
            Your sources appear here
          </p>
          <p className="text-xs text-ide-muted">
            Click a citation chip in an answer to view its source.
          </p>
        </div>
      </div>
    );
  }

  const lineInfo =
    source.startLine != null
      ? `Lines ${source.startLine}${
          source.endLine != null ? `–${source.endLine}` : ""
        }`
      : source.language;

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-ide-border bg-ide-panel px-3 py-2">
        <FileCode2 size={14} className="shrink-0 text-ide-accent" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-medium text-ide-text" title={source.title}>
            {source.title}
          </p>
          {source.uri ? (
            <p className="truncate text-[0.7rem] text-ide-muted" title={source.uri}>
              {source.uri}
            </p>
          ) : null}
        </div>
        <span className="shrink-0 rounded bg-ide-elevated px-1.5 py-0.5 text-[0.7rem] text-ide-muted">
          {lineInfo}
        </span>
      </div>
      <div className="min-h-0 flex-1">
        <Editor
          key={`${source.uri ?? source.title}-${source.startLine ?? 0}`}
          height="100%"
          theme="light"
          language={source.language}
          value={source.content}
          onMount={handleMount}
          options={{
            readOnly: true,
            domReadOnly: true,
            minimap: { enabled: false },
            fontSize: 12,
            lineNumbers: "on",
            scrollBeyondLastLine: false,
            wordWrap: "on",
            renderLineHighlight: "none",
            automaticLayout: true,
            scrollbar: { verticalScrollbarSize: 10, horizontalScrollbarSize: 10 },
            padding: { top: 8, bottom: 8 },
          }}
          loading={
            <div className="flex h-full items-center justify-center text-xs text-ide-muted">
              Loading editor…
            </div>
          }
        />
      </div>
    </div>
  );
}
