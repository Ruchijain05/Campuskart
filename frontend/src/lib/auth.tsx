import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api } from "./api";
import type { User } from "./types";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);

  const signIn = useCallback(async (email: string, password: string) => {
    const accessToken = await api.login(email, password);
    const profile = await api.me(accessToken);
    setToken(accessToken);
    setUser(profile);
  }, []);

  const signOut = useCallback(async () => {
    const currentToken = token;
    setUser(null);
    setToken(null);
    if (currentToken) await api.logout(currentToken);
  }, [token]);

  const refreshProfile = useCallback(async () => {
    if (!token) throw new Error("Please sign in again.");
    setUser(await api.me(token));
  }, [token]);

  const value = useMemo(
    () => ({ user, token, signIn, signOut, refreshProfile }),
    [user, token, signIn, signOut, refreshProfile],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within AuthProvider");
  return value;
}
