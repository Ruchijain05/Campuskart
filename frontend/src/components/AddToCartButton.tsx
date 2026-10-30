import { useState } from "react";
import { ArrowRight, ShoppingCart } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { useCart } from "../lib/cart";

export function AddToCartButton({ productId, disabled = false, compact = false }: { productId: number; disabled?: boolean; compact?: boolean }) {
  const { user } = useAuth();
  const { addItem } = useCart();
  const navigate = useNavigate();
  const location = useLocation();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function add() {
    setMessage("");
    if (!user) {
      navigate("/login", { state: { from: location.pathname } });
      return;
    }
    setBusy(true);
    try {
      await addItem(productId);
      setMessage("Added to cart");
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Could not add this product.");
    } finally {
      setBusy(false);
    }
  }
  return <div className={compact ? "add-cart-wrap add-cart-compact" : "add-cart-wrap"}>
    <button type="button" className="button button-dark add-cart-button" onClick={() => void add()} disabled={disabled || busy}>
      <ShoppingCart size={16} />{busy ? "Adding..." : "Add to Cart"}{compact && !busy ? <ArrowRight size={14} /> : null}
    </button>
    {message && <small className="add-cart-message" role="status">{message}</small>}
  </div>;
}