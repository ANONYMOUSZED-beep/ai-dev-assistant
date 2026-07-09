"use client";

import { type ReactNode, useEffect, useRef } from "react";

interface ParallaxProps {
  /** Positive drifts up as you scroll down; negative drifts down. ~0.1–0.4 is subtle. */
  speed?: number;
  className?: string;
  children?: ReactNode;
}

/**
 * Lightweight, dependency-free parallax. Translates its content on scroll based
 * on the element's position relative to the viewport centre, using rAF-throttled
 * passive scroll for smoothness. Honors prefers-reduced-motion.
 */
export default function Parallax({ speed = 0.2, className, children }: ParallaxProps) {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let raf = 0;
    let ticking = false;

    const update = () => {
      ticking = false;
      const rect = el.getBoundingClientRect();
      const viewportCenter = window.innerHeight / 2;
      const elCenter = rect.top + rect.height / 2;
      const delta = elCenter - viewportCenter;
      el.style.transform = `translate3d(0, ${(-delta * speed).toFixed(2)}px, 0)`;
    };

    const onScroll = () => {
      if (!ticking) {
        ticking = true;
        raf = requestAnimationFrame(update);
      }
    };

    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      cancelAnimationFrame(raf);
    };
  }, [speed]);

  return (
    <div ref={ref} className={className} style={{ willChange: "transform" }}>
      {children}
    </div>
  );
}
