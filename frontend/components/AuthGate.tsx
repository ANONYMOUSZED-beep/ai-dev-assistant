"use client";

import { LogIn, Terminal, UserPlus } from "lucide-react";
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

import {
  ApiError,
  clearToken,
  type CurrentUser,
  fetchMe,
  getToken,
  login,
  register,
  setToken,
} from "@/lib/api";

interface AuthContextValue {
  user: CurrentUser | null;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue>({ user: null, logout: () => {} });

/** Access the signed-in user and logout action from anywhere under <AuthGate>. */
export function useAuth(): AuthContextValue {
  return useContext(AuthContext);
}

type Status = "loading" | "anon" | "authed";

/**
 * Gates its children behind authentication. Validates any stored token on mount;
 * if absent/invalid, renders a login/register screen. On success, provides the
 * current user and a logout action via context.
 */
export default function AuthGate({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [user, setUser] = useState<CurrentUser | null>(null);

  useEffect(() => {
    if (!getToken()) {
      setStatus("anon");
      return;
    }
    fetchMe()
      .then((u) => {
        setUser(u);
        setStatus("authed");
      })
      .catch(() => {
        clearToken();
        setStatus("anon");
      });
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
    setStatus("anon");
  }, []);

  const onAuthenticated = useCallback((u: CurrentUser) => {
    setUser(u);
    setStatus("authed");
  }, []);

  if (status === "loading") {
    return (
      <div className="flex h-screen items-center justify-center bg-[#eef0f2] text-[#5e6470]">
        <span className="animate-pulse text-sm">Loading…</span>
      </div>
    );
  }

  if (status === "anon") {
    return <AuthScreen onAuthenticated={onAuthenticated} />;
  }

  return (
    <AuthContext.Provider value={{ user, logout }}>{children}</AuthContext.Provider>
  );
}

function AuthScreen({
  onAuthenticated,
}: {
  onAuthenticated: (user: CurrentUser) => void;
}) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const fn = mode === "login" ? login : register;
      const res = await fn(username.trim(), password);
      setToken(res.access_token);
      const me = await fetchMe();
      onAuthenticated(me);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : "Something went wrong. Please try again.";
      setError(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#eef0f2] px-4">
      <div className="w-full max-w-sm rounded-2xl border border-[#e0e4ea] bg-white p-8 shadow-[0_20px_60px_rgba(30,50,90,0.08)]">
        <div className="mb-6 flex items-center gap-2 text-[#1e325a]">
          <Terminal size={20} className="text-[#24406e]" />
          <span className="font-display text-lg font-semibold">
            AI Developer Assistant
          </span>
        </div>

        <h1 className="font-display text-xl font-semibold text-[#1e325a]">
          {mode === "login" ? "Welcome back" : "Create your account"}
        </h1>
        <p className="mt-1 text-sm text-[#5e6470]">
          {mode === "login"
            ? "Sign in to access your workspace."
            : "Your repositories stay private to your account."}
        </p>

        <form onSubmit={submit} className="mt-6 space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-[#5e6470]">
              Username
            </label>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
              minLength={3}
              className="w-full rounded-lg border border-[#d8dce2] bg-white px-3 py-2 text-sm text-[#1e325a] outline-none focus:border-[#24406e] focus:ring-1 focus:ring-[#24406e]"
              placeholder="yourname"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-[#5e6470]">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
              minLength={6}
              className="w-full rounded-lg border border-[#d8dce2] bg-white px-3 py-2 text-sm text-[#1e325a] outline-none focus:border-[#24406e] focus:ring-1 focus:ring-[#24406e]"
              placeholder="••••••••"
            />
          </div>

          {error ? (
            <p className="rounded-md bg-[#fdeceb] px-3 py-2 text-xs text-[#c0392b]">
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={busy}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#1e325a] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#16264a] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {mode === "login" ? <LogIn size={16} /> : <UserPlus size={16} />}
            {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>

        <button
          type="button"
          onClick={() => {
            setMode(mode === "login" ? "register" : "login");
            setError(null);
          }}
          className="mt-4 w-full text-center text-xs text-[#5e6470] hover:text-[#1e325a]"
        >
          {mode === "login"
            ? "New here? Create an account"
            : "Already have an account? Sign in"}
        </button>
      </div>
    </div>
  );
}
