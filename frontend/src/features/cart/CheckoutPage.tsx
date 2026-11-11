import { useEffect, useState, type FormEvent } from "react";
import { ArrowLeft, CheckCircle2, MapPin, ShoppingBag } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { LoadingState, Notice, PageTitle } from "../../components/SiteLayout";
import { formatPrice } from "../../components/ProductCard";
import { useAuth } from "../../lib/auth";
import { useCart } from "../../lib/cart";
import { api } from "../../lib/api";
import type { DeliveryAddress, PickupLocation } from "../../lib/types";
import type { CouponQuote } from "../../lib/types";

interface RazorpayResult {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

interface RazorpayOptions {
  key: string;
  amount: number;
  currency: string;
  name: string;
  description: string;
  order_id: string;
  prefill: { name: string; email?: string; contact: string };
  handler: (result: RazorpayResult) => void;
  modal: { ondismiss: () => void };
}

declare global {
  interface Window {
    Razorpay?: new (options: RazorpayOptions) => {
      open: () => void;
    };
  }
}

function loadRazorpay(): Promise<void> {
  if (window.Razorpay) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>('script[data-razorpay-checkout]');
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("Could not load Razorpay checkout.")), { once: true });
      return;
    }
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    script.dataset.razorpayCheckout = "true";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Could not load Razorpay checkout."));
    document.body.appendChild(script);
  });
}

