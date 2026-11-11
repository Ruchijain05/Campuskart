import { useEffect, useState, type FormEvent } from "react";
import { ArrowRight, PackageCheck, RotateCcw } from "lucide-react";
import { Link, useLocation, useParams } from "react-router-dom";
import { LoadingState, Notice, PageTitle } from "../../components/SiteLayout";
import { formatPrice } from "../../components/ProductCard";
import { useAuth } from "../../lib/auth";
import { api } from "../../lib/api";
import type { Order, OrderStatus, ReturnRequest, ReturnType } from "../../lib/types";
import { InvoiceDownloadButton } from "../../components/InvoiceDownloadButton";

const statusLabels: Record<OrderStatus, string> = {
  placed: "Placed",
  confirmed: "Confirmed",
  shipped: "Shipped",
  delivered: "Delivered",
  cancelled: "Cancelled",
};

const progressStatuses: OrderStatus[] = ["placed", "confirmed", "shipped", "delivered"];

function OrderProgress({ status }: { status: OrderStatus }) {
  if (status === "cancelled") return <div className="order-cancelled-state"><span className="order-status">Cancelled</span><p>This order was cancelled.</p></div>;
  const current = progressStatuses.indexOf(status);
  return <ol className="order-progress">{progressStatuses.map((step, index) => <li key={step} className={index < current ? "is-complete" : index === current ? "is-current" : ""}><span>{index + 1}</span><b>{statusLabels[step]}</b></li>)}</ol>;
}

function paymentLabel(method: string) {
  if (method === "razorpay") return "Razorpay";
  if (method === "coupon") return "No payment due";
  return "Cash on Delivery";
}

function pickupProgressMessage(status: Order["delivery_job_status"]): string {
  switch (status) {
    case "assigned": return "CampusKart staff are assigned and will collect your packed order from the seller.";
    case "collected_from_seller": return "CampusKart staff collected your order and are taking it to the pickup point.";
    case "ready_at_pickup": return "Your order is ready at the selected campus pickup point.";
    case "collected_by_buyer": return "Your order has been collected.";
    case "delivery_issue": return "Pickup is delayed. CampusKart staff will follow up.";
    default: return "We will notify you when your order is ready.";
  }
}

function OrderCard({ order }: { order: Order }) {
  return (
    <article className="order-card">
      <div className="order-card-heading"><div><span className="eyebrow">ORDER #{order.id}</span><h2>{new Date(order.created_at).toLocaleString()}</h2></div><span className="order-status">{statusLabels[order.status]}</span></div>
      <div className="order-card-items">{order.items.map((item) => <div key={item.id}><span>{item.product_name} × {item.quantity}</span><b>{formatPrice(item.line_total)}</b></div>)}</div>
      <div className="order-card-footer"><span>{order.delivery_method === "campus_pickup" ? `Campus pickup · ${order.pickup_status.replaceAll("_", " ")}${order.delivery_job_status ? ` · ${order.delivery_job_status.replaceAll("_", " ")}` : ""}` : "Home delivery"} · {paymentLabel(order.payment_method)} · Payment {order.payment_status}</span><strong>{formatPrice(order.total)}</strong><Link className="text-link" to={`/orders/${order.id}`}>View order <ArrowRight size={14} /></Link><InvoiceDownloadButton orderId={order.id} /></div>
    </article>
  );
}

