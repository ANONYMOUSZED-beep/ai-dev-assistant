import Link from "next/link";

import HomeShowcase from "@/components/HomeShowcase";
import SplineHero from "@/components/SplineHero";

/** Diagonal "open" arrow used inside every circular icon (matches the design). */
function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M7 17 17 7M9 7h8v8"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

const NAV_ITEMS = [
  { label: "Features", href: "#features" },
  { label: "Capabilities", href: "#capabilities" },
  { label: "Developers", href: "#developers" },
  { label: "Docs", href: "#docs" },
];

export default function LandingPage() {
  return (
    <div className="rivr-shell">
      <main>
        <div className="page-shell">
        <section className="hero-card">
          {/* Interactive 3D scene as the hero background. A light+glow base and
              an instant poster mean the blended look is present from frame one —
              the 3D simply crossfades in on top of it, never a bare old hero. */}
          <SplineHero scene="https://prod.spline.design/eIq-jAM8Cvk3ZGgW/scene.splinecode" />

          {/* RIVR chrome. The container ignores pointer events so the 3D scene
              stays draggable; only the real controls re-enable them. */}
          <div className="hero-content hero-content--interactive-children">
            <nav className="top-nav">
              <div className="nav-spacer" />
              <ul className="nav-links">
                {NAV_ITEMS.map((item) => (
                  <li key={item.label}>
                    <a href={item.href}>{item.label}</a>
                  </li>
                ))}
              </ul>
              <div className="nav-right">
                <Link className="book-demo" href="/app">
                  <span className="icon-circle">
                    <ArrowIcon />
                  </span>
                  <span>Launch App</span>
                </Link>
              </div>
            </nav>

            <div className="hero-copy">
              <div className="tag-pill">
                <span className="spark">✦</span>
                <span>Grounded in citations</span>
              </div>
              <h1>Understand Any Codebase</h1>
              <p>
                Chat with your docs and repositories, search code semantically,
                debug stack traces, and pair-program — every answer cited to its
                source.
              </p>
            </div>

            <div className="yield-card">
              <div className="yield-number">5</div>
              <div className="yield-label">AI Capabilities</div>
              <Link className="discord-btn" href="/app">
                <span className="icon-circle small">
                  <ArrowIcon />
                </span>
                <span>Get Started</span>
              </Link>
            </div>

            <Link className="doc-card" href="#docs">
              <span className="doc-notch top" />
              <span className="doc-notch side" />
              <span className="doc-icon icon-circle large">
                <ArrowIcon />
              </span>
              <span className="doc-texts">
                <span className="doc-title">Documentation</span>
                <span className="doc-sub">
                  Library <span className="chev">›</span>
                </span>
              </span>
            </Link>
          </div>
        </section>
        </div>

        <HomeShowcase />
      </main>
    </div>
  );
}