export function CheckoutPage() {
  const { token, user } = useAuth();
  const { cart, loading, error: cartError, clearAfterOrder } = useCart();
  const navigate = useNavigate();
  const [address, setAddress] = useState<DeliveryAddress>({
    delivery_name: user?.full_name ?? "",
    delivery_phone: user?.phone_number ?? "",
    address_line: "",
    city: "",
    state: "",
    postal_code: "",
  });
  const [error, setError] = useState("");
  const [placing, setPlacing] = useState(false);
  const [verificationResult, setVerificationResult] = useState<RazorpayResult | null>(null);
  const [paymentMethod, setPaymentMethod] = useState<"cod" | "razorpay">("cod");
  const [couponCode, setCouponCode] = useState("");
  const [couponQuote, setCouponQuote] = useState<CouponQuote | null>(null);
  const [couponBusy, setCouponBusy] = useState(false);
  const [couponError, setCouponError] = useState("");
  const [pickupLocations, setPickupLocations] = useState<PickupLocation[]>([]);
  const [pickupLocationId, setPickupLocationId] = useState("");
  const unavailable = cart.items.some((item) => !item.available);
  const selectedPickupLocation = pickupLocations.find((location) => String(location.id) === pickupLocationId);
  const totalDue = Number(couponQuote?.total ?? cart.total);

  useEffect(() => {
    api.listPickupLocations().then(setPickupLocations).catch(() => setPickupLocations([]));
  }, []);

  async function verifyCapturedPayment(result: RazorpayResult) {
    if (!token) return;
    setPlacing(true);
    setError("");
    try {
      const order = await api.verifyRazorpayPayment(result, token);
      setVerificationResult(null);
      clearAfterOrder();
      navigate(`/orders/${order.id}`, { replace: true, state: { justPlaced: true } });
    } catch (reason) {
      setVerificationResult(result);
      setError(reason instanceof Error ? reason.message : "Payment verification failed. Retry verification or contact support.");
    } finally {
      setPlacing(false);
    }
  }

  function change(field: keyof DeliveryAddress, value: string) {
    setAddress((current) => ({ ...current, [field]: value }));
  }

  async function applyCoupon() {
    if (!token || !couponCode.trim()) return;
    setCouponBusy(true);
    setCouponError("");
    try {
      const quote = await api.validateCoupon(couponCode, token);
      setCouponQuote(quote);
      setCouponCode(quote.code);
    } catch (reason) {
      setCouponQuote(null);
      setCouponError(reason instanceof Error ? reason.message : "Could not apply this coupon.");
    } finally {
      setCouponBusy(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !cart.items.length || unavailable || !selectedPickupLocation) return;
    setError(""); setPlacing(true);
    let paymentWindowOpened = false;
    try {
      const orderAddress: DeliveryAddress = {
        ...address,
        address_line: selectedPickupLocation.address_line,
        city: selectedPickupLocation.city,
        state: selectedPickupLocation.state,
        postal_code: selectedPickupLocation.postal_code,
      };
      if (paymentMethod === "cod" || totalDue === 0) {
        const order = await api.placeOrder(orderAddress, token, couponQuote?.code, "campus_pickup", selectedPickupLocation.id);
        clearAfterOrder();
        navigate(`/orders/${order.id}`, { replace: true, state: { justPlaced: true } });
        return;
      }

      const payment = await api.startRazorpayPayment(orderAddress, token, couponQuote?.code, "campus_pickup", selectedPickupLocation.id);
      try {
        await loadRazorpay();
      } catch (reason) {
        await api.cancelRazorpayPayment(payment.order.id, token);
        throw reason;
      }
      if (!window.Razorpay) throw new Error("Razorpay checkout could not start. Please try again.");
      let completed = false;
      let closing = false;
      const cancelPayment = async () => {
        if (closing || completed) return;
        closing = true;
        try {
          await api.cancelRazorpayPayment(payment.order.id, token);
          setError("Payment was cancelled. Your items are still in your cart.");
        } catch (reason) {
          setError(reason instanceof Error ? reason.message : "Could not update the payment status.");
        } finally {
          setPlacing(false);
        }
      };
      const checkout = new window.Razorpay({
        key: payment.key_id,
        amount: payment.amount,
        currency: payment.currency,
        name: "CampusKart",
        description: `Order #${payment.order.id}`,
        order_id: payment.razorpay_order_id,
        prefill: { name: address.delivery_name, email: user?.email, contact: address.delivery_phone },
        handler: (result) => {
          completed = true;
          setVerificationResult(result);
          void verifyCapturedPayment(result);
        },
        modal: { ondismiss: () => { void cancelPayment(); } },
      });
      checkout.open();
      paymentWindowOpened = true;
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not place your order.");
    } finally { if (!paymentWindowOpened) setPlacing(false); }
  }
  return (
    <section className="content-narrow checkout-page">
      <PageTitle eyebrow="ALMOST YOURS" title="Checkout" description="Choose a campus pickup point and review your order." />
      {cartError && <Notice tone="error">{cartError}</Notice>}
      {error && <Notice tone="error">{error}</Notice>}
      {loading ? <LoadingState label="Loading your cart..." /> : !cart.items.length ? (
        <div className="cart-empty"><ShoppingBag size={38} /><h2>Your cart is empty</h2><p>Add a campus find before checking out.</p><Link className="button button-dark" to="/">Explore products</Link></div>
      ) : (
        <form className="checkout-layout" onSubmit={(event) => void submit(event)}>
          <div className="checkout-main">
            <section className="checkout-card">
              <h2><MapPin size={18} /> Fulfillment</h2>
              <p>CampusKart orders are collected from the seller by CampusKart staff and brought to your selected campus pickup point.</p>
              <label className="saved-address-selector">Pickup location<select required value={pickupLocationId} onChange={(event) => setPickupLocationId(event.target.value)}><option value="">Choose a campus location</option>{pickupLocations.map((location) => <option key={location.id} value={location.id}>{location.name} · {location.city}</option>)}</select></label>
              {selectedPickupLocation && <div className="pickup-location-summary"><b>{selectedPickupLocation.name}</b><span>{selectedPickupLocation.address_line}, {selectedPickupLocation.city}, {selectedPickupLocation.state} {selectedPickupLocation.postal_code}</span>{selectedPickupLocation.instructions && <small>{selectedPickupLocation.instructions}</small>}</div>}
              {!pickupLocations.length && <Notice tone="error">Campus pickup locations are not available right now.</Notice>}
              <div className="checkout-fields">
                <label>Recipient name<input required maxLength={120} autoComplete="name" value={address.delivery_name} onChange={(event) => change("delivery_name", event.target.value)} /></label>
                <label>Phone number<input required type="tel" autoComplete="tel" minLength={10} maxLength={16} value={address.delivery_phone} onChange={(event) => change("delivery_phone", event.target.value)} /></label>
              </div>
            </section>
            <section className="checkout-card checkout-payment">
              <h2><CheckCircle2 size={18} /> Payment method</h2>
              <label><input type="radio" name="payment_method" value="cod" checked={paymentMethod === "cod"} onChange={() => setPaymentMethod("cod")} /> Pay at pickup <small>Pay when you collect your order.</small></label>
              <label><input type="radio" name="payment_method" value="razorpay" checked={paymentMethod === "razorpay"} onChange={() => setPaymentMethod("razorpay")} /> Pay online <small>Secure test-mode checkout with Razorpay.</small></label>
            </section>
          </div>
          <aside className="checkout-summary">
            <span className="eyebrow">ORDER SUMMARY</span>
            {cart.items.map((item) => <div className="checkout-summary-line" key={item.product_id}><span>{item.product_name} × {item.quantity}</span><b>{formatPrice(item.line_total)}</b></div>)}
            <div className="checkout-coupon-form">
              <label htmlFor="checkout-coupon">Coupon code</label>
              <div><input id="checkout-coupon" value={couponCode} maxLength={32} disabled={Boolean(couponQuote) || couponBusy || placing} onChange={(event) => setCouponCode(event.target.value.toUpperCase())} placeholder="Enter coupon code" />
                {couponQuote ? <button type="button" className="button button-light" disabled={placing} onClick={() => { setCouponQuote(null); setCouponCode(""); setCouponError(""); }}>Remove</button> : <button type="button" className="button button-light" disabled={couponBusy || placing || !couponCode.trim()} onClick={() => void applyCoupon()}>{couponBusy ? "Checking..." : "Apply"}</button>}
              </div>
              {couponError && <small className="coupon-error">{couponError}</small>}
              {couponQuote && <small className="coupon-success">{couponQuote.code} applied successfully.</small>}
            </div>
            <div className="checkout-summary-line"><span>Subtotal</span><b>{formatPrice(couponQuote?.subtotal ?? cart.total)}</b></div>
            {couponQuote && <div className="checkout-summary-line checkout-discount-line"><span>Discount ({couponQuote.code})</span><b>−{formatPrice(couponQuote.discount_amount)}</b></div>}
            <div className="checkout-summary-line"><span>Campus pickup</span><b>Free</b></div>
            <small className="delivery-estimate">CampusKart staff will collect packed items from the seller and bring them to your pickup point. We will notify you when they are ready.</small>
            <div className="checkout-summary-total"><span>{totalDue === 0 ? "Total due" : paymentMethod === "cod" ? "Total due at pickup" : "Total to pay online"}</span><strong>{formatPrice(totalDue)}</strong></div>
            {unavailable && <Notice tone="error">Some cart items are unavailable. Return to the cart and update or remove them.</Notice>}
            {verificationResult && <button type="button" className="button button-dark" disabled={placing} onClick={() => void verifyCapturedPayment(verificationResult)}>{placing ? "Verifying payment..." : "Retry payment verification"}</button>}
            <button className="button button-dark" disabled={placing || unavailable || !selectedPickupLocation}>{placing ? "Processing..." : totalDue === 0 ? "Place order · No payment due" : paymentMethod === "cod" ? "Place order · Pay at pickup" : "Pay securely with Razorpay"}</button>
            <Link className="checkout-back" to="/cart"><ArrowLeft size={14} /> Back to cart</Link>
          </aside>
        </form>
      )}
    </section>
  );
}
