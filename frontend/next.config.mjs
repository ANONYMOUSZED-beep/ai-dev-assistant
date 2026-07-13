import { withSentryConfig } from "@sentry/nextjs";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Required on Next 14.2 for instrumentation.ts (server/edge Sentry init) to run.
  experimental: {
    instrumentationHook: true,
  },
};

// Wrap with Sentry. Source-map upload is skipped unless SENTRY_AUTH_TOKEN/org/project
// are set, so builds work fine without them (errors are still captured at runtime).
export default withSentryConfig(nextConfig, {
  silent: true,
  disableLogger: true,
});
