import { useEffect, useState, type FormEvent } from "react";
import { LifeBuoy, Send } from "lucide-react";
import { LoadingState, Notice, PageTitle } from "../../components/SiteLayout";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import type { SupportTicket, SupportTicketCategory, SupportTicketDetail } from "../../lib/types";

const initialForm = { subject: "", category: "order" as SupportTicketCategory, description: "" };

function statusLabel(status: SupportTicket["status"]) {
  return status === "in_progress" ? "In Progress" : status.charAt(0).toUpperCase() + status.slice(1);
}

export function SupportPage() {
  const { token } = useAuth();
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [selected, setSelected] = useState<SupportTicketDetail | null>(null);
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function refreshTickets() {
    if (!token) return;
    setTickets(await api.listSupportTickets(token));
  }

  useEffect(() => {
    let active = true;
    if (!token) return;
    api.listSupportTickets(token).then((items) => { if (active) setTickets(items); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Could not load your tickets."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token]);

  async function openTicket(ticket: SupportTicket) {
    if (!token) return;
    setError("");
    try { setSelected(await api.getSupportTicket(ticket.id, token)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load this ticket."); }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setBusy(true); setError(""); setSuccess("");
    try {
      const created = await api.createSupportTicket(form, token);
      setSelected(await api.getSupportTicket(created.id, token));
      await refreshTickets();
      setForm(initialForm);
      setSuccess(`Support ticket #${created.id} submitted.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not submit your ticket.");
    } finally { setBusy(false); }
  }

  return <section className="content-narrow support-page">
    <PageTitle eyebrow="WE'RE HERE TO HELP" title="Customer support" description="Send us a message and track replies and status updates here." />
    {error && <Notice tone="error">{error}</Notice>}{success && <Notice tone="success">{success}</Notice>}
    <div className="support-layout">
      <form className="form-card support-form" onSubmit={(event) => void submit(event)}>
        <div className="form-card-heading"><span className="card-icon"><LifeBuoy size={19} /></span><div><h2>Submit a ticket</h2><p>Tell our team what you need help with.</p></div></div>
        <label>Subject<input required maxLength={160} value={form.subject} onChange={(event) => setForm((current) => ({ ...current, subject: event.target.value }))} /></label>
        <label>Category<select value={form.category} onChange={(event) => setForm((current) => ({ ...current, category: event.target.value as SupportTicketCategory }))}><option value="order">Order</option><option value="product">Product</option><option value="payment">Payment</option><option value="account">Account</option><option value="other">Other</option></select></label>
        <label>Description<textarea required minLength={1} maxLength={5000} rows={6} value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} /></label>
        <button className="button button-dark" disabled={busy}>{busy ? "Submitting..." : "Submit ticket"} <Send size={15} /></button>
      </form>
      <section className="support-ticket-list" aria-labelledby="my-tickets-heading">
        <div className="support-section-heading"><div><span className="eyebrow">YOUR REQUESTS</span><h2 id="my-tickets-heading">My tickets</h2></div><span>{tickets.length}</span></div>
        {loading ? <LoadingState label="Loading tickets..." /> : tickets.length ? <div className="support-ticket-items">{tickets.map((ticket) => <button type="button" key={ticket.id} className={`support-ticket-list-item${selected?.id === ticket.id ? " is-selected" : ""}`} onClick={() => void openTicket(ticket)}>
          <span><b>#{ticket.id} · {ticket.subject}</b><small>{ticket.category} · Updated {new Date(ticket.updated_at).toLocaleString()}</small></span><i className={`ticket-status ticket-status-${ticket.status}`}>{statusLabel(ticket.status)}</i>
        </button>)}</div> : <div className="support-empty">You have not submitted a support ticket yet.</div>}
        {selected && <article className="support-ticket-detail">
          <div className="support-ticket-detail-heading"><div><span className="eyebrow">TICKET #{selected.id}</span><h3>{selected.subject}</h3></div><i className={`ticket-status ticket-status-${selected.status}`}>{statusLabel(selected.status)}</i></div>
          <p className="support-ticket-category">{selected.category} · Opened {new Date(selected.created_at).toLocaleString()}</p>
          <div className="ticket-message ticket-message-buyer"><b>Your request</b><p>{selected.description}</p></div>
          {selected.messages.map((message) => <div className="ticket-message ticket-message-admin" key={message.id}><b>{message.sender_name} · Support</b><p>{message.body}</p><time>{new Date(message.created_at).toLocaleString()}</time></div>)}
        </article>}
      </section>
    </div>
  </section>;
}
