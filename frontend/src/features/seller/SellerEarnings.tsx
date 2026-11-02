import { useEffect, useState } from "react";
import { IndianRupee, Wallet } from "lucide-react";
import { formatPrice } from "../../components/ProductCard";
import { LoadingState, Notice } from "../../components/SiteLayout";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import type { SellerPayoutHistory } from "../../lib/types";

export function SellerEarnings() {
  const { token } = useAuth();
  const [history, setHistory] = useState<SellerPayoutHistory | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    if (!token) return;
    api.getSellerPayoutHistory(token)
      .then((result) => { if (active) setHistory(result); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Could not load seller earnings."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token]);

  return <section className="seller-earnings-panel">
    <div className="seller-recent-heading"><h3><Wallet size={17} /> Earnings &amp; payouts</h3><span>Total earnings reflect sales; payout availability uses paid orders and delivered COD.</span></div>
    {error && <Notice tone="error">{error}</Notice>}
    {loading ? <LoadingState label="Loading your earnings..." /> : history && <>
      <div className="seller-earnings-grid">
        <article><small>Units sold</small><strong>{history.earnings.total_sales}</strong></article>
        <article><small>Gross sales</small><strong><IndianRupee size={15} />{formatPrice(history.earnings.gross_sales)}</strong></article>
        <article><small>Total earnings</small><strong><IndianRupee size={15} />{formatPrice(history.earnings.earnings)}</strong></article>
        <article><small>Pending payments</small><strong><IndianRupee size={15} />{formatPrice(history.earnings.pending_payments)}</strong></article>
        <article><small>Available for payout</small><strong><IndianRupee size={15} />{formatPrice(history.earnings.available_for_payout)}</strong></article>
      </div>
      <div className="seller-payout-history"><h4>Payout history</h4>{history.payouts.length ? <div className="seller-payout-list">{history.payouts.map((payout) => <article key={payout.id}>
        <div><b>{formatPrice(payout.amount)}</b><small>{new Date(payout.created_at).toLocaleString()}{payout.reference ? ` · ${payout.reference}` : ""}</small>{payout.note && <small>{payout.note}</small>}</div>
        <span className={`payout-status payout-${payout.status}`}>{payout.status}</span>
      </article>)}</div> : <p>No payout records yet. Admin payout updates will appear here.</p>}</div>
    </>}
  </section>;
}
