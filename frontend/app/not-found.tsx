import { Compass } from "lucide-react";
import Link from "next/link";

/** Styled 404 page consistent with the RIVR light theme. */
export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-5 bg-[#f0f0f0] px-6 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-[#e0e4ea] bg-white text-[#1e325a] shadow-[0_10px_30px_rgba(30,50,90,0.08)]">
        <Compass size={26} />
      </div>
      <div>
        <p className="font-display text-5xl font-semibold text-[#1e325a]">404</p>
        <h1 className="mt-2 font-display text-xl font-semibold text-[#1e325a]">
          Page not found
        </h1>
        <p className="mt-2 max-w-sm text-sm text-[#5e6470]">
          The page you are looking for does not exist or has moved.
        </p>
      </div>
      <div className="flex gap-3">
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-full bg-[#1e325a] px-6 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#16264a]"
        >
          Back home
        </Link>
        <Link
          href="/app"
          className="inline-flex items-center gap-2 rounded-full border border-[#d8dce2] bg-white px-6 py-2.5 text-sm font-semibold text-[#1e325a] transition-colors hover:bg-[#f4f5f7]"
        >
          Open workspace
        </Link>
      </div>
    </div>
  );
}
