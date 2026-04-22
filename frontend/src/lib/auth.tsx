"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { auth as authApi } from "./api";
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
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
  });

  // Check existing session on mount
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setState({ user: null, isLoading: false, isAuthenticated: false });
      return;
    }

    authApi
      .me()
      .then(({ user }) => {
        setState({ user, isLoading: false, isAuthenticated: true });
      })
      .catch(() => {
        localStorage.removeItem("access_token");
        setState({ user: null, isLoading: false, isAuthenticated: false });
      });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const response = await authApi.login({ email, password });
    localStorage.setItem("access_token", response.access_token);
    // Login response only has token — fetch user profile
    const { user } = await authApi.me();
    setState({ user, isLoading: false, isAuthenticated: true });
  }, []);

  const signup = useCallback(
    async (data: {
      email: string;
      password: string;
      name: string;
      company_name: string;
    }) => {
      const response = await authApi.signup(data);
      localStorage.setItem("access_token", response.access_token);
      setState({
        user: response.user,
        isLoading: false,
        isAuthenticated: true,
      });
    },
    [],
  );

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    setState({ user: null, isLoading: false, isAuthenticated: false });
    window.location.href = "/login";
  }, []);

  return (
    <AuthContext.Provider
      value={{ ...state, login, signup, logout }}
    >
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
