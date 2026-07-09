"use client";

import {
  ArrowRight,
  BookOpen,
  Boxes,
  Bug,
  GitBranch,
  type LucideIcon,
  Quote,
  Rocket,
  Search,
  ShieldCheck,
  Sparkles,
  Terminal,
  Zap,
} from "lucide-react";
import Link from "next/link";

import Parallax from "./home/Parallax";
import Reveal from "./home/Reveal";

interface Feature {
  icon: LucideIcon;
  title: string;
  desc: string;
}

const FEATURES: Feature[] = [
  {
    icon: BookOpen,
    title: "Docs Chat",
    desc: "Ask questions across framework and internal documentation. Every answer is grounded in retrieved passages and cited to its source.",
  },
  {
    icon: GitBranch,
    title: "Repo Chat",
    desc: "Connect a GitHub repository and understand its architecture, files, classes, and cross-file dependencies in plain English.",
  },
  {
    icon: Search,
    title: "Code Search",
    desc: "Find exact implementations with natural-language semantic search — “where is JWT auth implemented?” just works.",
  },
  {
    icon: Bug,
    title: "Debug",
    desc: "Paste a stack trace and get pinpointed root-cause analysis with corrected code, linked back to the relevant sources.",
  },
  {
    icon: Sparkles,
    title: "Pair Programmer",
    desc: "Explain, refactor, generate tests and docs, optimize, and run security reviews — all respecting your repo's conventions.",
  },
];

const STACK = [
  "FastAPI",
  "Next.js",
  "PostgreSQL",
  "Redis",
  "FAISS",
  "BGE-M3",
  "Docker",
  "Pydantic v2",
];

const STEPS = [
  {
    n: "01",
    title: "Connect",
    desc: "Point the assistant at a docs collection or connect a GitHub repository to index.",
  },
  {
    n: "02",
    title: "Ask",
    desc: "Ask in plain English — chat, search, debug, or pair-program. No query syntax.",
  },
  {
    n: "03",
    title: "Trust",
    desc: "Read grounded answers with inline citations you can open and verify in a click.",
  },
];

function SectionHeader({
  eyebrow,
  title,
  subtitle,
}: {
  eyebrow: string;
  title: string;
  subtitle?: string;
}) {
  return (
    <Reveal className="mx-auto mb-14 max-w-2xl text-center">
      <span className="rivr-eyebrow">{eyebrow}</span>
      <h2 className="font-display mt-3 text-3xl font-semibold tracking-tight text-[#1e325a] md:text-5xl">
        {title}
      </h2>
      {subtitle ? <p className="mt-4 text-base text-[#5e6470]">{subtitle}</p> : null}
    </Reveal>
  );
}

