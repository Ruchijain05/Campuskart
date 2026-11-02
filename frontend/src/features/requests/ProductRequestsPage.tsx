import { useEffect, useRef, useState, type FormEvent } from "react";
import { ImagePlus, Send } from "lucide-react";
import { LoadingState, Notice, PageTitle } from "../../components/SiteLayout";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import type { ProductRequest } from "../../lib/types";
import { formatPrice } from "../../components/ProductCard";

const emptyForm = { product_name: "", quantity: "1", message: "" };

export function ProductRequestsPage() {
  const { token } = useAuth();
  const [requests, setRequests] = useState<ProductRequest[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [photo, setPhoto] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    let active = true;
    if (!token) return;
    api.listProductRequests(token)
      .then((items) => { if (active) setRequests(items); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Could not load your requests."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      const created = await api.createProductRequest({
        product_name: form.product_name,
        quantity: Number(form.quantity),
        message: form.message,
        photo,
      }, token);
      setRequests((current) => [created, ...current]);
      setForm(emptyForm);
      setPhoto(null);
      formRef.current?.reset();
      setSuccess(`Request #${created.id} sent to CampusKart admins.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not submit your request.");
    } finally {
      setBusy(false);
    }
  }

  return <section className="content-narrow product-requests-page">
    <PageTitle eyebrow="CAN'T FIND IT?" title="Request anything" description="Tell us what you need—even if it isn't listed. Our team will check whether we can arrange it and get back to you here." />
    {error && <Notice tone="error">{error}</Notice>}
    {success && <Notice tone="success">{success}</Notice>}
    <div className="product-request-layout">
      <form ref={formRef} className="form-card product-request-form" onSubmit={(event) => void submit(event)}>
        <div className="form-card-heading"><span className="card-icon"><ImagePlus size={19} /></span><div><h2>What are you looking for?</h2><p>Share the details and a photo if you have one.</p></div></div>
        <label>Product name<input required minLength={1} maxLength={160} value={form.product_name} onChange={(event) => setForm((current) => ({ ...current, product_name: event.target.value }))} placeholder="e.g. A3 drawing board" /></label>
        <label>Quantity<input type="number" min="1" max="100000" required value={form.quantity} onChange={(event) => setForm((current) => ({ ...current, quantity: event.target.value }))} /></label>
        <label>Message to the admin<textarea required minLength={1} maxLength={5000} rows={5} value={form.message} onChange={(event) => setForm((current) => ({ ...current, message: event.target.value }))} placeholder="Add size, color, brand, or any other details that will help us find it." /></label>
        <label>Product photo <span className="optional-label">OPTIONAL · JPEG, PNG, OR WEBP · MAX 5 MB</span><input type="file" accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp" onChange={(event) => setPhoto(event.target.files?.[0] ?? null)} /></label>
        {photo && <small className="field-hint">Selected: {photo.name}</small>}
        <button className="button button-dark" disabled={busy}>{busy ? "Sending request..." : "Send request"} <Send size={15} /></button>
      </form>

      <section className="product-request-list" aria-labelledby="my-product-requests">
        <div className="support-section-heading"><div><span className="eyebrow">TRACK YOUR REQUESTS</span><h2 id="my-product-requests">My requests</h2></div><span>{requests.length}</span></div>
        {loading ? <LoadingState label="Loading your requests..." /> : requests.length ? requests.map((request) => (
          <article className="product-request-card" key={request.id}>
            <div className="product-request-card-heading"><div><span className="eyebrow">REQUEST #{request.id}</span><h3>{request.product_name}</h3></div><span className={`product-request-status product-request-status-${request.status}`}>{request.status === "pending" ? "Awaiting response" : "Response received"}</span></div>
            <p className="product-request-meta">Quantity: {request.quantity} · Sent {new Date(request.created_at).toLocaleString()}</p>
            {request.photo_url && <a className="product-request-photo-link" href={request.photo_url} target="_blank" rel="noreferrer">View your product photo</a>}
            <p className="product-request-message">{request.message}</p>
            {request.status === "responded" && <div className="product-request-response">
              <b>{request.can_arrange ? "We can arrange this" : "We cannot arrange this"}</b>
              {request.can_arrange && <p>Price: {formatPrice(request.price ?? 0)} · Expected delivery: {request.expected_delivery_days} day{request.expected_delivery_days === 1 ? "" : "s"}</p>}
              <p>{request.admin_message}</p>
            </div>}
          </article>
        )) : <div className="support-empty">Your submitted requests and admin responses will appear here.</div>}
      </section>
    </div>
  </section>;
}
