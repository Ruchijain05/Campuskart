import { useCallback, useEffect, useState } from "react";
import { MapPin, Package, Phone, Truck } from "lucide-react";
import { formatPrice } from "../../components/ProductCard";
import { LoadingState, Notice, PageTitle } from "../../components/SiteLayout";
import { useAuth } from "../../lib/auth";
import { api } from "../../lib/api";
import type { FulfillmentStatus, SellerOrder } from "../../lib/types";

const fulfillmentSteps: FulfillmentStatus[] = ["processing", "packed", "shipped", "delivered"];

export function SellerOrdersPage() {
  const { token } = useAuth();
  const [orders, setOrders] = useState<SellerOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyItem, setBusyItem] = useState<number | null>(null);
  const [error, setError] = useState("");

  const loadOrders = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      setOrders(await api.listSellerOrders(token));
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load your orders.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void loadOrders(); }, [loadOrders]);

  async function updateFulfillment(orderId: number, itemId: number, status: FulfillmentStatus) {
    if (!token) return;
    setBusyItem(itemId);
    setError("");
    try {
      const updated = await api.updateSellerItemFulfillment(itemId, status, token);
      setOrders((current) => current.map((order) => order.id !== orderId ? order : {
        ...order,
        items: order.items.map((item) => item.id === itemId ? updated : item),
      }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not update fulfillment status.");
    } finally {
      setBusyItem(null);
    }
  }

  return (
    <section className="content-narrow seller-orders-page">
      <PageTitle eyebrow="SELLER STUDIO" title="Orders to fulfill" description="View orders that include your products and update each item as it moves through fulfillment." />
      {error && <Notice tone="error">{error}</Notice>}
      {loading ? <LoadingState label="Loading your orders..." /> : orders.length ? (
        <div className="seller-fulfillment-list">
          {orders.map((order) => (
            <article className="seller-fulfillment-order" key={order.id}>
              <header className="seller-fulfillment-heading">
                <div><span className="eyebrow">ORDER #{order.id}</span><h2>{new Date(order.created_at).toLocaleString()}</h2></div>
                <span className={`order-status seller-order-${order.status}`}>{order.status}</span>
              </header>
              <div className="seller-fulfillment-body">
                <section className="seller-fulfillment-items" aria-label={`Your items in order ${order.id}`}>
                  <h3><Package size={16} /> Your products in this order</h3>
                  {order.items.map((item) => {
                    const availableSteps = order.delivery_method === "campus_pickup" ? fulfillmentSteps.slice(0, 2) : fulfillmentSteps;
                    const stepIndex = availableSteps.indexOf(item.fulfillment_status);
                    const nextStep = stepIndex >= 0 ? availableSteps[stepIndex + 1] : undefined;
                    return (
                      <div className="seller-fulfillment-item" key={item.id}>
                        <div className="seller-fulfillment-product"><b>{item.product_name}</b><span>{item.quantity} × {formatPrice(item.unit_price)} · {formatPrice(item.line_total)}</span></div>
                        <label>Fulfillment status
                          <select
                            value={item.fulfillment_status}
                            disabled={!nextStep || order.status === "cancelled" || busyItem === item.id}
                            onChange={(event) => void updateFulfillment(order.id, item.id, event.target.value as FulfillmentStatus)}
                          >
                            {fulfillmentSteps.map((step) => <option key={step} value={step} disabled={fulfillmentSteps.indexOf(step) < stepIndex || fulfillmentSteps.indexOf(step) > stepIndex + 1}>{step}</option>)}
                          </select>
                        </label>
                      </div>
                    );
                  })}
                  <div className="seller-fulfillment-subtotal"><span>Your items subtotal</span><strong>{formatPrice(order.seller_subtotal)}</strong></div>
                </section>
                <aside className="seller-delivery-details">
                  <h3><Truck size={16} /> {order.delivery_method === "campus_pickup" ? "Campus pickup handoff" : "Delivery details"}</h3>
                  <b>{order.delivery_name}</b>
                  <p><Phone size={13} /> {order.delivery_phone}</p>
                  <p><MapPin size={13} /> {order.address_line}, {order.city}, {order.state} {order.postal_code}</p>
                  {order.delivery_method === "campus_pickup" && <small>Pack your items for CampusKart staff. {order.pickup_location_name ? `Pickup point: ${order.pickup_location_name}.` : "Staff will collect the packed order."}</small>}
                  <small>Payment: {order.payment_method.toUpperCase()} · {order.payment_status}</small>
                </aside>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="empty-state seller-orders-empty"><span className="empty-emoji"><Package size={24} /></span><h3>No orders yet</h3><p>Orders containing your products will appear here.</p></div>
      )}
    </section>
  );
}
