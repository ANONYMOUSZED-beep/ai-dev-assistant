"use client";

import { type ReactNode, useEffect, useRef } from "react";

interface RevealProps {
  /** Delay in ms before the reveal transition starts. */
  delay?: number;
  className?: string;
  children?: ReactNode;
}

/**
 * Fade-and-rise reveal when the element scrolls into view (once). Uses an
 * IntersectionObserver and toggles `.is-visible`; the transition lives in CSS
 * and is disabled under prefers-reduced-motion.
 */
export default function Reveal({ delay = 0, className = "", children }: RevealProps) {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            el.classList.add("is-visible");
            observer.unobserve(el);
          }
        }
      },
      { threshold: 0.15 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={`reveal ${className}`}
      style={delay ? { transitionDelay: `${delay}ms` } : undefined}
    >
      {children}
    </div>
  );
}