export function MyOrdersPage() {
  const { token } = useAuth();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    if (!token) return;
    api.listOrders(token).then((result) => { if (active) setOrders(result); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Could not load your orders."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token]);
  return <section className="content-narrow orders-page"><PageTitle eyebrow="YOUR CAMPUSKART" title="My orders" description="Your past orders and delivery details." />{error && <Notice tone="error">{error}</Notice>}{loading ? <LoadingState label="Loading your orders..." /> : orders.length ? <div className="orders-list">{orders.map((order) => <OrderCard key={order.id} order={order} />)}</div> : <div className="cart-empty"><PackageCheck size={38} /><h2>No orders yet</h2><p>Your placed orders will show up here.</p><Link className="button button-dark" to="/">Explore products</Link></div>}</section>;
}

export function OrderDetailPage() {
  const { token, user } = useAuth();
  const { orderId } = useParams();
  const location = useLocation();
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [returnRequest, setReturnRequest] = useState<ReturnRequest | null>(null);
  const [returnType, setReturnType] = useState<ReturnType>("return");
  const [returnReason, setReturnReason] = useState("");
  const [returnBusy, setReturnBusy] = useState(false);
  const [returnError, setReturnError] = useState("");
  useEffect(() => {
    let active = true;
    const id = Number(orderId);
    if (!token || !Number.isInteger(id) || id < 1) { setError("That order link is not valid."); setLoading(false); return; }
    Promise.all([
      api.getOrder(id, token),
      user?.role === "buyer" ? api.listMyReturns(token) : Promise.resolve([]),
    ]).then(([result, requests]) => {
      if (!active) return;
      setOrder(result);
      setReturnRequest(requests.find((item) => item.order_id === result.id) ?? null);
    })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Could not load this order."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [orderId, token, user?.role]);

  async function submitReturnRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || user?.role !== "buyer" || !order) return;
    setReturnBusy(true); setReturnError("");
    try {
      setReturnRequest(await api.requestReturn(order.id, returnType, returnReason, token));
      setReturnReason("");
    } catch (reason) {
      setReturnError(reason instanceof Error ? reason.message : "Could not submit your request.");
    } finally { setReturnBusy(false); }
  }
  if (loading) return <section className="content-narrow"><LoadingState label="Loading your order..." /></section>;
  if (error || !order) return <section className="content-narrow orders-page"><Notice tone="error">{error || "Order not found."}</Notice><Link className="text-link" to="/orders">Back to my orders</Link></section>;
  return (
    <section className="content-narrow orders-page">
      {location.state?.justPlaced && <Notice tone="success">Order placed successfully. {order.payment_method === "razorpay" ? "Your Razorpay payment was verified." : "Your items have been reserved and payment is due on delivery."}</Notice>}
      <PageTitle eyebrow={`ORDER #${order.id}`} title="Order details" description={`Placed ${new Date(order.created_at).toLocaleString()}`} />
      <div className="order-detail-layout"><div className="checkout-card"><h2>Items</h2>{order.items.map((item) => <div className="checkout-summary-line" key={item.id}><span>{item.product_name} × {item.quantity}<small>{formatPrice(item.unit_price)} each</small></span><b>{formatPrice(item.line_total)}</b></div>)}<div className="checkout-summary-line"><span>Subtotal</span><b>{formatPrice(order.subtotal)}</b></div>{Number(order.discount_amount) > 0 && <div className="checkout-summary-line checkout-discount-line"><span>{order.discount_description ?? `Coupon discount${order.coupon_code ? ` (${order.coupon_code})` : ""}`}</span><b>−{formatPrice(order.discount_amount)}</b></div>}<div className="checkout-summary-line"><span>{order.delivery_method === "campus_pickup" ? "Pickup charge" : "Delivery charge"}</span><b>{Number(order.shipping_fee) ? formatPrice(order.shipping_fee) : "Free"}</b></div><div className="checkout-summary-total"><span>Total paid / due</span><strong>{formatPrice(order.total)}</strong></div></div>
        <aside className="checkout-card"><h2>{order.delivery_method === "campus_pickup" ? "Campus pickup" : "Delivery"}</h2><p><b>{order.delivery_name}</b><br />{order.delivery_phone}<br />{order.address_line}<br />{order.city}, {order.state} {order.postal_code}</p>{order.delivery_method === "campus_pickup" && <div className={`pickup-status-panel pickup-status-${order.pickup_status}`}><b>{order.pickup_status === "ready" ? "Ready for collection" : order.pickup_status === "collected" ? "Collected" : "Preparing your pickup"}</b><small>{pickupProgressMessage(order.delivery_job_status)}</small></div>}<h2>Payment</h2><p>{paymentLabel(order.payment_method)} · Status: {order.payment_status}</p>{order.payment_method === "razorpay" && <p className="payment-reference">{order.razorpay_payment_id ? <>Payment ID: <code>{order.razorpay_payment_id}</code></> : <>Payment order: <code>{order.razorpay_order_id}</code></>}</p>}<h2>Order tracking</h2><OrderProgress status={order.status} />{order.estimated_delivery_at && <p><b>Estimated delivery:</b><br />{new Date(order.estimated_delivery_at).toLocaleString()}</p>}{order.courier_name && <p><b>Courier:</b> {order.courier_name}</p>}{order.tracking_id && <p><b>Tracking ID:</b> <code>{order.tracking_id}</code></p>}</aside></div>
      {user?.role === "buyer" && order.status === "delivered" && <section className="return-request-panel">
        <h2><RotateCcw size={18} /> Returns &amp; refunds</h2>
        {returnError && <Notice tone="error">{returnError}</Notice>}
        {returnRequest ? <div className="return-request-summary">
          <div className="return-request-summary-heading"><span className={`return-status return-status-${returnRequest.status}`}>{returnRequest.status}</span><span>Refund: <b className={`refund-status refund-status-${returnRequest.refund_status}`}>{returnRequest.refund_status.replaceAll("_", " ")}</b></span></div>
          <p><b>{returnRequest.request_type === "return" ? "Return" : "Refund"} request:</b> {returnRequest.reason}</p>
          {returnRequest.review_note && <p><b>Admin note:</b> {returnRequest.review_note}</p>}
        </div> : <form className="return-request-form" onSubmit={(event) => void submitReturnRequest(event)}>
          <p>This order was delivered. Choose what you need and tell us why.</p>
          <label>Request type<select value={returnType} onChange={(event) => setReturnType(event.target.value as ReturnType)}><option value="return">Return items</option><option value="refund">Refund</option></select></label>
          <label>Reason<textarea required minLength={1} maxLength={3000} rows={4} value={returnReason} onChange={(event) => setReturnReason(event.target.value)} placeholder="Describe the issue with your order..." /></label>
          <button className="button button-dark" disabled={returnBusy}>{returnBusy ? "Submitting..." : "Submit request"}</button>
          <small>Only one return or refund request can be made for an order.</small>
        </form>}
      </section>}
      <Link className="text-link orders-back-link" to="/orders">Back to all orders <ArrowRight size={14} /></Link>
    </section>
  );
}
