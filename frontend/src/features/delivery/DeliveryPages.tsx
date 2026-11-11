import { useCallback, useEffect, useState } from "react";
import { MapPin, PackageCheck, Phone, Truck } from "lucide-react";
import { LoadingState, Notice, PageTitle } from "../../components/SiteLayout";
import { useAuth } from "../../lib/auth";
import { api } from "../../lib/api";
import type { DeliveryJob } from "../../lib/types";

const steps: { status: DeliveryJob["status"]; label: string }[] = [
  { status: "collected_from_seller", label: "Collected packed order from seller" },
  { status: "ready_at_pickup", label: "Arrived at pickup point; notify buyer" },
  { status: "collected_by_buyer", label: "Buyer collected order" },
];

export function DeliveryJobsPage() {
  const { token } = useAuth();
  const [jobs, setJobs] = useState<DeliveryJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<number | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try { setJobs(await api.listMyDeliveryJobs(token)); setError(""); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load assigned jobs."); }
    finally { setLoading(false); }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  async function advance(job: DeliveryJob, status: DeliveryJob["status"]) {
    if (!token) return;
    let failure_note: string | null = null;
    if (status === "delivery_issue") {
      failure_note = window.prompt("Describe the issue so CampusKart can arrange a follow-up.")?.trim() ?? "";
      if (!failure_note) return;
    }
    setBusy(job.id); setError("");
    try { await api.updateDeliveryJob(job.id, status, failure_note, token); await load(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not update this job."); }
    finally { setBusy(null); }
  }

  return <section className="content-narrow delivery-jobs-page">
    <PageTitle eyebrow="CAMPUSKART STAFF" title="My delivery jobs" description="Collect packed items directly from each seller, then bring the order to the selected campus pickup point." />
    {error && <Notice tone="error">{error}</Notice>}
    {loading ? <LoadingState label="Loading your assigned jobs..." /> : jobs.length ? <div className="delivery-job-list">{jobs.map((job) => {
      const next = steps.find((step) => step.status === "collected_from_seller" ? job.status === "assigned" : step.status === "ready_at_pickup" ? job.status === "collected_from_seller" : job.status === "ready_at_pickup");
      return <article className="delivery-job-card" key={job.id}>
        <header><div><span className="eyebrow">JOB #{job.id}</span><h2>Order #{job.order_id}</h2></div><b className={`delivery-job-status status-${job.status}`}>{job.status.replaceAll("_", " ")}</b></header>
        <section><h3><PackageCheck size={16} /> Items to collect</h3><ul>{job.products.map((product, index) => <li key={`${product}-${index}`}>{product}</li>)}</ul></section>
        <section><h3><Truck size={16} /> Collect directly from seller</h3>{job.sellers.map((seller) => <div className="delivery-contact" key={seller.full_name}><b>{seller.full_name}</b><a href={`tel:${seller.phone_number}`}><Phone size={14} />{seller.phone_number}</a><small>{seller.products.join(" · ")}</small></div>)}</section>
        <section><h3><MapPin size={16} /> Drop at pickup point</h3><b>{job.pickup_location_name}</b><p>{job.pickup_address}</p><small>Buyer: {job.buyer_name} · <a href={`tel:${job.buyer_phone}`}>{job.buyer_phone}</a></small></section>
        {job.failure_note && <Notice tone="error">Issue reported: {job.failure_note}. Contact an admin for reassignment.</Notice>}
        {next && <button className="button button-dark" disabled={busy === job.id} onClick={() => void advance(job, next.status)}>{busy === job.id ? "Updating..." : next.label}</button>}
        {job.status === "collected_from_seller" && <button className="button button-outline" disabled={busy === job.id} onClick={() => void advance(job, "delivery_issue")}>Report a delivery issue</button>}
        {job.status === "ready_at_pickup" && <button className="button button-outline" disabled={busy === job.id} onClick={() => void advance(job, "delivery_issue")}>Report a handoff issue</button>}
      </article>;
    })}</div> : <div className="empty-state"><span className="empty-emoji"><Truck size={24} /></span><h3>No jobs assigned</h3><p>New jobs assigned by an admin will appear here.</p></div>}
  </section>;
}
