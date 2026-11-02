import { useEffect, useState, type FormEvent } from "react";
import { Check, Pencil, Tag, X } from "lucide-react";
import { Notice, LoadingState } from "../../components/SiteLayout";
import { formatPrice } from "../../components/ProductCard";
import { useAuth } from "../../lib/auth";
import { api } from "../../lib/api";
import type { Coupon, CouponInput, CouponDiscountType } from "../../lib/types";

type CouponForm = {
  code: string;
  discount_type: CouponDiscountType;
  discount_value: string;
  minimum_order_amount: string;
  maximum_discount: string;
  usage_limit: string;
  starts_at: string;
  ends_at: string;
  is_active: boolean;
};

const emptyForm: CouponForm = {
  code: "", discount_type: "percentage", discount_value: "10",
  minimum_order_amount: "0", maximum_discount: "", usage_limit: "",
  starts_at: "", ends_at: "", is_active: true,
};

function dateField(value: string | null) {
  return value ? new Date(value).toISOString().slice(0, 16) : "";
}

function toPayload(form: CouponForm): CouponInput {
  return {
    code: form.code.trim().toUpperCase(),
    discount_type: form.discount_type,
    discount_value: Number(form.discount_value),
    minimum_order_amount: Number(form.minimum_order_amount || 0),
    maximum_discount: form.maximum_discount ? Number(form.maximum_discount) : null,
    usage_limit: form.usage_limit ? Number(form.usage_limit) : null,
    starts_at: form.starts_at ? new Date(form.starts_at).toISOString() : null,
    ends_at: form.ends_at ? new Date(form.ends_at).toISOString() : null,
    is_active: form.is_active,
  };
}

function couponForm(coupon: Coupon): CouponForm {
  return {
    code: coupon.code,
    discount_type: coupon.discount_type,
    discount_value: String(coupon.discount_value),
    minimum_order_amount: String(coupon.minimum_order_amount),
    maximum_discount: coupon.maximum_discount === null ? "" : String(coupon.maximum_discount),
    usage_limit: coupon.usage_limit === null ? "" : String(coupon.usage_limit),
    starts_at: dateField(coupon.starts_at),
    ends_at: dateField(coupon.ends_at),
    is_active: coupon.is_active,
  };
}

