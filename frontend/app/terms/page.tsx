import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Terms of Service",
  description: "The terms for using AI Developer Assistant.",
};

const UPDATED = "July 2026";

export default function TermsPage() {
  return (
    <main className="mx-auto min-h-screen max-w-3xl px-6 py-14 text-[#1e325a]">
      <Link
        href="/"
        className="text-sm text-[#5e6470] underline underline-offset-2 hover:text-[#1e325a]"
      >
        ← Back to home
      </Link>

      <h1 className="mt-6 font-display text-3xl font-semibold">Terms of Service</h1>
      <p className="mt-1 text-sm text-[#5e6470]">Last updated: {UPDATED}</p>

      <div className="mt-8 space-y-6 text-[#39435c]">
        <section>
          <h2 className="text-lg font-semibold text-[#1e325a]">Acceptance</h2>
          <p>
            By creating an account or using AI Developer Assistant (&quot;the
            app&quot;), you agree to these terms. If you do not agree, please do not
            use the app.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-[#1e325a]">Acceptable use</h2>
          <ul className="list-disc space-y-1 pl-5">
            <li>Use the app lawfully and only with content you have the right to use.</li>
            <li>
              Do not upload malicious, illegal, or infringing material, or attempt to
              disrupt or abuse the service.
            </li>
            <li>
              Do not rely on answers as professional (legal, medical, or financial)
              advice — always verify important results against the cited sources.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-[#1e325a]">Your content</h2>
          <p>
            You retain ownership of the documents and code you add. You grant the app
            permission to process that content to provide answers to you. You are
            responsible for the content you upload.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-[#1e325a]">
            Availability and AI limitations
          </h2>
          <p>
            The app is provided &quot;as is&quot; without warranties. It may be
            unavailable at times, and AI-generated answers can be incomplete or
            incorrect. Use your own judgement.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-[#1e325a]">Termination</h2>
          <p>
            You can delete your account at any time from the account menu. We may
            suspend access that violates these terms.
          </p>
        </section>

        <p className="pt-4 text-xs text-[#8a91a0]">
          This is a student/educational project offered free of charge.
        </p>
      </div>

      <div className="mt-10 text-sm text-[#5e6470]">
        See also our{" "}
        <Link
          href="/privacy"
          className="underline underline-offset-2 hover:text-[#1e325a]"
        >
          Privacy Policy
        </Link>
        .
      </div>
    </main>
  );
}
