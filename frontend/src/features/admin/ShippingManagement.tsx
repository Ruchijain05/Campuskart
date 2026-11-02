import { useEffect, useState, type FormEvent } from "react";
import { Notice } from "../../components/SiteLayout";
import { formatPrice } from "../../components/ProductCard";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import type { Order, OrderShippingInput, ShippingSettings } from "../../lib/types";

function toLocalInput(value: string | null) {
  if (!value) return "";
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

export function ShippingManagement() {
  const { token } = useAuth();
  const [settings, setSettings] = useState<ShippingSettings>({ delivery_charge: 0, estimated_delivery_days: 5, updated_at: null });
  const [orders, setOrders] = useState<Order[]>([]);
  const [dates, setDates] = useState<Record<number, string>>({});
  const [couriers, setCouriers] = useState<Record<number, string>>({});
  const [trackingIds, setTrackingIds] = useState<Record<number, string>>({});
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    if (!token) return;
    const [config, orderList] = await Promise.all([api.getShippingSettings(), api.listAdminOrders(token)]);
    setSettings(config);
    setOrders(orderList);
    setDates(Object.fromEntries(orderList.map((order) => [order.id, toLocalInput(order.estimated_delivery_at)])));
    setCouriers(Object.fromEntries(orderList.map((order) => [order.id, order.courier_name ?? ""])));
    setTrackingIds(Object.fromEntries(orderList.map((order) => [order.id, order.tracking_id ?? ""])));
  }

  useEffect(() => { void load().catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Could not load shipping information.")); }, [token]);

  async function saveSettings(event: FormEvent) {
    event.preventDefault();
    if (!token) return;
    setBusy(true); setError(""); setSuccess("");
    try { setSettings(await api.updateShippingSettings(settings, token)); setSuccess("Delivery charge and estimated delivery window saved."); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not save shipping settings."); }
    finally { setBusy(false); }
  }

  async function saveOrder(orderId: number) {
    if (!token) return;
    setBusy(true); setError(""); setSuccess("");
    try {
      const payload: OrderShippingInput = {
        estimated_delivery_at: dates[orderId] ? new Date(dates[orderId]).toISOString() : null,
        courier_name: couriers[orderId]?.trim() || null,
        tracking_id: trackingIds[orderId]?.trim() || null,
      };
      await api.updateOrderShipping(orderId, payload, token);
      setSuccess(`Delivery details for order #${orderId} saved.`);
      await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not save delivery details."); }
    finally { setBusy(false); }
  }

  return <section className="admin-panel shipping-management">
    <div className="section-heading"><div><span className="eyebrow">FULFILLMENT</span><h2>Shipping &amp; delivery</h2><p>Set the delivery charge and update courier details for each order.</p></div></div>
    {error && <Notice tone="error">{error}</Notice>}{success && <Notice>{success}</Notice>}
    <form className="shipping-settings-form" onSubmit={(event) => void saveSettings(event)}>
      <label>Delivery charge (₹)<input type="number" min="0" step="0.01" required value={settings.delivery_charge} onChange={(event) => setSettings((current) => ({ ...current, delivery_charge: Number(event.target.value) }))} /></label>
      <label>Default delivery estimate (days)<input type="number" min="1" max="90" required value={settings.estimated_delivery_days} onChange={(event) => setSettings((current) => ({ ...current, estimated_delivery_days: Number(event.target.value) }))} /></label>
      <button className="button button-dark" disabled={busy}>Save delivery settings</button>
    </form>
    <h3>Order courier and tracking details</h3>
    {orders.length ? <div className="shipping-order-list">{orders.map((order) => <article key={order.id} className="shipping-order-item">
      <div><b>Order #{order.id}</b><small>{order.delivery_name} · {formatPrice(order.total)} · {order.status}</small></div>
      <label>Estimated delivery<input type="datetime-local" value={dates[order.id] ?? ""} onChange={(event) => setDates((items) => ({ ...items, [order.id]: event.target.value }))} /></label>
      <label>Courier<input maxLength={120} value={couriers[order.id] ?? ""} onChange={(event) => setCouriers((items) => ({ ...items, [order.id]: event.target.value }))} placeholder="Courier name" /></label>
      <label>Tracking ID<input maxLength={120} value={trackingIds[order.id] ?? ""} onChange={(event) => setTrackingIds((items) => ({ ...items, [order.id]: event.target.value }))} placeholder="Tracking number" /></label>
      <button className="button button-light" type="button" disabled={busy} onClick={() => void saveOrder(order.id)}>Save order details</button>
    </article>)}</div> : <p>No orders to update yet.</p>}
  </section>;
}
