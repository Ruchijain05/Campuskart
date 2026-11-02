import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useAuth } from "./auth";
import { api } from "./api";

interface NotificationsContextValue {
  unreadCount: number;
  refreshUnreadCount: () => Promise<void>;
}

const NotificationsContext = createContext<NotificationsContextValue | null>(null);

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const { token, user } = useAuth();
  const [unreadCount, setUnreadCount] = useState(0);

  const refreshUnreadCount = useCallback(async () => {
    if (!token || user?.role !== "buyer") {
      setUnreadCount(0);
      return;
    }
    try {
      const result = await api.getUnreadNotificationCount(token);
      setUnreadCount(result.unread_count);
    } catch {
      // Keep the current badge if a temporary request fails.
    }
  }, [token, user?.role]);

  useEffect(() => {
    setUnreadCount(0);
    void refreshUnreadCount();
  }, [refreshUnreadCount, user?.id]);

  useEffect(() => {
    if (!token || user?.role !== "buyer") return;
    const timer = window.setInterval(() => void refreshUnreadCount(), 45_000);
    const onUpdate = () => void refreshUnreadCount();
    window.addEventListener("campuskart-notifications-updated", onUpdate);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("campuskart-notifications-updated", onUpdate);
    };
  }, [token, user?.role, refreshUnreadCount]);

  const value = useMemo(() => ({ unreadCount, refreshUnreadCount }), [unreadCount, refreshUnreadCount]);
  return <NotificationsContext.Provider value={value}>{children}</NotificationsContext.Provider>;
}

export function useNotifications() {
  const value = useContext(NotificationsContext);
  if (!value) throw new Error("useNotifications must be used within NotificationsProvider");
  return value;
}
