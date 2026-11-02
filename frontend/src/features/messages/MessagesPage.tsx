import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ArrowUpRight, Check, MessageCircle, Send, X } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { LoadingState, Notice, PageTitle } from "../../components/SiteLayout";
import { useAuth } from "../../lib/auth";
import { api } from "../../lib/api";
import type { Conversation, ConversationDetail } from "../../lib/types";

export function MessagesPage() {
  const { token, user } = useAuth();
  const { conversationId } = useParams();
  const selectedId = conversationId ? Number(conversationId) : null;
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [thread, setThread] = useState<ConversationDetail | null>(null);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  const loadConversations = useCallback(async () => {
    if (!token) return;
    try { setConversations(await api.listConversations(token)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load your conversations."); }
    finally { setLoading(false); }
  }, [token]);

  useEffect(() => { void loadConversations(); }, [loadConversations]);
  useEffect(() => {
    if (!token || selectedId === null || !Number.isInteger(selectedId)) { setThread(null); return; }
    let active = true;
    api.getConversation(selectedId, token).then((item) => {
      if (!active) return;
      setThread(item);
      window.dispatchEvent(new Event("campuskart-messages-updated"));
      window.dispatchEvent(new Event("campuskart-notifications-updated"));
      void loadConversations();
    }).catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Could not open this conversation."); });
    return () => { active = false; };
  }, [token, selectedId, loadConversations]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      void loadConversations();
      if (token && selectedId !== null) api.getConversation(selectedId, token).then(setThread).catch(() => undefined);
    }, 15000);
    return () => window.clearInterval(timer);
  }, [token, selectedId, loadConversations]);

  async function send(event: FormEvent) {
    event.preventDefault();
    if (!token || !thread || !draft.trim()) return;
    setSending(true); setError("");
    try {
      setThread(await api.sendConversationMessage(thread.id, draft, token));
      setDraft(""); await loadConversations();
      window.dispatchEvent(new Event("campuskart-messages-updated"));
      window.dispatchEvent(new Event("campuskart-notifications-updated"));
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not send your message."); }
    finally { setSending(false); }
  }

  async function setStatus(status: "open" | "closed") {
    if (!token || !thread || user?.role !== "seller") return;
    try {
      await api.updateConversationStatus(thread.id, status, token);
      setThread(await api.getConversation(thread.id, token));
      await loadConversations();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not update this conversation."); }
  }

  return <section className="content-narrow messages-page">
    <PageTitle eyebrow="CAMPUSKART INBOX" title="Messages" description="Talk directly with buyers or sellers about products." />
    {error && <Notice tone="error">{error}</Notice>}
    <div className="messages-layout">
      <aside className="messages-inbox"><div className="messages-inbox-heading"><h2>Conversations</h2><span>{conversations.reduce((sum, item) => sum + item.unread_count, 0)} unread</span></div>
        {loading ? <LoadingState label="Loading conversations..." /> : conversations.length ? conversations.map((item) => <Link key={item.id} to={`/messages/${item.id}`} className={`conversation-link${selectedId === item.id ? " is-selected" : ""}${item.unread_count ? " has-unread" : ""}`}>
          {item.product_image_url ? <img src={item.product_image_url} alt="" /> : <span className="conversation-placeholder"><MessageCircle size={18} /></span>}
          <span className="conversation-link-copy"><b>{item.other_party_name}</b><small>{item.product_name}</small><small>{item.last_message || "No messages yet"}</small></span>
          {item.unread_count > 0 && <b className="conversation-unread-count">{item.unread_count}</b>}
        </Link>) : <p className="messages-empty-inbox">No conversations yet. Open a product and message its seller.</p>}
      </aside>
      <section className="messages-thread">
        {!selectedId ? <div className="messages-thread-empty"><MessageCircle size={32} /><h2>Choose a conversation</h2><p>Select a chat to read messages and reply.</p></div> : !thread ? <LoadingState label="Opening conversation..." /> : <>
          <header className="messages-thread-heading"><div>{thread.product_image_url ? <img src={thread.product_image_url} alt="" /> : <span className="conversation-placeholder"><MessageCircle size={18} /></span>}<div><b>{thread.other_party_name}</b><Link to={`/products/${thread.product_id}`}>{thread.product_name} <ArrowUpRight size={13} /></Link></div></div><div><span className={`chat-status chat-${thread.status}`}>{thread.status}</span>{user?.role === "seller" && <button className="chat-close-button" type="button" onClick={() => void setStatus(thread.status === "open" ? "closed" : "open")}>{thread.status === "open" ? <><X size={14} /> Close</> : <><Check size={14} /> Reopen</>}</button>}</div></header>
          <div className="message-list">{thread.messages.map((message) => <article key={message.id} className={`chat-message${message.sender_id === user?.id ? " is-mine" : ""}`}><span>{message.sender_name}</span><p>{message.body}</p><small>{new Date(message.created_at).toLocaleString()}</small></article>)}{!thread.messages.length && <p className="messages-empty-inbox">Start the conversation with a message.</p>}</div>
          <form className="message-compose" onSubmit={(event) => void send(event)}><textarea required maxLength={4000} rows={2} value={draft} onChange={(event) => setDraft(event.target.value)} placeholder={`Message ${thread.other_party_name} about this product`} /><button className="button button-dark" disabled={sending || !draft.trim()}>{sending ? "Sending..." : "Send"} <Send size={15} /></button></form>
        </>}
      </section>
    </div>
  </section>;
}
