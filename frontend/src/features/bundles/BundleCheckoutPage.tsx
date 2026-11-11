import { useEffect, useState, type FormEvent } from "react";
import { ArrowLeft, MapPin, PackageOpen } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { LoadingState, Notice, PageTitle } from "../../components/SiteLayout";
import { formatPrice } from "../../components/ProductCard";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import type { DeliveryAddress, PickupLocation, ProductBundle, SavedAddress, ShippingSettings } from "../../lib/types";

export function BundleCheckoutPage() {
  const { token, user } = useAuth();
  const { bundleId } = useParams();
  const navigate = useNavigate();
  const [bundle, setBundle] = useState<ProductBundle | null>(null);
  const [shipping] = useState<ShippingSettings>({ delivery_charge: 0, estimated_delivery_days: 0, updated_at: null });
  const [addresses] = useState<SavedAddress[]>([]);
  const [pickupLocations, setPickupLocations] = useState<PickupLocation[]>([]);
  const [deliveryMethod, setDeliveryMethod] = useState<"home_delivery" | "campus_pickup">("campus_pickup");
  const [pickupLocationId, setPickupLocationId] = useState("");
  const [selectedAddress, setSelectedAddress] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [address, setAddress] = useState<DeliveryAddress>({ delivery_name: user?.full_name ?? "", delivery_phone: user?.phone_number ?? "", address_line: "", city: "", state: "", postal_code: "" });
  const [loading, setLoading] = useState(true);
  const [placing, setPlacing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    if (!bundleId || !token) return;
    Promise.all([api.getBundle(Number(bundleId)), api.listPickupLocations()])
      .then(([item, pickups]) => {
        if (!active) return;
        setBundle(item); setPickupLocations(pickups);
      })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Could not load bundle checkout."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [bundleId, token]);

  function selectSaved(id: string) {
    setSelectedAddress(id);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const selectedPickup = pickupLocations.find((location) => String(location.id) === pickupLocationId);
    if (!bundle || !token || !bundle.available || !selectedPickup) return;
    setPlacing(true); setError("");
    try {
      const orderAddress = selectedPickup ? { ...address, address_line: selectedPickup.address_line, city: selectedPickup.city, state: selectedPickup.state, postal_code: selectedPickup.postal_code } : address;
      const order = await api.placeBundleOrder(bundle.id, quantity, orderAddress, token, "campus_pickup", selectedPickup.id);
      navigate(`/orders/${order.id}`, { replace: true, state: { justPlaced: true } });
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not place this bundle order."); }
    finally { setPlacing(false); }
  }

  if (loading) return <LoadingState label="Loading bundle checkout..." />;
  if (!bundle) return <section className="content-narrow"><Notice tone="error">{error || "Bundle not found."}</Notice><Link to="/bundles" className="text-link">Back to bundles</Link></section>;
  const subtotal = Number(bundle.original_price) * quantity;
  const discount = Number(bundle.discount_amount) * quantity;
  const payable = Number(bundle.payable_price) * quantity;
  const selectedPickup = pickupLocations.find((location) => String(location.id) === pickupLocationId);
  const deliveryCharge = 0;
  const total = payable;
  return <section className="content-narrow checkout-page bundle-checkout-page"><PageTitle eyebrow="BUNDLE CHECKOUT" title="Checkout" description={`Buying ${bundle.name}. Bundle orders are paid by Cash on Delivery.`} />{error && <Notice tone="error">{error}</Notice>}
    <form className="checkout-layout" onSubmit={(event) => void submit(event)}><div className="checkout-main"><section className="checkout-card"><h2><MapPin size={18} /> Fulfillment</h2><div className="checkout-fulfillment-options"><label><input type="radio" name="bundle_delivery_method" checked={deliveryMethod === "home_delivery"} onChange={() => setDeliveryMethod("home_delivery")} /> Home delivery</label><label><input type="radio" name="bundle_delivery_method" checked={deliveryMethod === "campus_pickup"} onChange={() => setDeliveryMethod("campus_pickup")} /> Campus pickup</label></div>
      {deliveryMethod === "campus_pickup" ? <><label className="saved-address-selector">Pickup location<select required value={pickupLocationId} onChange={(event) => setPickupLocationId(event.target.value)}><option value="">Choose a campus location</option>{pickupLocations.map((location) => <option key={location.id} value={location.id}>{location.name} · {location.city}</option>)}</select></label>{selectedPickup && <div className="pickup-location-summary"><b>{selectedPickup.name}</b><span>{selectedPickup.address_line}, {selectedPickup.city}, {selectedPickup.state} {selectedPickup.postal_code}</span>{selectedPickup.instructions && <small>{selectedPickup.instructions}</small>}</div>}{!pickupLocations.length && <Notice tone="error">Campus pickup locations are not available right now.</Notice>}</> : addresses.length > 0 && <label className="saved-address-selector">Choose saved address<select value={selectedAddress} onChange={(event) => selectSaved(event.target.value)}><option value="">Enter a different address</option>{addresses.map((item) => <option key={item.id} value={item.id}>{item.full_name} · {item.city}{item.is_default ? " (Default)" : ""}</option>)}</select></label>}
      <div className="checkout-fields"><label>Recipient name<input required maxLength={120} value={address.delivery_name} onChange={(event) => { setSelectedAddress(""); setAddress((value) => ({ ...value, delivery_name: event.target.value })); }} /></label><label>Phone number<input required type="tel" minLength={10} maxLength={16} value={address.delivery_phone} onChange={(event) => { setSelectedAddress(""); setAddress((value) => ({ ...value, delivery_phone: event.target.value })); }} /></label>{deliveryMethod === "home_delivery" && <><label className="checkout-field-full">Address<input required minLength={5} maxLength={1000} value={address.address_line} onChange={(event) => { setSelectedAddress(""); setAddress((value) => ({ ...value, address_line: event.target.value })); }} /></label><label>City<input required maxLength={100} value={address.city} onChange={(event) => { setSelectedAddress(""); setAddress((value) => ({ ...value, city: event.target.value })); }} /></label><label>State<input required maxLength={100} value={address.state} onChange={(event) => { setSelectedAddress(""); setAddress((value) => ({ ...value, state: event.target.value })); }} /></label><label>PIN code<input required minLength={4} maxLength={20} value={address.postal_code} onChange={(event) => { setSelectedAddress(""); setAddress((value) => ({ ...value, postal_code: event.target.value })); }} /></label></>}</div>
      <p className="bundle-payment-note">Payment method: Cash on Delivery</p><Link className="checkout-address-link" to="/addresses">Manage saved addresses</Link></section></div>
      <aside className="checkout-summary"><span className="eyebrow">ORDER SUMMARY</span><h3><PackageOpen size={16} /> {bundle.name}</h3><label className="bundle-quantity">Bundles<select value={quantity} onChange={(event) => setQuantity(Number(event.target.value))}>{Array.from({ length: Math.max(1, Math.min(bundle.max_bundles, 20)) }, (_, index) => <option key={index + 1} value={index + 1}>{index + 1}</option>)}</select></label>{bundle.items.map((item) => <div className="checkout-summary-line" key={item.product_id}><span>{item.product_name} × {item.quantity * quantity}</span><b>{formatPrice(Number(item.unit_price) * item.quantity * quantity)}</b></div>)}<div className="checkout-summary-line"><span>Subtotal</span><b>{formatPrice(subtotal)}</b></div><div className="checkout-summary-line checkout-discount-line"><span>Bundle discount</span><b>−{formatPrice(discount)}</b></div><div className="checkout-summary-line"><span>{deliveryMethod === "campus_pickup" ? "Campus pickup" : "Delivery charge"}</span><b>{deliveryCharge ? formatPrice(deliveryCharge) : "Free"}</b></div><small className="delivery-estimate">{deliveryMethod === "campus_pickup" ? "We will notify you when your order is ready for collection." : `Estimated delivery in ${shipping.estimated_delivery_days} days.`}</small><div className="checkout-summary-total"><span>Total due on delivery</span><strong>{formatPrice(total)}</strong></div><button className="button button-dark" disabled={placing || !bundle.available || (deliveryMethod === "campus_pickup" && !selectedPickup)}>{placing ? "Placing order..." : "Place bundle order · COD"}</button><Link className="checkout-back" to={`/bundles/${bundle.id}`}><ArrowLeft size={14} /> Back to bundle</Link></aside>
    </form>
  </section>;
}
