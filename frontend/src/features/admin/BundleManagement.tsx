import { useEffect, useState, type FormEvent } from "react";
import { Check, Package, Pencil, Plus, X } from "lucide-react";
import { Notice } from "../../components/SiteLayout";
import { formatPrice } from "../../components/ProductCard";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import type { Product, ProductBundle, ProductBundleInput } from "../../lib/types";

type BundleForm = { name: string; description: string; special_price: string; selected: Record<number, number>; is_active: boolean };
const blankForm = (): BundleForm => ({ name: "", description: "", special_price: "", selected: {}, is_active: true });

export function BundleManagement() {
  const { token } = useAuth();
  const [bundles, setBundles] = useState<ProductBundle[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [form, setForm] = useState<BundleForm>(blankForm);
  const [editing, setEditing] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    if (!token) return;
    try {
      const [rows, catalog] = await Promise.all([api.listAdminBundles(token), api.listAdminOfferProducts(token)]);
      setBundles(rows);
      setProducts(catalog.filter((product) => product.is_active));
      setError("");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load bundles."); }
  }
  useEffect(() => { void load(); }, [token]);

  function edit(bundle: ProductBundle) {
    setEditing(bundle.id);
    setForm({ name: bundle.name, description: bundle.description ?? "", special_price: String(bundle.special_price), is_active: bundle.is_active,
      selected: Object.fromEntries(bundle.items.map((item) => [item.product_id, item.quantity])) });
    setSuccess(""); setError("");
  }
  function clear() { setEditing(null); setForm(blankForm()); }
  function changeQuantity(productId: number, checked: boolean, quantity = 1) {
    setForm((current) => {
      const selected = { ...current.selected };
      if (checked) selected[productId] = quantity; else delete selected[productId];
      return { ...current, selected };
    });
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!token) return;
    const items = Object.entries(form.selected).map(([product_id, quantity]) => ({ product_id: Number(product_id), quantity }));
    if (items.length < 2) { setError("Choose at least two products for a bundle."); return; }
    const input: ProductBundleInput = { name: form.name.trim(), description: form.description.trim() || null, special_price: Number(form.special_price), items, is_active: form.is_active };
    setError(""); setSuccess(""); setBusy(true);
    try {
      if (editing === null) await api.createBundle(input, token); else await api.updateBundle(editing, input, token);
      clear(); await load(); setSuccess(editing === null ? "Bundle created." : "Bundle updated.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not save bundle."); }
    finally { setBusy(false); }
  }
  async function disable(bundle: ProductBundle) {
    if (!token || !window.confirm(`Disable “${bundle.name}”?`)) return;
    setError(""); setSuccess("");
    try { await api.disableBundle(bundle.id, token); await load(); setSuccess("Bundle disabled."); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not disable bundle."); }
  }

  return <section className="admin-card bundle-admin">
    <div className="form-card-heading"><span className="card-icon"><Package size={19} /></span><div><h2>Product bundles</h2><p>Combine products and set a special bundle price.</p></div><span className="count-badge">{bundles.length}</span></div>
    {error && <Notice tone="error">{error}</Notice>}{success && <Notice tone="success">{success}</Notice>}
    <form className="bundle-admin-form" onSubmit={(event) => void submit(event)}>
      <label>Bundle name<input required maxLength={150} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
      <label>Special price (₹)<input required type="number" min="0.01" step="0.01" value={form.special_price} onChange={(event) => setForm({ ...form, special_price: event.target.value })} /></label>
      <label className="bundle-description-field">Description<textarea rows={2} maxLength={4000} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
      <fieldset className="bundle-product-picker"><legend>Products (select at least two)</legend>
        {products.map((product) => <label className="bundle-product-option" key={product.id}>
          <input type="checkbox" checked={product.id in form.selected} onChange={(event) => changeQuantity(product.id, event.target.checked)} />
          <span>{product.name}<small>{formatPrice(product.offer_price ?? product.price)}</small></span>
          {product.id in form.selected && <input aria-label={`Quantity of ${product.name}`} type="number" min="1" max="100" value={form.selected[product.id]} onChange={(event) => changeQuantity(product.id, true, Math.max(1, Number(event.target.value)))} />}
        </label>)}
        {!products.length && <p>No active products are available.</p>}
      </fieldset>
      <label className="bundle-active-toggle"><input type="checkbox" checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} /> Available to buyers</label>
      <div className="bundle-admin-actions"><button className="button button-dark" disabled={busy || !products.length}>{editing === null ? <Plus size={16} /> : <Check size={16} />}{busy ? "Saving…" : editing === null ? "Create bundle" : "Save changes"}</button>{editing !== null && <button type="button" className="button button-light" onClick={clear}><X size={16} /> Cancel edit</button>}</div>
    </form>
    <div className="bundle-admin-list">{bundles.map((bundle) => <article key={bundle.id}>
      <div><b>{bundle.name}</b><small>{bundle.items.map((item) => `${item.quantity} × ${item.product_name}`).join(" · ")}</small></div>
      <strong>{formatPrice(bundle.special_price)} <small>{bundle.is_active ? "Active" : "Disabled"}</small></strong>
      <button type="button" aria-label={`Edit ${bundle.name}`} onClick={() => edit(bundle)}><Pencil size={15} /></button>
      {bundle.is_active && <button type="button" aria-label={`Disable ${bundle.name}`} onClick={() => void disable(bundle)}><X size={16} /></button>}
    </article>)}</div>
  </section>;
}
