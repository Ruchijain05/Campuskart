import { useEffect, useState } from "react";
import { RotateCcw } from "lucide-react";
import { Link } from "react-router-dom";
import { formatPrice } from "../../components/ProductCard";
import { LoadingState, Notice, PageTitle } from "../../components/SiteLayout";
import { useAuth } from "../../lib/auth";
import { api } from "../../lib/api";
import type { ReturnRequest } from "../../lib/types";

export function MyReturnsPage() {
  const { token } = useAuth();
  const [requests, setRequests] = useState<ReturnRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    if (!token) return;
    api.listMyReturns(token)
      .then((rows) => { if (active) setRequests(rows); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Could not load your return requests."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token]);

  return (
    <section className="content-narrow my-returns-page">
      <PageTitle eyebrow="YOUR ACCOUNT" title="Returns &amp; refunds" description="Review your requests and see admin decisions and refund progress." />
      {error && <Notice tone="error">{error}</Notice>}
      {loading ? <LoadingState label="Loading return requests..." /> : requests.length ? <div className="my-return-list">
        {requests.map((item) => <article className="my-return-card" key={item.id}>
          <header><div><span className="eyebrow">ORDER #{item.order_id}</span><h2>{item.request_type === "return" ? "Return request" : "Refund request"}</h2></div><span className={`return-status return-status-${item.status}`}>{item.status}</span></header>
          <p>{item.reason}</p>
          <div className="my-return-meta"><span>Order total <b>{formatPrice(item.order_total)}</b></span><span>Refund <b className={`refund-status refund-status-${item.refund_status}`}>{item.refund_status.replaceAll("_", " ")}</b></span><span>Requested {new Date(item.created_at).toLocaleDateString()}</span></div>
          {item.review_note && <div className="my-return-note"><b>Admin note</b><p>{item.review_note}</p></div>}
          <Link className="text-link" to={`/orders/${item.order_id}`}><RotateCcw size={14} /> View order</Link>
        </article>)}
      </div> : <div className="empty-state"><span className="empty-emoji"><RotateCcw size={24} /></span><h3>No return requests</h3><p>For a delivered order, open its details to request a return or refund.</p><Link className="button button-dark" to="/orders">View my orders</Link></div>}
    </section>
  );
}
