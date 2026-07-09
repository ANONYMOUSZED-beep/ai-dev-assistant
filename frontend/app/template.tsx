"use client";

import type { ReactNode } from "react";

/**
 * Route transition wrapper. Unlike `layout.tsx`, a `template.tsx` is re-mounted
 * on every navigation, so the `page-enter` animation replays each time the user
 * moves between routes (e.g. home → app), giving a smooth, fluid transition.
 */
export default function Template({ children }: { children: ReactNode }) {
  return <div className="page-enter">{children}</div>;
}
