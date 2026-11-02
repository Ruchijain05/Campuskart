import { useEffect, useState, type FormEvent } from "react";
import { LifeBuoy, Send } from "lucide-react";
import { LoadingState, Notice } from "../../components/SiteLayout";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import type { AdminSupportTicket, AdminSupportTicketDetail, SupportTicketStatus } from "../../lib/types";

const statuses: SupportTicketStatus[] = ["open", "in_progress", "resolved", "closed"];
const statusLabels: Record<SupportTicketStatus, string> = { open: "Open", in_progress: "In Progress", resolved: "Resolved", closed: "Closed" };

export function AdminSupportTickets() {
  const { token } = useAuth();
  const [tickets, setTickets] = useState<AdminSupportTicket[]>([]);
  const [selected, setSelected] = useState<AdminSupportTicketDetail | null>(null);
  const [reply, setReply] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function reload() {
    if (!token) return;
    setTickets(await api.listAdminSupportTickets(token));
  }

  useEffect(() => {
    let active = true;
    if (!token) return;
    api.listAdminSupportTickets(token).then((items) => { if (active) setTickets(items); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Could not load support tickets."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token]);

  async function selectTicket(ticket: AdminSupportTicket) {
    if (!token) return;
    setError("");
    try { setSelected(await api.getAdminSupportTicket(ticket.id, token)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load this ticket."); }
  }

  async function changeStatus(next: SupportTicketStatus) {
    if (!token || !selected) return;
    setBusy(true); setError(""); setSuccess("");
    try {
      const updated = await api.updateSupportTicketStatus(selected.id, next, token);
      setSelected(updated); await reload();
      setSuccess(`Ticket #${updated.id} is now ${statusLabels[updated.status]}.`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not update ticket status."); }
    finally { setBusy(false); }
  }

  async function sendReply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !selected) return;
    setBusy(true); setError(""); setSuccess("");
    try {
      const updated = await api.replySupportTicket(selected.id, reply, token);
      setSelected(updated); setReply(""); await reload();
      setSuccess(`Reply sent to ${updated.buyer_name}.`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not send reply."); }
    finally { setBusy(false); }
  }

  return <section className="admin-card admin-support-card">
    <div className="form-card-heading"><span className="card-icon"><LifeBuoy size={19} /></span><div><h2>Customer support</h2><p>Review buyer requests, reply, and update ticket status.</p></div><span className="count-badge">{tickets.length}</span></div>
    {error && <Notice tone="error">{error}</Notice>}{success && <Notice tone="success">{success}</Notice>}
    {loading ? <LoadingState label="Loading support tickets..." /> : <div className="admin-support-layout">
      <div className="admin-support-ticket-list">{tickets.length ? tickets.map((ticket) => <button type="button" key={ticket.id} className={selected?.id === ticket.id ? "is-selected" : ""} onClick={() => void selectTicket(ticket)}>
        <b>#{ticket.id} · {ticket.subject}</b><small>{ticket.buyer_name} · {ticket.category}</small><i className={`ticket-status ticket-status-${ticket.status}`}>{statusLabels[ticket.status]}</i>
      </button>) : <p className="support-empty">No support tickets yet.</p>}</div>
      {selected ? <article className="admin-support-detail">
        <div className="admin-support-detail-header"><div><span className="eyebrow">TICKET #{selected.id}</span><h3>{selected.subject}</h3><p>{selected.buyer_name} · {selected.buyer_email}</p></div>
          <label>Status<select value={selected.status} disabled={busy} onChange={(event) => void changeStatus(event.target.value as SupportTicketStatus)}>{statuses.map((status) => <option key={status} value={status}>{statusLabels[status]}</option>)}</select></label>
        </div>
        <div className="ticket-message ticket-message-buyer"><b>{selected.buyer_name} · {selected.category}</b><p>{selected.description}</p></div>
        {selected.messages.map((message) => <div className="ticket-message ticket-message-admin" key={message.id}><b>{message.sender_name} · Admin</b><p>{message.body}</p><time>{new Date(message.created_at).toLocaleString()}</time></div>)}
        <form className="support-reply-form" onSubmit={(event) => void sendReply(event)}><label>Reply to buyer<textarea required maxLength={5000} rows={4} value={reply} onChange={(event) => setReply(event.target.value)} /></label><button className="button button-dark" disabled={busy}>{busy ? "Sending..." : "Send reply"} <Send size={15} /></button></form>
      </article> : <div className="support-empty support-select-hint">Select a ticket to view details and respond.</div>}
    </div>}
  </section>;
}
