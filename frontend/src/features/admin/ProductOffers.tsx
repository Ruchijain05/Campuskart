import { useEffect, useState, type FormEvent } from "react";
import { Notice } from "../../components/SiteLayout";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import type { Product, ProductOfferInput } from "../../lib/types";
import { formatPrice } from "../../components/ProductCard";

function localDateTime(value: string | null) {
  if (!value) return "";
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

export function ProductOffers() {
  const { token } = useAuth();
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [discountType, setDiscountType] = useState<"fixed" | "percentage">("percentage");
  const [discountValue, setDiscountValue] = useState("");
  const [startsAt, setStartsAt] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);
  const selected = products.find((product) => String(product.id) === selectedId);

  async function refresh(preferredId?: string) {
    if (!token) return;
    const items = await api.listAdminOfferProducts(token);
    setProducts(items);
    const nextId = preferredId || selectedId || (items[0] ? String(items[0].id) : "");
    setSelectedId(nextId);
    const product = items.find((item) => String(item.id) === nextId);
    if (product) {
      setDiscountType(product.offer_discount_type ?? "percentage");
      setDiscountValue(product.offer_discount_value == null ? "" : String(product.offer_discount_value));
      setStartsAt(localDateTime(product.offer_starts_at));
      setEndsAt(localDateTime(product.offer_ends_at));
    }
  }

  useEffect(() => { void refresh().catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Could not load products.")); }, [token]);

  function selectProduct(id: string) {
    setSelectedId(id);
    const product = products.find((item) => String(item.id) === id);
    setDiscountType(product?.offer_discount_type ?? "percentage");
    setDiscountValue(product?.offer_discount_value == null ? "" : String(product.offer_discount_value));
    setStartsAt(localDateTime(product?.offer_starts_at ?? null));
    setEndsAt(localDateTime(product?.offer_ends_at ?? null));
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!token || !selected) return;
    setError(""); setSuccess(""); setBusy(true);
    try {
      const payload: ProductOfferInput = { discount_type: discountType, discount_value: Number(discountValue), starts_at: new Date(startsAt).toISOString(), ends_at: new Date(endsAt).toISOString(), is_active: true };
      await api.saveProductOffer(selected.id, payload, token);
      await refresh(String(selected.id));
      setSuccess("Offer saved.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not save offer."); }
    finally { setBusy(false); }
  }

  async function disable() {
    if (!token || !selected) return;
    setError(""); setSuccess(""); setBusy(true);
    try { await api.disableProductOffer(selected.id, token); await refresh(String(selected.id)); setSuccess("Offer disabled."); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not disable offer."); }
    finally { setBusy(false); }
  }

  return <section className="admin-panel product-offers-panel">
    <div className="section-heading"><div><span className="eyebrow">PROMOTIONS</span><h2>Product offers & flash sales</h2><p>Schedule a product discount. The regular price stays unchanged.</p></div></div>
    {error && <Notice tone="error">{error}</Notice>}{success && <Notice>{success}</Notice>}
    {!products.length ? <p>No products are available to manage.</p> : <form className="product-offer-form" onSubmit={save}>
      <label>Product<select value={selectedId} onChange={(event) => selectProduct(event.target.value)}>{products.map((product) => <option value={product.id} key={product.id}>{product.name} — {formatPrice(product.price)}</option>)}</select></label>
      <label>Discount type<select value={discountType} onChange={(event) => setDiscountType(event.target.value as "fixed" | "percentage")}><option value="percentage">Percentage (%)</option><option value="fixed">Fixed amount (₹)</option></select></label>
      <label>Discount value<input type="number" min="0.01" max={discountType === "percentage" ? 100 : undefined} step="0.01" required value={discountValue} onChange={(event) => setDiscountValue(event.target.value)} /></label>
      <label>Starts at<input type="datetime-local" required value={startsAt} onChange={(event) => setStartsAt(event.target.value)} /></label>
      <label>Ends at<input type="datetime-local" required value={endsAt} onChange={(event) => setEndsAt(event.target.value)} /></label>
      {selected?.offer_active && <p>Current offer price: <b>{formatPrice(selected.offer_price ?? selected.price)}</b></p>}
      <div className="form-actions"><button className="button button-dark" disabled={busy}>{busy ? "Saving…" : "Save offer"}</button>{selected?.offer_is_active && <button className="button button-outline" type="button" onClick={() => void disable()} disabled={busy}>Disable offer</button>}</div>
    </form>}
  </section>;
}
