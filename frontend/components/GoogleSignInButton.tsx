"use client";

import { useEffect, useRef } from "react";

import {
  type CurrentUser,
  fetchMe,
  GOOGLE_CLIENT_ID,
  googleLogin,
  setToken,
} from "@/lib/api";
import { humanizeError } from "@/lib/errors";

// Minimal typing for the Google Identity Services global.
interface GoogleCredentialResponse {
  credential?: string;
}
interface GoogleIdApi {
  initialize: (config: {
    client_id: string;
    callback: (response: GoogleCredentialResponse) => void;
  }) => void;
  renderButton: (el: HTMLElement, options: Record<string, unknown>) => void;
}
declare global {
  interface Window {
    google?: { accounts: { id: GoogleIdApi } };
  }
}

const GIS_SRC = "https://accounts.google.com/gsi/client";
let gisPromise: Promise<void> | null = null;

function loadGis(): Promise<void> {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("no window"));
  }
  if (window.google?.accounts?.id) return Promise.resolve();
  if (gisPromise) return gisPromise;
  gisPromise = new Promise<void>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = GIS_SRC;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Google sign-in"));
    document.head.appendChild(script);
  });
  return gisPromise;
}

interface GoogleSignInButtonProps {
  onAuthenticated: (user: CurrentUser) => void;
  onError: (message: string) => void;
}

/**
 * Renders the official "Sign in with Google" button. On success it exchanges the
 * Google ID token for our own access token via the backend, then reports the user.
 * Renders nothing when NEXT_PUBLIC_GOOGLE_CLIENT_ID is not configured.
 */
export default function GoogleSignInButton({
  onAuthenticated,
  onError,
}: GoogleSignInButtonProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;
    let cancelled = false;

    loadGis()
      .then(() => {
        if (cancelled || !containerRef.current || !window.google) return;
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: (response) => {
            if (!response.credential) {
              onError("Google sign-in was cancelled. Please try again.");
              return;
            }
            googleLogin(response.credential)
              .then((token) => {
                setToken(token.access_token);
                return fetchMe();
              })
              .then((user) => onAuthenticated(user))
              .catch((err) => onError(humanizeError(err)));
          },
        });
        window.google.accounts.id.renderButton(containerRef.current, {
          theme: "outline",
          size: "large",
          width: 320,
          text: "continue_with",
          shape: "pill",
        });
      })
      .catch(() => onError("We couldn't load Google sign-in. Please try again."));

    return () => {
      cancelled = true;
    };
  }, [onAuthenticated, onError]);

  if (!GOOGLE_CLIENT_ID) return null;
  return <div ref={containerRef} className="flex justify-center" />;
}
