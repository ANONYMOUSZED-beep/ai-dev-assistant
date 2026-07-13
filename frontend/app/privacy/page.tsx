import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "How AI Developer Assistant collects, uses, and protects your data.",
};

const UPDATED = "July 2026";

export default function PrivacyPage() {
  return (
    <main className="mx-auto min-h-screen max-w-3xl px-6 py-14 text-[#1e325a]">
      <Link
        href="/"
        className="text-sm text-[#5e6470] underline underline-offset-2 hover:text-[#1e325a]"
      >
        ← Back to home
      </Link>

      <h1 className="mt-6 font-display text-3xl font-semibold">Privacy Policy</h1>
      <p className="mt-1 text-sm text-[#5e6470]">Last updated: {UPDATED}</p>

      <div className="prose-sm mt-8 space-y-6 text-[#39435c]">
        <section>
          <h2 className="text-lg font-semibold text-[#1e325a]">Overview</h2>
          <p>
            AI Developer Assistant (&quot;the app&quot;) lets you chat with your own
            documents and code with answers grounded in cited sources. This policy
            explains what we store and why. We aim to collect the minimum needed to
            run the service.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-[#1e325a]">What we store</h2>
          <ul className="list-disc space-y-1 pl-5">
            <li>
              <strong>Account:</strong> a username, and — if you sign in with Google —
              your email address and Google account identifier. Passwords, when used,
              are stored only as a salted hash, never in plain text.
            </li>
            <li>
              <strong>Your content:</strong> documents you upload, repositories you
              add, and the resulting text embeddings used for search.
            </li>
            <li>
              <strong>Conversations:</strong> your chat history, so you can revisit it.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-[#1e325a]">
            How your content is used
          </h2>
          <p>
            Your questions and the relevant snippets of your indexed content are sent
            to a third-party large language model provider to generate answers. Your
            content is used only to answer your own requests — it is not sold, and it
            is not used to train third-party models by us.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-[#1e325a]">Sign in with Google</h2>
          <p>
            If you use Google sign-in, we receive your basic profile email and a
            unique identifier to create and recognise your account. We do not access
            your Gmail, contacts, or other Google data.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-[#1e325a]">
            Your control over your data
          </h2>
          <p>
            You can export all of your data as a file, or permanently delete your
            account and all associated documents, repositories, and chats, at any time
            from the account menu in the app.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-[#1e325a]">Contact</h2>
          <p>
            For any privacy questions or data requests, contact the project owner
            through the repository or the email associated with this deployment.
          </p>
        </section>

        <p className="pt-4 text-xs text-[#8a91a0]">
          This is a student/educational project. Please avoid uploading highly
          sensitive information.
        </p>
      </div>

      <div className="mt-10 text-sm text-[#5e6470]">
        See also our{" "}
        <Link href="/terms" className="underline underline-offset-2 hover:text-[#1e325a]">
          Terms of Service
        </Link>
        .
      </div>
    </main>
  );
}
