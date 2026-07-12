// Turn raw/technical errors into calm, plain-language messages a non-technical
// user can act on. Server-provided messages for ordinary 4xx cases (e.g. "Invalid
// username or password") are kept, since those are already meaningful.

import { ApiError } from "./api";

const NETWORK_RE = /failed to fetch|networkerror|network error|network request/i;

export function humanizeError(err: unknown): string {
  if (err instanceof ApiError) {
    const status = err.status;
    const raw = (err.message ?? "").trim();

    if (status === 0 || NETWORK_RE.test(raw)) {
      return "We couldn't reach the server. It may be waking up from sleep — please wait a few seconds and try again.";
    }
    if (status === 429) {
      return "You're going a little fast — please wait a moment and try again.";
    }
    if (status === 413 || /too large/i.test(raw)) {
      return "That file is too large. Please choose a file under 10 MB.";
    }
    if (status >= 500) {
      return "Something went wrong on our end. Please try again in a moment.";
    }
    // Ordinary 4xx: the backend's message is usually already clear.
    return raw || "Something went wrong. Please try again.";
  }

  if (err instanceof Error) {
    if (NETWORK_RE.test(err.message)) {
      return "We couldn't reach the server. Please check your connection and try again.";
    }
    return err.message || "Something went wrong. Please try again.";
  }

  return "Something went wrong. Please try again.";
}
