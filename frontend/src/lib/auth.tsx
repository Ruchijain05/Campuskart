import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { ApiError, api } from "./api";
import type { User } from "./types";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  restoreError: string | null;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshProfile: () => Promise<void>;
  retryRestore: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [restoreError, setRestoreError] = useState<string | null>(null);

  const retryRestore = useCallback(async () => {
    setIsLoading(true);
    setRestoreError(null);
    try {
      const accessToken = await api.refreshAccessToken();
      const profile = await api.me(accessToken);
      setToken(accessToken);
      setUser(profile);
    } catch (reason) {
      setToken(null);
      setUser(null);
      if (reason instanceof ApiError && reason.status === 401) {
        setRestoreError(null);
      } else {
        setRestoreError(reason instanceof Error ? reason.message : "Could not restore your session.");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    api.setRefreshedTokenHandler(setToken);
    return () => api.setRefreshedTokenHandler(null);
  }, []);

  useEffect(() => {
    void retryRestore();
  }, [retryRestore]);

  const signIn = useCallback(async (email: string, password: string) => {
    const accessToken = await api.login(email, password);
    const profile = await api.me(accessToken);
    setToken(accessToken);
    setUser(profile);
    setRestoreError(null);
  }, []);

  const signOut = useCallback(async () => {
    const currentToken = token;
    if (currentToken) await api.logout(currentToken);
    setUser(null);
    setToken(null);
    setRestoreError(null);
  }, [token]);

  const refreshProfile = useCallback(async () => {
    if (!token) throw new Error("Please sign in again.");
    setUser(await api.me(token));
  }, [token]);

  const value = useMemo(
    () => ({ user, token, isLoading, restoreError, signIn, signOut, refreshProfile, retryRestore }),
    [user, token, isLoading, restoreError, signIn, signOut, refreshProfile, retryRestore],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within AuthProvider");
  return value;
}
