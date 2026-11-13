import { useEffect, useState, type FormEvent } from "react";
import { ShieldCheck } from "lucide-react";
import { Notice } from "../../components/SiteLayout";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import type { UserRoleMapEntry } from "../../lib/types";

export function PrivilegedRoleManagement() {
  const { token } = useAuth();
  const [userId, setUserId] = useState("");
  const [role, setRole] = useState<"admin" | "delivery_person">("delivery_person");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [assignments, setAssignments] = useState<UserRoleMapEntry[]>([]);
  const [loadingAssignments, setLoadingAssignments] = useState(true);
  const [assignmentError, setAssignmentError] = useState("");

  useEffect(() => {
    if (!token) return;
    let active = true;
    setLoadingAssignments(true);
    setAssignmentError("");
    api.listUserRoleMap(token)
      .then((rows) => {
        if (active) setAssignments(rows);
      })
      .catch((reason) => {
        if (active) setAssignmentError(reason instanceof Error ? reason.message : "Could not load user roles.");
      })
      .finally(() => {
        if (active) setLoadingAssignments(false);
      });
    return () => { active = false; };
  }, [token]);

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
    <div className="admin-table-section">
      <h3>Assigned user roles</h3>
      {assignmentError && <Notice tone="error">{assignmentError}</Notice>}
      {loadingAssignments ? <p>Loading user roles...</p> : assignments.length ? <div className="table-scroll"><table>
        <thead><tr><th>User ID</th><th>Name</th><th>Email</th><th>Role ID</th><th>Role</th></tr></thead>
        <tbody>{assignments.map((assignment) => <tr key={assignment.user_id + "-" + assignment.role_id}>
          <td>{assignment.user_id}</td><td>{assignment.full_name}</td><td>{assignment.email}</td>
          <td>{assignment.role_id}</td><td>{assignment.role_name.replaceAll("_", " ")}</td>
        </tr>)}</tbody>
      </table></div> : <p>No active user-role assignments found.</p>}
    </div>
  </section>;
}
