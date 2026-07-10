"use client";

import { ReactLenis } from "lenis/react";
import { type ReactNode, useEffect, useState } from "react";

/**
 * Buttery momentum scrolling for the landing page via Lenis.
 *
 * - `root` drives the document scroll (so anchor links and parallax still work).
 * - `anchors` makes in-page `#section` links smooth-scroll.
 * - Disabled entirely under prefers-reduced-motion (falls back to native scroll).
 */
export default function SmoothScroll({ children }: { children: ReactNode }) {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    setReduced(window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }, []);

  if (reduced) return <>{children}</>;

  return (
    <ReactLenis
      root
      options={{ lerp: 0.09, duration: 1.1, smoothWheel: true, anchors: true }}
    >
      {children}
    </ReactLenis>
  );
}
