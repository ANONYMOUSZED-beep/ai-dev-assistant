"use client";

import { useEffect, useRef, useState } from "react";

// mermaid is heavy and browser-only; load it lazily once and share the promise
// across every diagram so it stays out of the initial bundle.
let mermaidPromise: Promise<typeof import("mermaid").default> | null = null;
function loadMermaid() {
  if (!mermaidPromise) {
    mermaidPromise = import("mermaid").then((m) => m.default);
  }
  return mermaidPromise;
}

let seq = 0;

interface MermaidDiagramProps {
  code: string;
}

/**
 * Renders a mermaid source string as an inline SVG diagram. The source comes
 * from LLM output, so rendering runs with mermaid's "strict" securityLevel
 * (which sanitises the SVG) and any parse failure falls back to showing the
 * raw code rather than throwing.
 */
export default function MermaidDiagram({ code }: MermaidDiagramProps) {
  const [svg, setSvg] = useState<string | null>(null);
  const idRef = useRef(`mermaid-${(seq += 1)}`);

  useEffect(() => {
    let cancelled = false;

    const render = async () => {
      const source = code.trim();
      if (!source) {
        setSvg(null);
        return;
      }
      try {
        const mermaid = await loadMermaid();
        mermaid.initialize({
          startOnLoad: false,
          securityLevel: "strict",
          theme: document.documentElement.classList.contains("dark")
            ? "dark"
            : "default",
        });
        await mermaid.parse(source);
        const rendered = await mermaid.render(idRef.current, source);
        if (!cancelled) setSvg(rendered.svg);
      } catch {
        if (!cancelled) setSvg(null);
      }
    };

    void render();

    // Re-render when the user toggles light/dark (the theme is a `.dark` class
    // on <html>, not React state, so observe the class attribute directly).
    const observer = new MutationObserver(() => void render());
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });

    return () => {
      cancelled = true;
      observer.disconnect();
    };
  }, [code]);

  if (svg === null) {
    return (
      <pre className="overflow-x-auto rounded-lg border border-ide-border bg-ide-elevated p-3 text-xs text-ide-text">
        <code>{code}</code>
      </pre>
    );
  }

  return (
    <div
      className="my-2 flex justify-center overflow-x-auto rounded-lg border border-ide-border bg-ide-panel p-3"
      role="img"
      aria-label="Diagram"
      // Safe: mermaid renders with securityLevel "strict", which sanitises the SVG.
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
