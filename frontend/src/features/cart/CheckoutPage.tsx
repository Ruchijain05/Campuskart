import { useEffect, useState, type FormEvent } from "react";
import { ArrowLeft, CheckCircle2, MapPin, ShoppingBag } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { LoadingState, Notice, PageTitle } from "../../components/SiteLayout";
import { formatPrice } from "../../components/ProductCard";
import { useAuth } from "../../lib/auth";
import { useCart } from "../../lib/cart";
import { api } from "../../lib/api";
import type { DeliveryAddress, PickupLocation, SavedAddress, SavedAddressInput } from "../../lib/types";
import type { CouponQuote } from "../../lib/types";
import type { ShippingSettings } from "../../lib/types";

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
  const [savedAddresses, setSavedAddresses] = useState<SavedAddress[]>([]);
  const [selectedAddressId, setSelectedAddressId] = useState("");
  const [saveAddress, setSaveAddress] = useState(false);
  const [addressLoadError, setAddressLoadError] = useState("");
  const [shipping, setShipping] = useState<ShippingSettings>({ delivery_charge: 0, estimated_delivery_days: 5, updated_at: null });
  const [deliveryMethod, setDeliveryMethod] = useState<"home_delivery" | "campus_pickup">("home_delivery");
  const [pickupLocations, setPickupLocations] = useState<PickupLocation[]>([]);
  const [pickupLocationId, setPickupLocationId] = useState("");
  const unavailable = cart.items.some((item) => !item.available);
  const selectedPickupLocation = pickupLocations.find((location) => String(location.id) === pickupLocationId);
  const deliveryCharge = deliveryMethod === "campus_pickup" ? 0 : Number(shipping.delivery_charge);
  const totalDue = Number(couponQuote?.total ?? cart.total) + deliveryCharge;

  useEffect(() => {
    api.getShippingSettings().then(setShipping).catch(() => setShipping({ delivery_charge: 0, estimated_delivery_days: 5, updated_at: null }));
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

  useEffect(() => {
    let active = true;
    if (!token || user?.role !== "buyer") return;
    api.listAddresses(token).then((items) => {
      if (!active) return;
      setSavedAddresses(items);
      const preferred = items.find((item) => item.is_default) ?? items[0];
      if (preferred) {
        setSelectedAddressId(String(preferred.id));
        setAddress({
          delivery_name: preferred.full_name,
          delivery_phone: preferred.phone_number,
          address_line: preferred.address_line,
          city: preferred.city,
          state: preferred.state,
          postal_code: preferred.pin_code,
        });
      }
    }).catch((reason: unknown) => {
      if (active) setAddressLoadError(reason instanceof Error ? reason.message : "Could not load saved addresses.");
    });
    return () => { active = false; };
  }, [token, user?.role]);

  function change(field: keyof DeliveryAddress, value: string) {
    setSelectedAddressId("");
    setAddress((current) => ({ ...current, [field]: value }));
  }

  function selectAddress(id: string) {
    setSelectedAddressId(id);
    setSaveAddress(false);
    if (!id) return;
    const selected = savedAddresses.find((item) => String(item.id) === id);
    if (!selected) return;
    setAddress({
      delivery_name: selected.full_name,
      delivery_phone: selected.phone_number,
      address_line: selected.address_line,
      city: selected.city,
      state: selected.state,
      postal_code: selected.pin_code,
    });
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
    if (!token || !cart.items.length || unavailable || (deliveryMethod === "campus_pickup" && !selectedPickupLocation)) return;
    setError(""); setPlacing(true);
    let paymentWindowOpened = false;
    try {
      if (saveAddress && deliveryMethod === "home_delivery") {
        const savedInput: SavedAddressInput = {
          full_name: address.delivery_name,
          phone_number: address.delivery_phone,
          address_line: address.address_line,
          city: address.city,
          state: address.state,
          pin_code: address.postal_code,
          is_default: savedAddresses.length === 0,
        };
        await api.createAddress(savedInput, token);
      }
      const orderAddress: DeliveryAddress = selectedPickupLocation ? {
        ...address,
        address_line: selectedPickupLocation.address_line,
        city: selectedPickupLocation.city,
        state: selectedPickupLocation.state,
        postal_code: selectedPickupLocation.postal_code,
      } : address;
      if (paymentMethod === "cod" || totalDue === 0) {
        const order = await api.placeOrder(orderAddress, token, couponQuote?.code, deliveryMethod, selectedPickupLocation?.id);
        clearAfterOrder();
        navigate(`/orders/${order.id}`, { replace: true, state: { justPlaced: true } });
        return;
      }

      const payment = await api.startRazorpayPayment(orderAddress, token, couponQuote?.code, deliveryMethod, selectedPickupLocation?.id);
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
      <PageTitle eyebrow="ALMOST YOURS" title="Checkout" description="Add a delivery address and review your order." />
      {cartError && <Notice tone="error">{cartError}</Notice>}
      {error && <Notice tone="error">{error}</Notice>}
      {loading ? <LoadingState label="Loading your cart..." /> : !cart.items.length ? (
        <div className="cart-empty"><ShoppingBag size={38} /><h2>Your cart is empty</h2><p>Add a campus find before checking out.</p><Link className="button button-dark" to="/">Explore products</Link></div>
      ) : (
        <form className="checkout-layout" onSubmit={(event) => void submit(event)}>
          <div className="checkout-main">
            <section className="checkout-card">
              <h2><MapPin size={18} /> Fulfillment</h2>
              <div className="checkout-fulfillment-options"><label><input type="radio" name="delivery_method" checked={deliveryMethod === "home_delivery"} onChange={() => setDeliveryMethod("home_delivery")} /> Home delivery</label><label><input type="radio" name="delivery_method" checked={deliveryMethod === "campus_pickup"} onChange={() => setDeliveryMethod("campus_pickup")} /> Campus pickup</label></div>
              {deliveryMethod === "campus_pickup" ? <>
                <label className="saved-address-selector">Pickup location<select required value={pickupLocationId} onChange={(event) => setPickupLocationId(event.target.value)}><option value="">Choose a campus location</option>{pickupLocations.map((location) => <option key={location.id} value={location.id}>{location.name} · {location.city}</option>)}</select></label>
                {selectedPickupLocation && <div className="pickup-location-summary"><b>{selectedPickupLocation.name}</b><span>{selectedPickupLocation.address_line}, {selectedPickupLocation.city}, {selectedPickupLocation.state} {selectedPickupLocation.postal_code}</span>{selectedPickupLocation.instructions && <small>{selectedPickupLocation.instructions}</small>}</div>}
                {!pickupLocations.length && <Notice tone="error">Campus pickup locations are not available right now.</Notice>}
              </> : <>
              {addressLoadError && <Notice tone="error">{addressLoadError}</Notice>}
              {savedAddresses.length > 0 && <label className="saved-address-selector">Choose a saved address<select value={selectedAddressId} onChange={(event) => selectAddress(event.target.value)}><option value="">Enter a different address</option>{savedAddresses.map((saved) => <option key={saved.id} value={saved.id}>{saved.full_name} · {saved.city}{saved.is_default ? " (Default)" : ""}</option>)}</select></label>}
              </>}
              <div className="checkout-fields">
                <label>Recipient name<input required maxLength={120} autoComplete="name" value={address.delivery_name} onChange={(event) => change("delivery_name", event.target.value)} /></label>
                <label>Phone number<input required type="tel" autoComplete="tel" minLength={10} maxLength={16} value={address.delivery_phone} onChange={(event) => change("delivery_phone", event.target.value)} /></label>
                {deliveryMethod === "home_delivery" && <>
                <label className="checkout-field-full">Address<input required minLength={5} maxLength={1000} autoComplete="street-address" value={address.address_line} onChange={(event) => change("address_line", event.target.value)} placeholder="Building, street, hostel, room" /></label>
                <label>City<input required maxLength={100} autoComplete="address-level2" value={address.city} onChange={(event) => change("city", event.target.value)} /></label>
                <label>State<input required maxLength={100} autoComplete="address-level1" value={address.state} onChange={(event) => change("state", event.target.value)} /></label>
                <label>PIN code<input required minLength={4} maxLength={20} autoComplete="postal-code" value={address.postal_code} onChange={(event) => change("postal_code", event.target.value)} /></label>
                </>}
              </div>
              {deliveryMethod === "home_delivery" && user?.role === "buyer" && !selectedAddressId && <label className="default-address-option"><input type="checkbox" checked={saveAddress} onChange={(event) => setSaveAddress(event.target.checked)} /> Save this address to my account</label>}
              {deliveryMethod === "home_delivery" && user?.role === "buyer" && <Link className="checkout-address-link" to="/addresses">Manage saved addresses</Link>}
            </section>
            <section className="checkout-card checkout-payment">
              <h2><CheckCircle2 size={18} /> Payment method</h2>
              <label><input type="radio" name="payment_method" value="cod" checked={paymentMethod === "cod"} onChange={() => setPaymentMethod("cod")} /> Cash on Delivery <small>Pay when your order arrives.</small></label>
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
            <div className="checkout-summary-line"><span>{deliveryMethod === "campus_pickup" ? "Campus pickup" : "Delivery charge"}</span><b>{deliveryMethod === "campus_pickup" || !Number(shipping.delivery_charge) ? "Free" : formatPrice(shipping.delivery_charge)}</b></div>
            <small className="delivery-estimate">{deliveryMethod === "campus_pickup" ? "We will notify you when your order is ready for collection." : `Estimated delivery in ${shipping.estimated_delivery_days} days after order placement.`}</small>
            <div className="checkout-summary-total"><span>{totalDue === 0 ? "Total due" : paymentMethod === "cod" ? "Total due on delivery" : "Total to pay online"}</span><strong>{formatPrice(totalDue)}</strong></div>
            {unavailable && <Notice tone="error">Some cart items are unavailable. Return to the cart and update or remove them.</Notice>}
            {verificationResult && <button type="button" className="button button-dark" disabled={placing} onClick={() => void verifyCapturedPayment(verificationResult)}>{placing ? "Verifying payment..." : "Retry payment verification"}</button>}
            <button className="button button-dark" disabled={placing || unavailable || (deliveryMethod === "campus_pickup" && !selectedPickupLocation)}>{placing ? "Processing..." : totalDue === 0 ? "Place order · No payment due" : paymentMethod === "cod" ? "Place order · Cash on Delivery" : "Pay securely with Razorpay"}</button>
            <Link className="checkout-back" to="/cart"><ArrowLeft size={14} /> Back to cart</Link>
          </aside>
        </form>
      )}
    </section>
  );
}
