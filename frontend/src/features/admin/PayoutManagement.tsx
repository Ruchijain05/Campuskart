import { useEffect, useState, type FormEvent } from "react";
import { CircleDollarSign } from "lucide-react";
import { formatPrice } from "../../components/ProductCard";
import { LoadingState, Notice } from "../../components/SiteLayout";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import type { AdminPayoutDashboard, PayoutStatus } from "../../lib/types";

const transitions: Record<PayoutStatus, PayoutStatus[]> = {
  pending: ["processing", "paid", "failed"],
  processing: ["paid", "failed"],
  paid: [],
  failed: [],
};

export function PayoutManagement() {
  const { token } = useAuth();
  const [data, setData] = useState<AdminPayoutDashboard | null>(null);
  const [sellerId, setSellerId] = useState("");
  const [amount, setAmount] = useState("");
  const [reference, setReference] = useState("");
  const [note, setNote] = useState("");
  const [statuses, setStatuses] = useState<Record<number, PayoutStatus>>({});
  const [references, setReferences] = useState<Record<number, string>>({});
  const [notes, setNotes] = useState<Record<number, string>>({});
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    if (!token) return;
    const result = await api.getAdminPayoutDashboard(token);
    setData(result);
    if (!sellerId && result.sellers[0]) setSellerId(String(result.sellers[0].seller_id));
    setStatuses(Object.fromEntries(result.payouts.map((payout) => [payout.id, payout.status])));
    setReferences(Object.fromEntries(result.payouts.map((payout) => [payout.id, payout.reference ?? ""])));
    setNotes(Object.fromEntries(result.payouts.map((payout) => [payout.id, payout.note ?? ""])));
  }

  useEffect(() => { void load().catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Could not load payout data.")); }, [token]);

  async function createPayout(event: FormEvent) {
    event.preventDefault();
    if (!token || !sellerId) return;
    setBusy(true); setError(""); setSuccess("");
    try {
      await api.createAdminPayout({ seller_id: Number(sellerId), amount: Number(amount), reference: reference.trim() || null, note: note.trim() || null }, token);
      setAmount(""); setReference(""); setNote("");
      await load(); setSuccess("Payout record created. Update its status as it is processed.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not create payout."); }
    finally { setBusy(false); }
  }

  async function updatePayout(id: number) {
    if (!token) return;
    const payout = data?.payouts.find((item) => item.id === id);
    if (!payout) return;
    setBusy(true); setError(""); setSuccess("");
    try {
      await api.updateAdminPayout(id, { status: statuses[id] ?? payout.status, reference: references[id]?.trim() || null, note: notes[id]?.trim() || null }, token);
      await load(); setSuccess(`Payout #${id} updated.`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not update payout."); }
    finally { setBusy(false); }
  }

  const selectedSeller = data?.sellers.find((seller) => String(seller.seller_id) === sellerId);
  return <section className="admin-panel payout-management">
    <div className="section-heading"><div><span className="eyebrow">SELLER PAYMENTS</span><h2><CircleDollarSign size={21} /> Seller earnings &amp; payouts</h2><p>Review earnings and record seller payouts. Amounts are limited to paid orders and delivered COD orders.</p></div></div>
    {error && <Notice tone="error">{error}</Notice>}{success && <Notice>{success}</Notice>}
    {data && <>
      <div className="admin-seller-earnings-list">{data.sellers.map((seller) => <article key={seller.seller_id}>
        <div><b>{seller.seller_name}</b><small>{seller.seller_email} · {seller.total_sales} units sold</small></div>
        <span>Gross sales <b>{formatPrice(seller.gross_sales)}</b></span>
        <span>Earnings <b>{formatPrice(seller.earnings)}</b></span>
        <span>Pending <b>{formatPrice(seller.pending_payments)}</b></span>
        <span>Available <b>{formatPrice(seller.available_for_payout)}</b></span>
      </article>)}</div>
      <form className="admin-payout-form" onSubmit={(event) => void createPayout(event)}>
        <h3>Create payout record</h3>
        <label>Seller<select required value={sellerId} onChange={(event) => setSellerId(event.target.value)}><option value="">Select a seller</option>{data.sellers.map((seller) => <option key={seller.seller_id} value={seller.seller_id}>{seller.seller_name} · available {formatPrice(seller.available_for_payout)}</option>)}</select></label>
        <label>Amount (₹)<input type="number" min="0.01" max={selectedSeller?.available_for_payout ?? undefined} step="0.01" required value={amount} onChange={(event) => setAmount(event.target.value)} /></label>
        <label>Transaction reference<input maxLength={120} value={reference} onChange={(event) => setReference(event.target.value)} /></label>
        <label>Admin note<input maxLength={2000} value={note} onChange={(event) => setNote(event.target.value)} /></label>
        <button className="button button-dark" disabled={busy || !sellerId || Number(selectedSeller?.available_for_payout ?? 0) <= 0}>Create payout</button>
      </form>
      <h3>Payout history</h3>
      {data.payouts.length ? <div className="admin-payout-list">{data.payouts.map((payout) => <article key={payout.id}>
        <div className="admin-payout-person"><b>{payout.seller_name}</b><small>{payout.seller_email} · {new Date(payout.created_at).toLocaleString()}</small><strong>{formatPrice(payout.amount)}</strong></div>
        <label>Status<select value={statuses[payout.id] ?? payout.status} disabled={transitions[payout.status].length === 0} onChange={(event) => setStatuses((current) => ({ ...current, [payout.id]: event.target.value as PayoutStatus }))}><option value={payout.status}>{payout.status}</option>{transitions[payout.status].map((status) => <option key={status} value={status}>{status}</option>)}</select></label>
        <label>Reference<input maxLength={120} value={references[payout.id] ?? ""} onChange={(event) => setReferences((current) => ({ ...current, [payout.id]: event.target.value }))} /></label>
        <label>Note<input maxLength={2000} value={notes[payout.id] ?? ""} onChange={(event) => setNotes((current) => ({ ...current, [payout.id]: event.target.value }))} /></label>
        <button className="button button-light" disabled={busy || transitions[payout.status].length === 0} onClick={() => void updatePayout(payout.id)}>Save</button>
      </article>)}</div> : <p>No payouts have been recorded.</p>}
    </>}
    {!data && !error && <LoadingState label="Loading seller payouts..." />}
  </section>;
}
