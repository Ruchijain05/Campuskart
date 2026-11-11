import { useEffect, useState, type FormEvent } from "react";
import { Check, MapPin, Plus, X } from "lucide-react";
import { Notice } from "../../components/SiteLayout";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import type { Order, PickupLocation, PickupLocationInput } from "../../lib/types";

const emptyForm = (): PickupLocationInput => ({ name: "", address_line: "", city: "", state: "", postal_code: "", instructions: null, is_active: true });

export function CampusPickupManagement() {
  const { token } = useAuth();
  const [locations, setLocations] = useState<PickupLocation[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [form, setForm] = useState<PickupLocationInput>(emptyForm());
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    if (!token) return;
    const [places, allOrders, jobs] = await Promise.all([api.listAdminPickupLocations(token), api.listAdminOrders(token), api.listAdminDeliveryJobs(token)]);
    const assignedOrderIds = new Set(jobs.map((job) => job.order_id));
    setLocations(places); setOrders(allOrders.filter((order) => order.delivery_method === "campus_pickup" && !assignedOrderIds.has(order.id)));
  }
  useEffect(() => { void load().catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Could not load pickup data.")); }, [token]);

  async function submit(event: FormEvent) {
    event.preventDefault(); if (!token) return;
    setBusy(true); setError(""); setSuccess("");
    try {
      const payload = { ...form, instructions: form.instructions?.trim() || null };
      if (editingId === null) await api.createPickupLocation(payload, token); else await api.updatePickupLocation(editingId, payload, token);
      setForm(emptyForm()); setEditingId(null); await load(); setSuccess(editingId === null ? "Pickup location added." : "Pickup location updated.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not save the pickup location."); }
    finally { setBusy(false); }
  }

  async function disable(location: PickupLocation) {
    if (!token || !window.confirm(`Deactivate ${location.name}? Existing orders will keep their saved location details.`)) return;
    setError(""); setSuccess("");
    try { await api.disablePickupLocation(location.id, token); await load(); setSuccess("Pickup location deactivated."); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not deactivate location."); }
  }

  async function markReady(order: Order) {
    if (!token) return;
    setError(""); setSuccess("");
    try {
      await api.markPickupReady(order.id, token); await load();
      setSuccess(`Buyer notified that order #${order.id} is ready for collection.`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not update pickup status."); }
  }

  return <section className="admin-panel pickup-management">
    <div className="section-heading"><div><span className="eyebrow">FULFILLMENT</span><h2>Campus pickup</h2><p>Manage collection points and notify buyers when orders are ready.</p></div></div>
    {error && <Notice tone="error">{error}</Notice>}{success && <Notice tone="success">{success}</Notice>}
    <form className="pickup-location-form" onSubmit={(event) => void submit(event)}>
      <label>Location name<input required minLength={2} maxLength={120} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="e.g. Main campus desk" /></label>
      <label>Address<input required minLength={5} maxLength={500} value={form.address_line} onChange={(event) => setForm({ ...form, address_line: event.target.value })} /></label>
      <label>City<input required value={form.city} onChange={(event) => setForm({ ...form, city: event.target.value })} /></label>
      <label>State<input required value={form.state} onChange={(event) => setForm({ ...form, state: event.target.value })} /></label>
      <label>PIN code<input required minLength={4} maxLength={20} value={form.postal_code} onChange={(event) => setForm({ ...form, postal_code: event.target.value })} /></label>
      <label>Pickup instructions<textarea rows={2} maxLength={2000} value={form.instructions ?? ""} onChange={(event) => setForm({ ...form, instructions: event.target.value || null })} /></label>
      <label className="pickup-active"><input type="checkbox" checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} /> Available at checkout</label>
      <div className="pickup-form-actions"><button className="button button-dark" disabled={busy}>{editingId === null ? <Plus size={16} /> : <Check size={16} />}{editingId === null ? "Add pickup location" : "Save location"}</button>{editingId !== null && <button className="button button-light" type="button" onClick={() => { setEditingId(null); setForm(emptyForm()); }}>Cancel</button>}</div>
    </form>
    <div className="pickup-admin-list">{locations.map((location) => <article key={location.id}><div><b><MapPin size={14} /> {location.name}</b><small>{location.address_line}, {location.city}, {location.state} {location.postal_code}{location.is_active ? " · Active" : " · Inactive"}</small>{location.instructions && <small>{location.instructions}</small>}</div><button className="button button-light" type="button" onClick={() => { setEditingId(location.id); setForm({ name: location.name, address_line: location.address_line, city: location.city, state: location.state, postal_code: location.postal_code, instructions: location.instructions, is_active: location.is_active }); }}>Edit</button>{location.is_active && <button className="icon-button" type="button" aria-label={`Deactivate ${location.name}`} onClick={() => void disable(location)}><X size={16} /></button>}</article>)}</div>
    <h3>Pickup orders</h3>
    <div className="pickup-admin-list">{orders.map((order) => <article key={order.id}><div><b>Order #{order.id} · {order.pickup_location_name}</b><small>{order.delivery_name} · {order.pickup_status.replaceAll("_", " ")} · {order.status}</small><small>{order.items.map((item) => `${item.product_name} × ${item.quantity}`).join(" · ")}</small></div>{order.pickup_status === "awaiting_pickup" && order.status !== "cancelled" && <button className="button button-dark" type="button" disabled={busy} onClick={() => void markReady(order)}>Mark ready &amp; notify</button>}{order.pickup_status === "ready" && <span className="pickup-ready-badge">Ready for pickup</span>}</article>)}{!orders.length && <p>No campus pickup orders yet.</p>}</div>
  </section>;
}
