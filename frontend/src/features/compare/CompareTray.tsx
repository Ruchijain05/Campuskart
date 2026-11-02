import { ArrowRight, X } from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "../../lib/auth";
import { useComparison } from "../../lib/comparison";

export function CompareTray() {
  const { user } = useAuth();
  const { productIds, message, clearProducts } = useComparison();
  if (user?.role !== "buyer" || productIds.length === 0) return null;
  const compareUrl = `/compare?products=${productIds.join(",")}`;
  return <aside className="compare-tray" aria-label="Product comparison selection">
    <div className="compare-tray-copy"><b>{productIds.length} of 3 selected</b><span>{message || (productIds.length < 2 ? "Select at least two products to compare." : "Ready to compare side by side.")}</span></div>
    <div className="compare-tray-actions"><button type="button" className="compare-clear" onClick={clearProducts}><X size={14} /> Clear</button><Link className="button button-dark" aria-disabled={productIds.length < 2} onClick={(event) => { if (productIds.length < 2) event.preventDefault(); }} to={compareUrl}>Compare now <ArrowRight size={15} /></Link></div>
  </aside>;
}
