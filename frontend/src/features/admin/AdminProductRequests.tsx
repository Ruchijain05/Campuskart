import { useEffect, useState, type FormEvent } from "react";
import { ImagePlus, Send } from "lucide-react";
import { formatPrice } from "../../components/ProductCard";
import { LoadingState, Notice } from "../../components/SiteLayout";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import type { AdminProductRequest } from "../../lib/types";

export function AdminProductRequests() {
  const { token } = useAuth();
  const [requests, setRequests] = useState<AdminProductRequest[]>([]);
  const [selected, setSelected] = useState<AdminProductRequest | null>(null);
  const [canArrange, setCanArrange] = useState(true);
  const [price, setPrice] = useState("");
  const [deliveryDays, setDeliveryDays] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    let active = true;
    if (!token) return;
    api.listAdminProductRequests(token)
      .then((items) => { if (active) setRequests(items); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Could not load product requests."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token]);

  function selectRequest(request: AdminProductRequest) {
    setSelected(request);
    setCanArrange(request.can_arrange ?? true);
    setPrice(request.price == null ? "" : String(request.price));
    setDeliveryDays(request.expected_delivery_days == null ? "" : String(request.expected_delivery_days));
    setMessage(request.admin_message ?? "");
    setError("");
    setSuccess("");
  }

  async function respond(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !selected) return;
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      const updated = await api.respondToProductRequest(selected.id, {
        can_arrange: canArrange,
        price: canArrange ? Number(price) : null,
        expected_delivery_days: canArrange ? Number(deliveryDays) : null,
        admin_message: message,
      }, token);
      setRequests((current) => current.map((request) => request.id === updated.id ? updated : request));
      selectRequest(updated);
      setSuccess(`Response sent to ${updated.buyer_name}.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not send this response.");
    } finally {
      setBusy(false);
    }
  }

  return <section className="admin-card admin-product-requests">
    <div className="form-card-heading"><span className="card-icon"><ImagePlus size={19} /></span><div><h2>Product requests</h2><p>Review student requests for products not currently listed.</p></div><span className="count-badge">{requests.filter((request) => request.status === "pending").length} pending</span></div>
    {error && <Notice tone="error">{error}</Notice>}{success && <Notice tone="success">{success}</Notice>}
    {loading ? <LoadingState label="Loading product requests..." /> : <div className="admin-product-request-layout">
      <div className="admin-product-request-list">{requests.length ? requests.map((request) => (
        <button type="button" key={request.id} className={`admin-product-request-item${selected?.id === request.id ? " is-selected" : ""}`} onClick={() => selectRequest(request)}>
          <b>#{request.id} · {request.product_name}</b><small>{request.buyer_name} · Quantity {request.quantity}</small><span className={`product-request-status product-request-status-${request.status}`}>{request.status === "pending" ? "Pending" : "Responded"}</span>
        </button>
      )) : <p className="support-empty">No product requests yet.</p>}</div>
      {selected ? <article className="admin-product-request-detail">
        <div className="product-request-card-heading"><div><span className="eyebrow">REQUEST #{selected.id}</span><h3>{selected.product_name}</h3></div><span className={`product-request-status product-request-status-${selected.status}`}>{selected.status === "pending" ? "Pending" : "Responded"}</span></div>
        <p className="product-request-meta">{selected.buyer_name} · {selected.buyer_email}<br />Quantity: {selected.quantity} · {new Date(selected.created_at).toLocaleString()}</p>
        {selected.photo_url && <a href={selected.photo_url} target="_blank" rel="noreferrer" className="product-request-photo-link">View uploaded photo</a>}
        <div className="ticket-message ticket-message-buyer"><b>Student's message</b><p>{selected.message}</p></div>
        <form className="product-request-response-form" onSubmit={(event) => void respond(event)}>
          <label>Can this product be arranged?<select value={canArrange ? "yes" : "no"} disabled={busy} onChange={(event) => setCanArrange(event.target.value === "yes")}><option value="yes">Yes, we can arrange it</option><option value="no">No, we cannot arrange it</option></select></label>
          {canArrange && <div className="product-request-response-fields">
            <label>Price (₹)<input type="number" min="0" step="0.01" required value={price} onChange={(event) => setPrice(event.target.value)} /></label>
            <label>Expected delivery (days)<input type="number" min="1" max="365" step="1" required value={deliveryDays} onChange={(event) => setDeliveryDays(event.target.value)} /></label>
          </div>}
          <label>Message to student<textarea required minLength={1} maxLength={5000} rows={4} value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Add any useful details for the student." /></label>
          <button className="button button-dark" disabled={busy}>{busy ? "Sending response..." : "Send response"} <Send size={15} /></button>
        </form>
        {selected.status === "responded" && <p className="product-request-meta">Last responded {selected.responded_at ? new Date(selected.responded_at).toLocaleString() : ""}{selected.can_arrange && selected.price != null && <> · {formatPrice(selected.price)} · {selected.expected_delivery_days} day delivery</>}</p>}
      </article> : <div className="support-empty support-select-hint">Select a student request to review and respond.</div>}
    </div>}
  </section>;
}
