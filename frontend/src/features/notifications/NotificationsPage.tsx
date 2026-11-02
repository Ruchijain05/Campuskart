import { useCallback, useEffect, useState } from "react";
import { Bell, Check, CheckCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { PageTitle, LoadingState, Notice } from "../../components/SiteLayout";
import { useAuth } from "../../lib/auth";
import { useNotifications } from "../../lib/notifications";
import { api } from "../../lib/api";
import type { Notification } from "../../lib/types";

export function NotificationsPage() {
  const { token } = useAuth();
  const { refreshUnreadCount } = useNotifications();
  const [items, setItems] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const result = await api.listNotifications(token);
      setItems(result.notifications);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load notifications.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  async function markOneRead(id: number) {
    if (!token) return;
    try {
      const updated = await api.markNotificationRead(id, token);
      setItems((current) => current.map((item) => item.id === id ? updated : item));
      void refreshUnreadCount();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update notification.");
    }
  }

  async function markAllRead() {
    if (!token) return;
    try {
      await api.markAllNotificationsRead(token);
      setItems((current) => current.map((item) => ({ ...item, is_read: true })));
      void refreshUnreadCount();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update notifications.");
    }
  }

  return (
    <section className="content-narrow notifications-page">
      <PageTitle eyebrow="YOUR ACCOUNT" title="Notifications" description="Order updates and important account activity." />
      {error && <Notice tone="error">{error}</Notice>}
      {items.some((item) => !item.is_read) && (
        <div className="notification-toolbar">
          <span>{items.filter((item) => !item.is_read).length} unread</span>
          <button className="notification-mark-all" type="button" onClick={() => void markAllRead()}><CheckCheck size={15} /> Mark all as read</button>
        </div>
      )}
      {loading ? <LoadingState label="Loading notifications..." /> : items.length ? (
        <div className="notification-list">
          {items.map((item) => (
            <article className={`notification-card${item.is_read ? " is-read" : " is-unread"}`} key={item.id}>
              <span className="notification-icon"><Bell size={17} /></span>
              <div className="notification-copy">
                <div className="notification-heading"><h2>{item.title}</h2><time>{new Date(item.created_at).toLocaleString()}</time></div>
                <p>{item.message}</p>
                {item.link && <Link to={item.link} className="notification-open">View details</Link>}
              </div>
              {!item.is_read && <button type="button" className="notification-read-button" onClick={() => void markOneRead(item.id)} aria-label="Mark as read"><Check size={16} /> Mark read</button>}
            </article>
          ))}
        </div>
      ) : (
        <div className="empty-state notification-empty"><span className="empty-emoji"><Bell size={24} /></span><h3>You’re all caught up</h3><p>Important account and order updates will show here.</p></div>
      )}
    </section>
  );
}
