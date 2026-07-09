"use client";

import { RefreshCw } from "lucide-react";
import { useEffect } from "react";

/**
 * Route-segment error boundary. Catches render/runtime errors so users get a
 * graceful recovery screen instead of a blank page, and logs for diagnostics.
 */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error("Unhandled UI error:", error);
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-5 bg-[#f0f0f0] px-6 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-[#e0e4ea] bg-white text-[#1e325a] shadow-[0_10px_30px_rgba(30,50,90,0.08)]">
        <RefreshCw size={26} />
      </div>
      <div>
        <h1 className="font-display text-2xl font-semibold text-[#1e325a]">
          Something went wrong
        </h1>
        <p className="mt-2 max-w-sm text-sm text-[#5e6470]">
          An unexpected error occurred. You can try again — if it keeps happening,
          reload the page.
        </p>
        {error.digest ? (
          <p className="mt-2 font-mono text-xs text-[#9aa0ad]">ref: {error.digest}</p>
        ) : null}
      </div>
      <button
        type="button"
        onClick={reset}
        className="inline-flex items-center gap-2 rounded-full bg-[#1e325a] px-6 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#16264a]"
      >
        <RefreshCw size={16} />
        Try again
      </button>
    </div>
  );
}
