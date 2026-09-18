"use client";

import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { authApi, tokenStore } from "./api";
import type { User } from "./types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: Parameters<typeof authApi.register>[0]) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  /** Met à jour le solde de crédits après une génération, sans requête. */
  setCredits: (remaining: number) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    if (!tokenStore.access) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      setUser(await authApi.me());
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  const login = useCallback(
    async (email: string, password: string) => {
      const data = await authApi.login(email, password);
      tokenStore.set(data.access_token, data.refresh_token);
      setUser(data.user);
      router.push("/tableau-de-bord");
    },
    [router],
  );

  const register = useCallback(
    async (payload: Parameters<typeof authApi.register>[0]) => {
      const data = await authApi.register(payload);
      tokenStore.set(data.access_token, data.refresh_token);
      setUser(data.user);
      router.push("/tableau-de-bord");
    },
    [router],
  );

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
    router.push("/connexion");
  }, [router]);

  const setCredits = useCallback((remaining: number) => {
    setUser((current) =>
      current ? { ...current, ai_credits_remaining: remaining } : current,
    );
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, register, logout, refreshUser, setCredits }),
    [user, loading, login, register, logout, refreshUser, setCredits],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth doit être utilisé à l'intérieur d'un AuthProvider.");
  }
  return context;
}
