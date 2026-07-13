// Sentry browser (client) initialisation. Runs only when the DSN is configured
// (NEXT_PUBLIC_SENTRY_DSN), so local dev without the env var is a no-op.
import * as Sentry from "@sentry/nextjs";

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (dsn) {
  Sentry.init({
    dsn,
    environment: process.env.NODE_ENV,
    // Small trace sample to stay within the free tier; errors are always captured.
    tracesSampleRate: 0.1,
    // Session Replay is disabled to keep the bundle light and quota low.
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: 0,
  });
}
