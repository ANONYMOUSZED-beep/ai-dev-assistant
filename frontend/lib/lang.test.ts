import { describe, expect, it } from "vitest";

import { citationToSource, languageFor, languageFromPath } from "./lang";
import type { Citation } from "./types";

describe("languageFromPath", () => {
  it("maps common extensions to Monaco language ids", () => {
    expect(languageFromPath("src/app/main.py")).toBe("python");
    expect(languageFromPath("component.tsx")).toBe("typescript");
    expect(languageFromPath("styles.css")).toBe("css");
    expect(languageFromPath("data.json")).toBe("json");
  });

  it("recognises Dockerfile by name", () => {
    expect(languageFromPath("path/to/Dockerfile")).toBe("dockerfile");
  });

  it("strips query strings and hashes before extracting the extension", () => {
    expect(languageFromPath("https://x.com/a/b.ts?ref=1#L3")).toBe("typescript");
  });

  it("falls back to plaintext for unknown or missing paths", () => {
    expect(languageFromPath("README")).toBe("plaintext");
    expect(languageFromPath(null)).toBe("plaintext");
    expect(languageFromPath(undefined)).toBe("plaintext");
  });
});

describe("languageFor", () => {
  it("prefers the path-derived language", () => {
    expect(languageFor("a.py", "markdown")).toBe("python");
  });

  it("falls back to the source type when the path is unhelpful", () => {
    expect(languageFor("noext", "markdown")).toBe("markdown");
    expect(languageFor(null, "code")).toBe("typescript");
  });

  it("returns plaintext when nothing matches", () => {
    expect(languageFor("noext", null)).toBe("plaintext");
  });
});

describe("citationToSource", () => {
  const base: Citation = {
    index: 1,
    title: "FastAPI Docs",
    source_type: "markdown",
    uri: "https://fastapi.tiangolo.com/di.md",
    snippet: "Dependency injection via Depends.",
    start_line: 10,
    end_line: 20,
    score: 0.9,
  };

  it("maps a citation to a viewer source with a resolved language", () => {
    const src = citationToSource(base);
    expect(src.title).toBe("FastAPI Docs");
    expect(src.language).toBe("markdown");
    expect(src.content).toBe("Dependency injection via Depends.");
    expect(src.startLine).toBe(10);
    expect(src.endLine).toBe(20);
  });

  it("derives a title and tolerates a missing snippet", () => {
    const src = citationToSource({
      ...base,
      title: "",
      snippet: "",
      uri: "repo/app.py",
    });
    expect(src.title).toBe("repo/app.py");
    expect(src.language).toBe("python");
    expect(src.content).toBe("");
  });
});
