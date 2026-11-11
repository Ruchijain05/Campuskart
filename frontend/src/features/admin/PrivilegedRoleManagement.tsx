import { useState, type FormEvent } from "react";
import { ShieldCheck } from "lucide-react";
import { Notice } from "../../components/SiteLayout";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";

export function PrivilegedRoleManagement() {
  const { token } = useAuth();
  const [userId, setUserId] = useState("");
  const [role, setRole] = useState<"admin" | "delivery_person">("delivery_person");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setBusy(true); setError(""); setSuccess("");
    try {
      const user = await api.assignPrivilegedRole(Number(userId), role, token);
      setSuccess(`${role.replace("_", " ")} access assigned to ${user.full_name} (${user.email}).`);
      setUserId("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not assign the role.");
    } finally { setBusy(false); }
  }

  return <section className="admin-card">
    <div className="form-card-heading"><span className="card-icon"><ShieldCheck size={18} /></span><div><h2>Assign privileged access</h2><p>Add Admin or Delivery Person access to an existing account. Its current role and sign-in stay intact.</p></div></div>
    {error && <Notice tone="error">{error}</Notice>}{success && <Notice tone="success">{success}</Notice>}
    <form className="form-stack" onSubmit={(event) => void submit(event)}>
      <label>CampusKart account ID<input required type="number" min={1} step={1} value={userId} onChange={(event) => setUserId(event.target.value)} /></label>
      <label>Role<select value={role} onChange={(event) => setRole(event.target.value as "admin" | "delivery_person")}><option value="delivery_person">Delivery Person</option><option value="admin">Admin</option></select></label>
      <button className="button button-dark" disabled={busy}>{busy ? "Assigning..." : "Assign role"}</button>
    </form>
  </section>;
}
