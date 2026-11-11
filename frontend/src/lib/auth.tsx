import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { ApiError, api, setAuthFailureHandler } from "./api";
import { supabase } from "./supabase";
import type { User } from "./types";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  restoreError: string | null;
  signIn: (email: string, password: string) => Promise<void>;
  signInWithGoogle: () => Promise<void>;
  signUp: (input: {
    full_name: string;
    email: string;
    phone_number: string;
    password: string;
  }) => Promise<boolean>;
  requestPasswordReset: (email: string) => Promise<void>;
  updatePassword: (password: string) => Promise<void>;
  resendVerification: (email: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshProfile: () => Promise<void>;
  switchRole: (role: User["role"]) => Promise<void>;
  retryRestore: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function redirectUrl(path: string) {
  return `${window.location.origin}${path}`;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [restoreError, setRestoreError] = useState<string | null>(null);
  const profileLoadVersion = useRef(0);

  const loadProfile = useCallback(async (accessToken: string, throwOnError = false) => {
    const version = ++profileLoadVersion.current;
    setToken(accessToken);
    setIsLoading(true);
    setRestoreError(null);
    try {
      const profile = await api.me(accessToken);
      if (version === profileLoadVersion.current) setUser(profile);
    } catch (reason) {
      if (version === profileLoadVersion.current) {
        setUser(null);
        setRestoreError(
          reason instanceof ApiError && reason.status === 401
            ? "Your sign-in session is no longer valid. Please sign in again."
            : reason instanceof Error
              ? reason.message
              : "Could not restore your account.",
        );
      }
      if (throwOnError) throw reason;
    } finally {
      if (version === profileLoadVersion.current) setIsLoading(false);
    }
  }, []);

  const retryRestore = useCallback(async () => {
    setIsLoading(true);
    setRestoreError(null);
    try {
      const { data, error } = await supabase.auth.getSession();
      if (error) throw error;
      if (data.session) {
        await loadProfile(data.session.access_token);
      } else {
        setToken(null);
        setUser(null);
      }
    } catch (reason) {
      setToken(null);
      setUser(null);
      setRestoreError(reason instanceof Error ? reason.message : "Could not restore your session.");
    } finally {
      setIsLoading(false);
    }
  }, [loadProfile]);

  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      ++profileLoadVersion.current;
      if (!session) {
        setToken(null);
        setUser(null);
        setRestoreError(null);
        setIsLoading(false);
        return;
      }
      queueMicrotask(() => void loadProfile(session.access_token));
    });
    setAuthFailureHandler(() => {
      ++profileLoadVersion.current;
      setToken(null);
      setUser(null);
      setRestoreError("Your sign-in session has expired. Please sign in again.");
      setIsLoading(false);
      window.location.assign("/login");
    });
    void retryRestore();
    return () => {
      subscription.unsubscribe();
      setAuthFailureHandler(null);
    };
  }, [loadProfile, retryRestore]);

  const signIn = useCallback(async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
    if (!data.session) throw new Error("Supabase did not return a sign-in session.");
    await loadProfile(data.session.access_token, true);
  }, [loadProfile]);

  const signInWithGoogle = useCallback(async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: redirectUrl("/account") },
    });
    if (error) throw error;
  }, []);

  const signUp = useCallback(async (input: {
    full_name: string;
    email: string;
    phone_number: string;
    password: string;
  }) => {
    const { data, error } = await supabase.auth.signUp({
      email: input.email,
      password: input.password,
      options: {
        data: {
          full_name: input.full_name,
          phone_number: input.phone_number,
        },
        emailRedirectTo: redirectUrl("/login"),
      },
    });
    if (error) throw error;
    if (data.session) await loadProfile(data.session.access_token, true);
    return !data.session;
  }, [loadProfile]);

  const requestPasswordReset = useCallback(async (email: string) => {
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: redirectUrl("/reset-password"),
    });
    if (error) throw error;
  }, []);

  const updatePassword = useCallback(async (password: string) => {
    const { error } = await supabase.auth.updateUser({ password });
    if (error) throw error;
  }, []);

  const resendVerification = useCallback(async (email: string) => {
    const { error } = await supabase.auth.resend({
      type: "signup",
      email,
      options: { emailRedirectTo: redirectUrl("/login") },
    });
    if (error) throw error;
  }, []);

  const signOut = useCallback(async () => {
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
    setUser(null);
    setToken(null);
    setRestoreError(null);
  }, []);

  const refreshProfile = useCallback(async () => {
    if (!token) throw new Error("Please sign in again.");
    setUser(await api.me(token));
  }, [token]);

  const switchRole = useCallback(async (role: User["role"]) => {
    if (!token) throw new Error("Please sign in again.");
    const profile = await api.setActiveRole(role, token);
    setUser(profile);
  }, [token]);

  const value = useMemo(
    () => ({
      user,
      token,
      isLoading,
      restoreError,
      signIn,
      signInWithGoogle,
      signUp,
      requestPasswordReset,
      updatePassword,
      resendVerification,
      signOut,
      refreshProfile,
      switchRole,
      retryRestore,
    }),
    [
      user,
      token,
      isLoading,
      restoreError,
      signIn,
      signInWithGoogle,
      signUp,
      requestPasswordReset,
      updatePassword,
      resendVerification,
      signOut,
      refreshProfile,
      switchRole,
      retryRestore,
    ],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within AuthProvider");
  return value;
}
