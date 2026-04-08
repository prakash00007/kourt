"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

type AuthContextValue = {
  token: string | null;
  isAuthenticated: boolean;
  isReady: boolean;
  setToken: (token: string) => void;
  logout: () => void;
};

const STORAGE_KEY = "kourt_auth_token";

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: Readonly<{ children: React.ReactNode }>) {
  const [token, setTokenState] = useState<string | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored) {
      setTokenState(stored);
    }
    setIsReady(true);
  }, []);

  function setToken(nextToken: string) {
    window.localStorage.setItem(STORAGE_KEY, nextToken);
    setTokenState(nextToken);
  }

  function logout() {
    window.localStorage.removeItem(STORAGE_KEY);
    setTokenState(null);
  }

  const value = useMemo(
    () => ({
      token,
      isAuthenticated: Boolean(token),
      isReady,
      setToken,
      logout
    }),
    [token, isReady]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider.");
  }
  return context;
}