export default function HomeShowcase() {
  return (
    <div className="rivr-showcase">
      {/* ── Features ─────────────────────────────────────────── */}
      <section id="features" className="rivr-section">
        <Parallax speed={0.12} className="rivr-blob rivr-blob--violet -left-24 top-10" />
        <div className="rivr-container">
          <SectionHeader
            eyebrow="Features"
            title="One assistant, five ways to ship faster."
            subtitle="Every capability is grounded in your own sources, so you can trust what you read and act on it immediately."
          />
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f, i) => {
              const Icon = f.icon;
              return (
                <Reveal key={f.title} delay={(i % 3) * 90} className="h-full">
                  <div className="rivr-card group h-full">
                    <div className="rivr-icon">
                      <Icon size={22} />
                    </div>
                    <h3 className="font-display mt-5 text-xl font-semibold text-[#1e325a]">
                      {f.title}
                    </h3>
                    <p className="mt-2 text-sm leading-relaxed text-[#5e6470]">
                      {f.desc}
                    </p>
                  </div>
                </Reveal>
              );
            })}
          </div>
        </div>
      </section>

      {/* ── Capabilities ─────────────────────────────────────── */}
      <section id="capabilities" className="rivr-section rivr-section--tint">
        <Parallax speed={0.16} className="rivr-blob rivr-blob--cyan right-[-6rem] top-24" />
        <div className="rivr-container">
          <SectionHeader
            eyebrow="Capabilities"
            title="Answers you can actually trust."
            subtitle="Retrieval-augmented, streamed token-by-token, and provider-agnostic — engineered to reduce hallucinations, not hide them."
          />

          <div className="grid items-center gap-10 md:grid-cols-2">
            <Reveal>
              <div className="space-y-6">
                <div className="flex gap-4">
                  <div className="rivr-icon shrink-0">
                    <Quote size={20} />
                  </div>
                  <div>
                    <h3 className="font-display text-lg font-semibold text-[#1e325a]">
                      Grounded in citations
                    </h3>
                    <p className="mt-1 text-sm text-[#5e6470]">
                      Responses are generated from retrieved passages of your docs
                      and code. Inline{" "}
                      <span className="rivr-chip">1</span> markers open the exact
                      source.
                    </p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="rivr-icon shrink-0">
                    <Zap size={20} />
                  </div>
                  <div>
                    <h3 className="font-display text-lg font-semibold text-[#1e325a]">
                      Streamed in real time
                    </h3>
                    <p className="mt-1 text-sm text-[#5e6470]">
                      Answers stream token-by-token over SSE, so you start reading
                      the moment the model starts thinking.
                    </p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="rivr-icon shrink-0">
                    <ShieldCheck size={20} />
                  </div>
                  <div>
                    <h3 className="font-display text-lg font-semibold text-[#1e325a]">
                      Provider-agnostic
                    </h3>
                    <p className="mt-1 text-sm text-[#5e6470]">
                      Swap between Claude, GPT, Gemini, DeepSeek, Qwen, and Groq
                      without changing a line of your workflow.
                    </p>
                  </div>
                </div>
              </div>
            </Reveal>

            <Reveal delay={120}>
              <Parallax speed={-0.1}>
                <div className="rivr-card">
                  <p className="text-sm leading-relaxed text-[#1e325a]">
                    Dependency injection lets FastAPI resolve shared resources per
                    request via{" "}
                    <code className="rivr-code">Depends</code>
                    <span className="ml-1 inline-flex gap-1 align-middle">
                      <span className="rivr-chip">1</span>
                      <span className="rivr-chip">2</span>
                    </span>
                    .
                  </p>
                  <div className="mt-4 space-y-2">
                    {["dependencies.py", "routing.py"].map((file, idx) => (
                      <div key={file} className="rivr-source">
                        <span className="rivr-chip">{idx + 1}</span>
                        <span className="font-mono text-xs text-[#1e325a]">
                          {file}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </Parallax>
            </Reveal>
          </div>

          <Reveal className="mt-14">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {[
                { k: "13+", v: "Frameworks indexed" },
                { k: "6", v: "LLM providers" },
                { k: "100%", v: "Answers cited" },
              ].map((s) => (
                <div key={s.v} className="rivr-stat">
                  <div className="font-display text-4xl font-semibold text-[#1e325a]">
                    {s.k}
                  </div>
                  <div className="mt-1 text-xs uppercase tracking-[0.14em] text-[#5e6470]">
                    {s.v}
                  </div>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      {/* ── Developers ───────────────────────────────────────── */}
      <section id="developers" className="rivr-section">
        <Parallax speed={0.14} className="rivr-blob rivr-blob--indigo left-[-5rem] bottom-10" />
        <div className="rivr-container">
          <SectionHeader
            eyebrow="Developers"
            title="Built for engineers, top to bottom."
            subtitle="A typed, async, container-ready stack with a pluggable RAG pipeline — inspectable and yours to run."
          />

          <div className="grid items-center gap-10 md:grid-cols-2">
            <Reveal delay={120} className="md:order-2">
              <Parallax speed={-0.08}>
                <div className="rivr-terminal">
                  <div className="rivr-terminal__bar">
                    <span className="rivr-dot" style={{ background: "#ff6159" }} />
                    <span className="rivr-dot" style={{ background: "#ffbd2e" }} />
                    <span className="rivr-dot" style={{ background: "#28c840" }} />
                    <span className="ml-2 font-mono text-[0.7rem] text-white/50">
                      quickstart.sh
                    </span>
                  </div>
                  <pre className="rivr-terminal__body">
{`# spin up the full stack
docker compose up --build

# API   → http://localhost:8000/docs
# Web   → http://localhost:3000

curl -X POST localhost:8000/api/v1/chat \\
  -H "Content-Type: application/json" \\
  -d '{"question":"How does DI work?"}'`}
                  </pre>
                </div>
              </Parallax>
            </Reveal>

            <Reveal className="md:order-1">
              <ul className="space-y-4">
                {[
                  {
                    icon: Zap,
                    t: "Async FastAPI + Pydantic v2",
                    d: "Fully typed, validated at the edges, streaming-first.",
                  },
                  {
                    icon: Boxes,
                    t: "Pluggable RAG pipeline",
                    d: "Swap embedders, vector stores, and rerankers behind clean contracts.",
                  },
                  {
                    icon: Terminal,
                    t: "One-command Docker",
                    d: "docker compose up brings the whole system online.",
                  },
                  {
                    icon: ShieldCheck,
                    t: "Auth & rate limiting",
                    d: "API-key auth and per-client rate limits, ready for production.",
                  },
                ].map((row) => {
                  const Icon = row.icon;
                  return (
                    <li key={row.t} className="flex gap-4">
                      <div className="rivr-icon shrink-0">
                        <Icon size={18} />
                      </div>
                      <div>
                        <p className="font-display font-semibold text-[#1e325a]">
                          {row.t}
                        </p>
                        <p className="text-sm text-[#5e6470]">{row.d}</p>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </Reveal>
          </div>

          <Reveal className="mt-12">
            <div className="flex flex-wrap justify-center gap-2.5">
              {STACK.map((s) => (
                <span key={s} className="rivr-badge">
                  {s}
                </span>
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      {/* ── Docs / Get started ───────────────────────────────── */}
      <section id="docs" className="rivr-section rivr-section--tint">
        <Parallax speed={0.16} className="rivr-blob rivr-blob--violet right-[-4rem] top-8" />
        <div className="rivr-container">
          <SectionHeader
            eyebrow="Documentation"
            title="Up and running in three steps."
          />
          <div className="grid gap-5 md:grid-cols-3">
            {STEPS.map((step, i) => (
              <Reveal key={step.n} delay={i * 100}>
                <div className="rivr-card h-full">
                  <span className="font-display text-4xl font-semibold text-[#c3c8d4]">
                    {step.n}
                  </span>
                  <h3 className="font-display mt-3 text-xl font-semibold text-[#1e325a]">
                    {step.title}
                  </h3>
                  <p className="mt-2 text-sm text-[#5e6470]">{step.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>

          <Reveal className="mt-14 text-center">
            <div className="rivr-cta">
              <Rocket size={26} className="mx-auto text-[#1e325a]" />
              <h3 className="font-display mt-3 text-2xl font-semibold text-[#1e325a] md:text-3xl">
                Start exploring your codebase
              </h3>
              <p className="mx-auto mt-2 max-w-md text-sm text-[#5e6470]">
                Grounded answers, cited sources, and an interactive workspace —
                one click away.
              </p>
              <Link href="/app" className="rivr-cta__btn">
                Launch App
                <ArrowRight size={18} />
              </Link>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────── */}
      <footer className="rivr-footer">
        <div className="rivr-container flex flex-col items-center justify-between gap-4 md:flex-row">
          <div className="flex items-center gap-2 text-[#1e325a]">
            <Terminal size={18} />
            <span className="font-display font-semibold">AI Developer Assistant</span>
          </div>
          <p className="text-xs text-[#5e6470]">
            Grounded · Cited · Interactive — © 2026
          </p>
        </div>
      </footer>
    </div>
  );
}
