import { useState, type FormEvent } from "react";
import { ArrowRight, Minus, Plus, ShoppingCart, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import { Notice, LoadingState, PageTitle } from "../../components/SiteLayout";
import { formatPrice } from "../../components/ProductCard";
import { useCart } from "../../lib/cart";

export function CartPage() {
  const { cart, loading, error: loadError, updateItem, removeItem } = useCart();
  const [quantities, setQuantities] = useState<Record<number, string>>({});
  const [busyProduct, setBusyProduct] = useState<number | null>(null);
  const [error, setError] = useState("");
  async function saveQuantity(event: FormEvent<HTMLFormElement>, productId: number) {
    event.preventDefault();
    const quantity = Number(quantities[productId]);
    if (!Number.isInteger(quantity) || quantity < 1) { setError("Enter a quantity of at least 1."); return; }
    setBusyProduct(productId); setError("");
    try { await updateItem(productId, quantity); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not update this quantity."); }
    finally { setBusyProduct(null); }
  }
  async function deleteItem(productId: number) {
    setBusyProduct(productId); setError("");
    try {
      await removeItem(productId);
      setQuantities((current) => { const next = { ...current }; delete next[productId]; return next; });
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not remove this item."); }
    finally { setBusyProduct(null); }
  }
  return (
    <section className="content-narrow cart-page">
      <PageTitle eyebrow="YOUR CAMPUSKART" title="Your cart" description="Review your finds and adjust quantities." />
      {loadError && <Notice tone="error">{loadError}</Notice>}
      {error && <Notice tone="error">{error}</Notice>}
      {loading ? <LoadingState label="Loading your cart..." /> : cart.items.length ? (
        <div className="cart-layout">
          <div className="cart-items">
            {cart.items.map((item) => (
              <article className="cart-item" key={item.product_id}>
                {item.image_url ? <img className="cart-item-image" src={item.image_url} alt="" /> : <div className="cart-item-image cart-item-placeholder"><ShoppingCart size={24} /></div>}
                <div className="cart-item-main">
                  <h2>{item.product_name}</h2>
                  <p>{formatPrice(item.unit_price)} each · {item.stock} in stock</p>
                  {!item.available && <small className="cart-unavailable">This quantity is no longer available. Update it or remove the item.</small>}
                  <form className="cart-quantity-form" onSubmit={(event) => void saveQuantity(event, item.product_id)}>
                    <label htmlFor={'cart-quantity-' + item.product_id}>Quantity</label>
                    <div className="cart-quantity-control">
                      <button type="button" aria-label={'Decrease ' + item.product_name} disabled={Number(quantities[item.product_id] ?? item.quantity) <= 1} onClick={() => setQuantities((current) => ({ ...current, [item.product_id]: String(Math.max(1, Number(current[item.product_id] ?? item.quantity) - 1)) }))}><Minus size={14} /></button>
                      <input id={'cart-quantity-' + item.product_id} type="number" min="1" max={item.stock || 1} value={quantities[item.product_id] ?? item.quantity} onChange={(event) => setQuantities((current) => ({ ...current, [item.product_id]: event.target.value }))} />
                      <button type="button" aria-label={'Increase ' + item.product_name} disabled={Number(quantities[item.product_id] ?? item.quantity) >= item.stock} onClick={() => setQuantities((current) => ({ ...current, [item.product_id]: String(Number(current[item.product_id] ?? item.quantity) + 1) }))}><Plus size={14} /></button>
                    </div>
                    <button className="button button-outline cart-update-button" disabled={busyProduct === item.product_id}>{busyProduct === item.product_id ? "Saving..." : "Update"}</button>
                  </form>
                </div>
                <div className="cart-item-side">
                  <strong>{item.available ? formatPrice(item.line_total) : "Unavailable"}</strong>
                  <button type="button" className="cart-remove-button" disabled={busyProduct === item.product_id} onClick={() => void deleteItem(item.product_id)}><Trash2 size={15} /> Remove</button>
                </div>
              </article>
            ))}
          </div>
          <aside className="cart-summary">
            <span className="eyebrow">ORDER SUMMARY</span>
            <div><span>Available items</span><b>{cart.items.filter((item) => item.available).reduce((sum, item) => sum + item.quantity, 0)}</b></div>
            <div className="cart-total"><span>Total</span><strong>{formatPrice(cart.total)}</strong></div>
            <small>Prices and stock are checked by CampusKart. Checkout is not available yet.</small>
            <Link className="button button-dark" to="/">Continue browsing <ArrowRight size={16} /></Link>
          </aside>
        </div>
      ) : (
        <div className="cart-empty"><ShoppingCart size={38} /><h2>Your cart is empty</h2><p>Add a campus find and it will appear here.</p><Link className="button button-dark" to="/">Explore products <ArrowRight size={16} /></Link></div>
      )}
    </section>
  );
}