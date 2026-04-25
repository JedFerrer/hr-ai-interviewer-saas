"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
  type ReactNode,
} from "react";
import { auth as authApi, onSessionExpired } from "./api";
import type { User } from "./types";

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  signup: (data: {
    email: string;
    password: string;
    name: string;
    company_name: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// --- Refresh scheduling -------------------------------------------------------
//
// The HttpOnly cookie carries the JWT; the cookie's lifetime equals the token's
// `exp`. The backend reports `expires_in` (seconds remaining) on /auth/me and
// /auth/refresh so the frontend can schedule a refresh comfortably before the
// token expires.
//
//   - REFRESH_LEAD_SECONDS: how far before expiry to refresh.
//   - MIN_REFRESH_INTERVAL_MS: never schedule sooner than this — prevents a
//     pathological tight loop if the server reports a tiny TTL.
//   - VISIBILITY_THRESHOLD_MS: if the tab returns to foreground and the next
//     scheduled refresh is closer than this, refresh immediately. Browsers
//     throttle setTimeout in background tabs, so a 60-min session with the tab
//     hidden could otherwise wake up already expired.

const REFRESH_LEAD_SECONDS = 5 * 60; // refresh 5 min before exp
const MIN_REFRESH_INTERVAL_MS = 30 * 1000; // never re-fire within 30s
const VISIBILITY_THRESHOLD_MS = 2 * 60 * 1000;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
  });

  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const nextRefreshAtRef = useRef<number | null>(null);

  const clearRefreshTimer = useCallback(() => {
    if (refreshTimerRef.current !== null) {
      clearTimeout(refreshTimerRef.current);
      refreshTimerRef.current = null;
    }
    nextRefreshAtRef.current = null;
  }, []);

  /**
   * Schedule a single refresh `expires_in - REFRESH_LEAD_SECONDS` from now,
   * floored at MIN_REFRESH_INTERVAL_MS. After a successful refresh we
   * re-schedule using the new TTL returned by the server.
   */
  const scheduleRefresh = useCallback(
    (expiresInSeconds: number) => {
      clearRefreshTimer();

      const leadMs = Math.max(
        (expiresInSeconds - REFRESH_LEAD_SECONDS) * 1000,
        MIN_REFRESH_INTERVAL_MS,
      );
      nextRefreshAtRef.current = Date.now() + leadMs;

      refreshTimerRef.current = setTimeout(async () => {
        try {
          const { expires_in } = await authApi.refresh();
          scheduleRefresh(expires_in);
        } catch {
          // Refresh failed — onSessionExpired listener will fire from the
          // /auth/refresh request itself if the cookie is gone. Stop
          // scheduling so we don't spin.
          clearRefreshTimer();
        }
      }, leadMs);
    },
    [clearRefreshTimer],
  );

  // Probe `/auth/me` on mount to learn whether the browser already has a
  // valid session. If so, kick off the proactive refresh schedule.
  useEffect(() => {
    let cancelled = false;
    authApi
      .me()
      .then(({ user, expires_in }) => {
        if (cancelled) return;
        setState({ user, isLoading: false, isAuthenticated: true });
        scheduleRefresh(expires_in);
      })
      .catch(() => {
        if (cancelled) return;
        setState({ user: null, isLoading: false, isAuthenticated: false });
      });
    return () => {
      cancelled = true;
    };
  }, [scheduleRefresh]);

  // When the tab returns to the foreground, browsers may have throttled the
  // refresh timer. If the scheduled refresh is imminent (or overdue), do it
  // now so we never serve a request with an expired cookie.
  useEffect(() => {
    if (typeof document === "undefined") return;

    const onVisibility = async () => {
      if (document.visibilityState !== "visible") return;
      const next = nextRefreshAtRef.current;
      if (next === null) return;
      const remaining = next - Date.now();
      if (remaining > VISIBILITY_THRESHOLD_MS) return;

      clearRefreshTimer();
      try {
        const { expires_in } = await authApi.refresh();
        scheduleRefresh(expires_in);
      } catch {
        // handled by onSessionExpired listener below
      }
    };

    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, [clearRefreshTimer, scheduleRefresh]);

  // Subscribe to silent-refresh failures from the API layer. When the session
  // is unrecoverable, drop local state and bounce to /login (unless already on
  // a public page like /login or /signup).
  useEffect(() => {
    const unsubscribe = onSessionExpired(() => {
      clearRefreshTimer();
      setState({ user: null, isLoading: false, isAuthenticated: false });
      if (typeof window === "undefined") return;
      const path = window.location.pathname;
      const isPublic =
        path.startsWith("/login") ||
        path.startsWith("/signup") ||
        path.startsWith("/interview") ||
        path.startsWith("/report");
      if (!isPublic) {
        window.location.href = "/login";
      }
    });
    return unsubscribe;
  }, [clearRefreshTimer]);

  // Always clean up on unmount.
  useEffect(() => clearRefreshTimer, [clearRefreshTimer]);

  const login = useCallback(
    async (email: string, password: string) => {
      // Cookie is set by the response Set-Cookie header.
      const { expires_in } = await authApi.login({ email, password });
      const { user } = await authApi.me();
      setState({ user, isLoading: false, isAuthenticated: true });
      scheduleRefresh(expires_in);
    },
    [scheduleRefresh],
  );

  const signup = useCallback(
    async (data: {
      email: string;
      password: string;
      name: string;
      company_name: string;
    }) => {
      const response = await authApi.signup(data);
      setState({
        user: response.user,
        isLoading: false,
        isAuthenticated: true,
      });
      scheduleRefresh(response.expires_in);
    },
    [scheduleRefresh],
  );

  const logout = useCallback(async () => {
    clearRefreshTimer();
    try {
      await authApi.logout();
    } catch {
      // Logout is best-effort; clear local state regardless.
    }
    setState({ user: null, isLoading: false, isAuthenticated: false });
    window.location.href = "/login";
  }, [clearRefreshTimer]);

  return (
    <AuthContext.Provider value={{ ...state, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
