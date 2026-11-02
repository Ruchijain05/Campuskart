import { useEffect, useState } from "react";
import { ArrowRight, PackageOpen, ShoppingCart } from "lucide-react";
import { Link } from "react-router-dom";
import { LoadingState, Notice, PageTitle } from "../../components/SiteLayout";
import { formatPrice } from "../../components/ProductCard";
import { useAuth } from "../../lib/auth";
import { useCart } from "../../lib/cart";
import { api } from "../../lib/api";
import type { BuyAgainProduct } from "../../lib/types";

export function BuyAgainPage() {
  const { token } = useAuth();
  const { addItem } = useCart();
  const [products, setProducts] = useState<BuyAgainProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [quantityByProduct, setQuantityByProduct] = useState<Record<number, number>>({});
  const [addingProduct, setAddingProduct] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<Record<number, { tone: "success" | "error"; text: string }>>({});

  useEffect(() => {
    let active = true;
    if (!token) return;
    api.listBuyAgainProducts(token)
      .then((items) => { if (active) { setProducts(items); setError(""); } })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Could not load your previous purchases."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token]);

  async function addProduct(item: BuyAgainProduct) {
    if (item.product_id === null || !item.available || !token) return;
    const productId = item.product_id;
    const quantity = Math.min(quantityByProduct[productId] ?? Math.min(item.last_quantity, item.stock), item.stock);
    setAddingProduct(productId);
    try {
      await addItem(productId, Math.max(1, quantity));
      setFeedback((current) => ({ ...current, [productId]: { tone: "success", text: "Added to your cart." } }));
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "Could not add this product to your cart.";
      setFeedback((current) => ({ ...current, [productId]: { tone: "error", text: message } }));
      try {
        const freshItems = await api.listBuyAgainProducts(token);
        setProducts(freshItems);
      } catch {
        // Keep the cart error visible if refreshing current availability also fails.
      }
    } finally {
      setAddingProduct(null);
    }
  }

  return <section className="content-narrow buy-again-page">
    <PageTitle eyebrow="YOUR CAMPUSKART" title="Buy again" description="Find products from your earlier orders and add them to your cart again." />
    {error && <Notice tone="error">{error}</Notice>}
    {loading ? <LoadingState label="Finding products from your orders..." /> : products.length ? <div className="buy-again-list">
      {products.map((item, index) => {
        const productId = item.product_id;
        const quantity = productId === null ? 1 : Math.min(quantityByProduct[productId] ?? Math.min(item.last_quantity, item.stock || 1), item.stock || 1);
        const itemFeedback = productId === null ? undefined : feedback[productId];
        return <article className={`buy-again-card${item.available ? "" : " is-unavailable"}`} key={productId ?? `unavailable-${item.product_name}-${index}`}>
          {item.image_url ? <img className="buy-again-image" src={item.image_url} alt="" /> : <div className="buy-again-image buy-again-placeholder"><PackageOpen size={25} /></div>}
          <div className="buy-again-details">
            {productId !== null && item.available ? <Link to={`/products/${productId}`} className="buy-again-name">{item.product_name}</Link> : <h2 className="buy-again-name">{item.product_name}</h2>}
            <p>{item.available ? "Current price" : "Last paid"} {formatPrice(item.price)} · previously bought {item.last_quantity}</p>
            <small>Last ordered {new Date(item.last_ordered_at).toLocaleDateString()}</small>
            {itemFeedback && <span className={`buy-again-feedback ${itemFeedback.tone}`}>{itemFeedback.text}</span>}
          </div>
          <div className="buy-again-actions">
            {item.available && productId !== null ? <>
              <label>Qty <input aria-label={`Quantity for ${item.product_name}`} type="number" min="1" max={item.stock} value={quantity} onChange={(event) => setQuantityByProduct((current) => ({ ...current, [productId]: Math.max(1, Number(event.target.value) || 1) }))} /></label>
              <button className="button button-dark" disabled={addingProduct === productId} onClick={() => void addProduct(item)}><ShoppingCart size={15} />{addingProduct === productId ? "Adding..." : "Add to cart"}</button>
            </> : <span className="buy-again-unavailable">{item.unavailable_reason || "Unavailable"}</span>}
          </div>
        </article>;
      })}
    </div> : <div className="buy-again-empty"><PackageOpen size={38} /><h2>No past products yet</h2><p>Products from your orders will show here when they can be bought again.</p><Link className="button button-dark" to="/orders">View my orders <ArrowRight size={15} /></Link></div>}
  </section>;
}
