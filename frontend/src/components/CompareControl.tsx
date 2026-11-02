import { ArrowLeftRight } from "lucide-react";
import { useAuth } from "../lib/auth";
import { useComparison } from "../lib/comparison";

export function CompareControl({ productId, compact = false }: { productId: number; compact?: boolean }) {
  const { user } = useAuth();
  const { productIds, toggleProduct } = useComparison();
  if (user?.role !== "buyer") return null;
  const selected = productIds.includes(productId);
  return <button
    type="button"
    className={`compare-control${selected ? " is-selected" : ""}${compact ? " compare-control-compact" : ""}`}
    aria-pressed={selected}
    onClick={() => toggleProduct(productId)}
  ><ArrowLeftRight size={14} />{selected ? "Selected to compare" : "Compare"}</button>;
}
