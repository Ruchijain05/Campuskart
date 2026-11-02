import { useEffect, useState } from "react";
import { Check, RotateCcw, X } from "lucide-react";
import { formatPrice } from "../../components/ProductCard";
import { LoadingState, Notice } from "../../components/SiteLayout";
import { useAuth } from "../../lib/auth";
import { api } from "../../lib/api";
import type { AdminReturnRequest, RefundStatus } from "../../lib/types";

const refundNext: Record<RefundStatus, RefundStatus[]> = {
  pending: ["processing", "refunded", "failed"],
  processing: ["refunded", "failed"],
  failed: ["processing"],
  refunded: [],
  not_applicable: [],
};

export function ReturnsManagement() {
  const { token } = useAuth();
  const [requests, setRequests] = useState<AdminReturnRequest[]>([]);
  const [notes, setNotes] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    let active = true;
    if (!token) return;
    api.listAdminReturns(token)
      .then((rows) => { if (active) setRequests(rows); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Could not load return requests."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token]);

  async function review(id: number, decision: "approved" | "rejected") {
    if (!token) return;
    setBusyId(id); setError(""); setSuccess("");
    try {
      const updated = await api.reviewReturn(id, decision, notes[id] ?? "", token);
      setRequests((current) => current.map((item) => item.id === id ? updated : item));
      setSuccess(`Request #${id} ${decision}. The buyer has been notified.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not review the request.");
    } finally { setBusyId(null); }
  }

  async function updateRefund(request: AdminReturnRequest, nextStatus: RefundStatus) {
    if (!token) return;
    setBusyId(request.id); setError(""); setSuccess("");
    try {
      const updated = await api.updateRefundStatus(request.id, nextStatus, token);
      setRequests((current) => current.map((item) => item.id === request.id ? updated : item));
      setSuccess(`Refund status for order #${request.order_id} updated. The buyer has been notified.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not update refund status.");
    } finally { setBusyId(null); }
  }

  return (
    <section className="admin-card returns-admin-card">
      <div className="form-card-heading"><span className="card-icon"><RotateCcw size={19} /></span><div><h2>Returns &amp; refunds</h2><p>Review delivered order requests and track refund progress.</p></div><span className="count-badge">{requests.filter((item) => item.status === "pending").length} pending</span></div>
      {error && <Notice tone="error">{error}</Notice>}{success && <Notice tone="success">{success}</Notice>}
      {loading ? <LoadingState label="Loading return requests..." /> : requests.length ? <div className="returns-admin-list">
        {requests.map((item) => <article className="returns-admin-item" key={item.id}>
          <div className="returns-admin-heading"><div><b>ORDER #{item.order_id} · {item.request_type}</b><small>{new Date(item.created_at).toLocaleString()}</small></div><span className={`return-status return-status-${item.status}`}>{item.status}</span></div>
          <p className="returns-admin-buyer">{item.buyer_name} · {item.buyer_email} · {formatPrice(item.order_total)} · {item.payment_method.toUpperCase()}</p>
          <p className="returns-admin-reason"><b>Reason:</b> {item.reason}</p>
          {item.status === "pending" ? <>
            <label className="return-note-label">Decision note (optional)<textarea rows={2} maxLength={1000} value={notes[item.id] ?? ""} onChange={(event) => setNotes((current) => ({ ...current, [item.id]: event.target.value }))} /></label>
            <div className="review-actions"><button className="button button-approve" disabled={busyId === item.id} onClick={() => void review(item.id, "approved")}><Check size={15} /> Approve</button><button className="button button-reject" disabled={busyId === item.id} onClick={() => void review(item.id, "rejected")}><X size={15} /> Reject</button></div>
          </> : <>
            {item.review_note && <p className="returns-admin-note"><b>Admin note:</b> {item.review_note}</p>}
            <label className="refund-status-control">Refund status <select value={item.refund_status} disabled={item.status !== "approved" || !refundNext[item.refund_status].length || busyId === item.id} onChange={(event) => void updateRefund(item, event.target.value as RefundStatus)}>
              <option value={item.refund_status}>{item.refund_status.replaceAll("_", " ")}</option>
              {refundNext[item.refund_status].map((refundStatus) => <option value={refundStatus} key={refundStatus}>{refundStatus}</option>)}
            </select></label>
          </>}
        </article>)}
      </div> : <div className="empty-admin"><span>↻</span><p>No return or refund requests yet.</p></div>}
    </section>
  );
}
