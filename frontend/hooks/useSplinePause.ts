"use client";

import { useEffect, useRef } from "react";

/** Minimal structural type — the Spline Application exposes play()/stop(). */
type SplineControls = { play?: () => void; stop?: () => void };

/**
 * Pauses a Spline scene's render loop while it's scrolled off-screen and resumes
 * it when visible, using an IntersectionObserver. Spline scenes render every
 * frame on the GPU, so stopping the loop offscreen removes their cost entirely.
 *
 * Returns:
 * - `appRef`  — assign the Application from Spline's `onLoad`.
 * - `containerRef` — attach to the element that scrolls in/out of view.
 */
export function useSplinePause() {
  const appRef = useRef<SplineControls | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el || typeof IntersectionObserver === "undefined") return;

    const observer = new IntersectionObserver(
      (entries) => {
        const app = appRef.current;
        if (!app) return;
        for (const entry of entries) {
          if (entry.isIntersecting) app.play?.();
          else app.stop?.();
        }
      },
      { threshold: 0.01 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return { appRef, containerRef };
}
