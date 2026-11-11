import { useEffect, useState, type FormEvent } from "react";
import { MapPin, Package, Truck } from "lucide-react";
import { LoadingState, Notice } from "../../components/SiteLayout";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import type { DeliveryJob, DeliveryPersonSummary, Order } from "../../lib/types";

export function DeliveryManagement() {
  const { token } = useAuth();
  const [people, setPeople] = useState<DeliveryPersonSummary[]>([]);
  const [eligible, setEligible] = useState<Order[]>([]);
  const [jobs, setJobs] = useState<DeliveryJob[]>([]);
  const [selected, setSelected] = useState<Record<number, string>>({});
  const [staffForm, setStaffForm] = useState({ email: "" });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function load() {
    if (!token) return;
    setLoading(true);
    try {
      const [staff, orders, assigned] = await Promise.all([
        api.listDeliveryPeople(token),
        api.listEligibleDeliveryOrders(token), api.listAdminDeliveryJobs(token),
      ]);
      setPeople(staff); setEligible(orders); setJobs(assigned); setError("");
      setSelected((current) => {
        const next = { ...current };
        for (const order of orders) if (!next[order.id] && staff[0]) next[order.id] = String(staff[0].id);
        for (const job of assigned) if (!next[job.order_id]) next[job.order_id] = String(job.delivery_person_id);
        return next;
      });
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load delivery management."); }
    finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, [token]);

  async function createStaff(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setBusy(-1); setError(""); setSuccess("");
    try {
      const created = await api.createDeliveryPerson(staffForm, token);
      setSuccess(`Delivery access assigned to ${created.full_name}. They can use their existing account to switch roles.`);
      setStaffForm({ email: "" });
      await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not create the staff account."); }
    finally { setBusy(null); }
  }

  async function assign(orderId: number) {
    if (!token || !selected[orderId]) return;
    setBusy(orderId); setError(""); setSuccess("");
    try {
      await api.assignDeliveryJob(orderId, Number(selected[orderId]), token);
      setSuccess(`Delivery job for order #${orderId} assigned.`);
      await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not assign this order."); }
    finally { setBusy(null); }
  }

  const existingOrderIds = new Set(jobs.map((job) => job.order_id));
  return <section className="delivery-admin-management">
    <div className="section-heading"><div><span className="eyebrow">CAMPUS OPERATIONS</span><h2>Delivery staff and pickup jobs</h2><p>Assign delivery access to an existing CampusKart account, then assign packed orders for campus pickup.</p></div></div>
    {error && <Notice tone="error">{error}</Notice>}{success && <Notice tone="success">{success}</Notice>}
    {loading ? <LoadingState label="Loading delivery operations..." /> : <>
      <div className="delivery-admin-grid">
        <section className="admin-card"><div className="form-card-heading"><span className="card-icon"><Truck size={18} /></span><div><h2>Assign delivery access</h2><p>Enter the email address on the person’s existing CampusKart account.</p></div></div>
          <form className="form-stack" onSubmit={(event) => void createStaff(event)}>
            <label>Email<input required type="email" value={staffForm.email} onChange={(event) => setStaffForm({ ...staffForm, email: event.target.value })} /></label>
            <button className="button button-dark" disabled={busy === -1}>{busy === -1 ? "Assigning..." : "Assign delivery role"}</button>
          </form>
          <div className="form-card-heading"><div><h2>Active delivery staff</h2><p>Only accounts assigned the delivery role can receive jobs.</p></div><span className="count-badge">{people.length}</span></div>
          {people.length ? <ul>{people.map((person) => <li key={person.id}>{person.full_name} · {person.email} · {person.phone_number}</li>)}</ul> : <p>No delivery staff accounts yet.</p>}
        </section>
        <section className="admin-card"><div className="form-card-heading"><span className="card-icon"><Package size={18} /></span><div><h2>Ready to assign</h2><p>Orders appear here after every seller packs their items.</p></div><span className="count-badge">{eligible.length}</span></div>
          {eligible.length ? <div className="delivery-admin-orders">{eligible.map((order) => <article key={order.id}>
            <div><b>Order #{order.id} · {order.pickup_location_name}</b><small>{order.items.map((item) => `${item.product_name} × ${item.quantity}`).join(" · ")}</small><small><MapPin size={13} /> {order.address_line}, {order.city}</small></div>
            <select aria-label={`Assign order ${order.id}`} value={selected[order.id] ?? ""} onChange={(event) => setSelected((current) => ({ ...current, [order.id]: event.target.value }))} disabled={!people.length}><option value="">Select staff</option>{people.map((person) => <option key={person.id} value={person.id}>{person.full_name}</option>)}</select>
            <button className="button button-dark" disabled={busy === order.id || !people.length || !selected[order.id]} onClick={() => void assign(order.id)}>{busy === order.id ? "Assigning..." : "Assign job"}</button>
          </article>)}</div> : <p>No packed campus pickup orders are waiting for assignment.</p>}
        </section>
      </div>
      <section className="admin-card delivery-admin-current"><div className="form-card-heading"><span className="card-icon"><Truck size={18} /></span><div><h2>Assigned delivery jobs</h2><p>Reassign jobs that have not started or were reported with an issue.</p></div><span className="count-badge">{jobs.length}</span></div>
        {jobs.length ? <div className="delivery-admin-orders">{jobs.map((job) => <article key={job.id}>
          <div><b>Order #{job.order_id} · {job.pickup_location_name}</b><small>{job.buyer_name} · {job.status.replaceAll("_", " ")}</small>{job.failure_note && <small>Issue: {job.failure_note}</small>}</div>
          {(job.status === "assigned" || job.status === "delivery_issue") && <><select aria-label={`Reassign order ${job.order_id}`} value={selected[job.order_id] ?? String(job.delivery_person_id)} onChange={(event) => setSelected((current) => ({ ...current, [job.order_id]: event.target.value }))}>{people.map((person) => <option key={person.id} value={person.id}>{person.full_name}</option>)}</select><button className="button button-outline" disabled={busy === job.order_id || !selected[job.order_id]} onClick={() => void assign(job.order_id)}>{busy === job.order_id ? "Saving..." : existingOrderIds.has(job.order_id) ? "Save assignment" : "Assign"}</button></>}
        </article>)}</div> : <p>No delivery jobs assigned yet.</p>}
      </section>
    </>}
  </section>;
}
