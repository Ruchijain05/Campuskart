import { useState } from "react";
import { Heart } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { useWishlist } from "../lib/wishlist";

export function WishlistButton({ productId, compact = false }: { productId: number; compact?: boolean }) {
  const { user } = useAuth();
  const { contains, add, remove } = useWishlist();
  const navigate = useNavigate();
  const location = useLocation();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  if (user && user.role !== "buyer") return null;
  const saved = contains(productId);
  async function toggle() {
    setMessage("");
    if (!user) {
      navigate("/login", { state: { from: location.pathname } });
      return;
    }
    setBusy(true);
    try {
      if (saved) { await remove(productId); setMessage("Removed from wishlist"); }
      else { await add(productId); setMessage("Saved to wishlist"); }
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Could not update your wishlist.");
    } finally { setBusy(false); }
  }
  return <div className={compact ? "wishlist-control wishlist-control-compact" : "wishlist-control"}>
    <button type="button" className={saved ? "button button-outline wishlist-button is-saved" : "button button-outline wishlist-button"} onClick={() => void toggle()} disabled={busy} aria-pressed={saved} aria-label={saved ? "Remove from wishlist" : "Add to wishlist"}>
      <Heart size={16} fill={saved ? "currentColor" : "none"} />{busy ? "Saving..." : saved ? "Saved" : "Save to wishlist"}
    </button>
    {message && <small className="wishlist-message" role="status">{message}</small>}
  </div>;
}