export function CouponManagement() {
  const { token } = useAuth();
  const [coupons, setCoupons] = useState<Coupon[]>([]);
  const [form, setForm] = useState<CouponForm>(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function load() {
    if (!token) return;
    setLoading(true);
    try {
      setCoupons(await api.listAdminCoupons(token));
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load coupons.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [token]);

  function cancelEdit() {
    setEditingId(null);
    setForm(emptyForm);
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setBusy(true); setError(""); setSuccess("");
    try {
      const payload = toPayload(form);
      if (editingId === null) {
        const created = await api.createCoupon(payload, token);
        setCoupons((current) => [created, ...current]);
        setSuccess(`Coupon ${created.code} created.`);
      } else {
        const updated = await api.updateCoupon(editingId, payload, token);
        setCoupons((current) => current.map((item) => item.id === updated.id ? updated : item));
        setSuccess(`Coupon ${updated.code} updated.`);
      }
      cancelEdit();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save this coupon.");
    } finally {
      setBusy(false);
    }
  }

  async function toggle(coupon: Coupon) {
    if (!token) return;
    setError(""); setSuccess("");
    try {
      const updated = await api.updateCoupon(coupon.id, { is_active: !coupon.is_active }, token);
      setCoupons((current) => current.map((item) => item.id === updated.id ? updated : item));
      setSuccess(`Coupon ${updated.code} ${updated.is_active ? "enabled" : "disabled"}.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not update this coupon.");
    }
  }

  const update = (field: keyof CouponForm, value: string | boolean) => setForm((current) => ({ ...current, [field]: value }));

  return <section className="admin-card admin-coupons-card">
    <div className="form-card-heading"><span className="card-icon"><Tag size={19} /></span><div><h2>Coupons &amp; discounts</h2><p>Create discount codes and control when buyers can use them.</p></div><span className="count-badge">{coupons.length}</span></div>
    {error && <Notice tone="error">{error}</Notice>}{success && <Notice tone="success">{success}</Notice>}
    <form className="coupon-admin-form" onSubmit={(event) => void save(event)}>
      <label>Coupon code<input required minLength={3} maxLength={32} pattern="[A-Za-z0-9_-]+" value={form.code} onChange={(event) => update("code", event.target.value.toUpperCase())} placeholder="WELCOME10" /></label>
      <label>Discount type<select value={form.discount_type} onChange={(event) => update("discount_type", event.target.value as CouponDiscountType)}><option value="percentage">Percentage</option><option value="fixed">Fixed amount (INR)</option></select></label>
      <label>Discount value<input required type="number" min="0.01" max={form.discount_type === "percentage" ? 100 : undefined} step="0.01" value={form.discount_value} onChange={(event) => update("discount_value", event.target.value)} /></label>
      <label>Minimum order (INR)<input type="number" min="0" step="0.01" value={form.minimum_order_amount} onChange={(event) => update("minimum_order_amount", event.target.value)} /></label>
      <label>Maximum discount (INR)<input type="number" min="0.01" step="0.01" value={form.maximum_discount} onChange={(event) => update("maximum_discount", event.target.value)} placeholder="No limit" /></label>
      <label>Total uses limit<input type="number" min="1" step="1" value={form.usage_limit} onChange={(event) => update("usage_limit", event.target.value)} placeholder="Unlimited" /></label>
      <label>Starts at<input type="datetime-local" value={form.starts_at} onChange={(event) => update("starts_at", event.target.value)} /></label>
      <label>Ends at<input type="datetime-local" value={form.ends_at} onChange={(event) => update("ends_at", event.target.value)} /></label>
      <label className="coupon-active-check"><input type="checkbox" checked={form.is_active} onChange={(event) => update("is_active", event.target.checked)} /> Enabled</label>
      <div className="coupon-form-actions"><button className="button button-dark" disabled={busy}>{busy ? "Saving..." : editingId === null ? "Create coupon" : "Save changes"}</button>{editingId !== null && <button type="button" className="button button-light" onClick={cancelEdit}><X size={15} /> Cancel</button>}</div>
    </form>
    {loading ? <LoadingState label="Loading coupons..." /> : coupons.length ? <div className="coupon-admin-list">{coupons.map((coupon) => <article key={coupon.id} className="coupon-admin-item">
      <div><b>{coupon.code}</b><span>{coupon.discount_type === "percentage" ? `${coupon.discount_value}% off` : `${formatPrice(coupon.discount_value)} off`}{coupon.maximum_discount !== null && coupon.discount_type === "percentage" ? ` (up to ${formatPrice(coupon.maximum_discount)})` : ""}</span><small>Minimum {formatPrice(coupon.minimum_order_amount)} · Uses {coupon.used_count}{coupon.usage_limit === null ? " / unlimited" : ` / ${coupon.usage_limit}`}</small></div>
      <span className={`coupon-active-badge ${coupon.is_active ? "is-active" : ""}`}>{coupon.is_active ? "Enabled" : "Disabled"}</span>
      <div className="category-actions"><button type="button" aria-label={`Edit ${coupon.code}`} onClick={() => { setEditingId(coupon.id); setForm(couponForm(coupon)); }}><Pencil size={15} /></button><button type="button" aria-label={`${coupon.is_active ? "Disable" : "Enable"} ${coupon.code}`} onClick={() => void toggle(coupon)}>{coupon.is_active ? <X size={16} /> : <Check size={16} />}</button></div>
    </article>)}</div> : <div className="empty-admin"><span>✦</span><p>No coupons yet. Create one above.</p></div>}
  </section>;
}
