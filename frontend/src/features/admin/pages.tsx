import { useEffect, useState, type FormEvent } from "react";
import { Check, FolderPlus, Pencil, ShieldCheck, X } from "lucide-react";
import { LoadingState, Notice, PageTitle } from "../../components/SiteLayout";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { buildCategoryTree, flattenCategoryTree, getCategoryDescendantIds } from "../../lib/categoryTree";
import type { Category, SellerApplication } from "../../lib/types";

export function AdminPage() {
  const { token } = useAuth();
  const [applications, setApplications] = useState<SellerApplication[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [categoryName, setCategoryName] = useState("");
  const [categoryDescription, setCategoryDescription] = useState("");
  const [categoryParentId, setCategoryParentId] = useState("");
  const [editingCategoryId, setEditingCategoryId] = useState<number | null>(null);
  const [editingCategoryName, setEditingCategoryName] = useState("");
  const [editingCategoryDescription, setEditingCategoryDescription] = useState("");
  const [editingCategoryParentId, setEditingCategoryParentId] = useState("");
  const [reviewNotes, setReviewNotes] = useState<Record<number, string>>({});
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(true);
  const categoryOptions = flattenCategoryTree(buildCategoryTree(categories));
  const editableCategoryIds = editingCategoryId === null
    ? new Set<number>()
    : getCategoryDescendantIds(categories, editingCategoryId);

  async function loadData() {
    if (!token) return;
    setLoading(true);
    try {
      const [pending, groups] = await Promise.all([
        api.listSellerApplications(token),
        api.listCategories(),
      ]);
      setApplications(pending);
      setCategories(groups);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load admin data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void loadData(); }, [token]);

  async function review(id: number, decision: "approved" | "rejected") {
    if (!token) return;
    setError("");
    setSuccess("");
    try {
      await api.reviewSellerApplication(id, decision, reviewNotes[id] ?? "", token);
      setApplications((items) => items.filter((item) => item.id !== id));
      setSuccess(`Application #${id} ${decision}.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not review application.");
    }
  }

  async function addCategory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setError("");
    setSuccess("");
    try {
      const category = await api.createCategory(
        {
          name: categoryName,
          description: categoryDescription.trim() || null,
          parent_id: categoryParentId ? Number(categoryParentId) : null,
        },
        token,
      );
      setCategories((items) => [...items, category]);
      setCategoryName("");
      setCategoryDescription("");
      setCategoryParentId("");
      setSuccess(`Category “${category.name}” added.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not add category.");
    }
  }

  async function removeCategory(category: Category) {
    if (!token || !window.confirm(`Remove "${category.name}"?`)) return;
    setError("");
    try {
      await api.deleteCategory(category.id, token);
      setCategories((items) => items.filter((item) => item.id !== category.id));
      setSuccess(`Category “${category.name}” removed.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not remove category.");
    }
  }

  function startEditingCategory(category: Category) {
    setEditingCategoryId(category.id);
    setEditingCategoryName(category.name);
    setEditingCategoryDescription(category.description ?? "");
    setEditingCategoryParentId(category.parent_id === null ? "" : String(category.parent_id));
  }

  async function saveCategory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || editingCategoryId === null) return;
    setError("");
    try {
      const updated = await api.updateCategory(editingCategoryId, {
        name: editingCategoryName,
        description: editingCategoryDescription.trim() || null,
        parent_id: editingCategoryParentId ? Number(editingCategoryParentId) : null,
      }, token);
      setCategories((items) => items.map((item) => item.id === updated.id ? updated : item));
      setEditingCategoryId(null);
      setSuccess(`Category “${updated.name}” updated.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not update category.");
    }
  }

  return (
    <div className="admin-page">
      <PageTitle eyebrow="CAMPUSKART ADMIN" title="Keep good things moving." description="Review seller applications and keep the catalog organized." />
      {error && <Notice tone="error">{error}</Notice>}
      {success && <Notice tone="success">{success}</Notice>}
      <div className="admin-grid">
        <section className="admin-card">
          <div className="form-card-heading"><span className="card-icon"><ShieldCheck size={19} /></span><div><h2>Seller applications</h2><p>Pending requests from your community.</p></div><span className="count-badge">{applications.length}</span></div>
          {loading ? <LoadingState label="Loading applications..." /> : applications.length ? (
            <div className="application-list">
              {applications.map((application) => (
                <article className="admin-application" key={application.id}>
                  <div className="application-meta"><span className="application-id">APPLICATION #{application.id}</span><span>{new Date(application.created_at).toLocaleDateString()}</span></div>
                  <p>{application.message || "No message included."}</p>
                  <label>Review note<textarea rows={2} maxLength={500} value={reviewNotes[application.id] ?? ""} onChange={(event) => setReviewNotes((current) => ({ ...current, [application.id]: event.target.value }))} placeholder="Optional note for the applicant" /></label>
                  <div className="review-actions"><button className="button button-approve" onClick={() => void review(application.id, "approved")}><Check size={15} /> Approve</button><button className="button button-reject" onClick={() => void review(application.id, "rejected")}><X size={15} /> Reject</button></div>
                </article>
              ))}
            </div>
          ) : <div className="empty-admin"><span>✦</span><p>No pending applications.</p></div>}
        </section>
        <section className="admin-card category-admin">
          <div className="form-card-heading"><span className="card-icon"><FolderPlus size={19} /></span><div><h2>Categories</h2><p>Organize campus finds.</p></div></div>
          <form className="category-add-form" onSubmit={addCategory}>
            <label>Category name<input required maxLength={100} value={categoryName} onChange={(event) => setCategoryName(event.target.value)} placeholder="e.g. Study essentials" /></label>
            <label>Description <span className="optional-label">OPTIONAL</span><input maxLength={500} value={categoryDescription} onChange={(event) => setCategoryDescription(event.target.value)} placeholder="What belongs here?" /></label>
            <label>Parent category<select value={categoryParentId} onChange={(event) => setCategoryParentId(event.target.value)}><option value="">Main category</option>{categoryOptions.map(({ category, depth, path }) => <option key={category.id} value={category.id}>{`${"— ".repeat(depth)}${path}`}</option>)}</select></label>
            <button className="button button-dark"><FolderPlus size={16} /> Add category</button>
          </form>
          <div className="category-admin-list">
            {categoryOptions.map(({ category, depth, path }) => editingCategoryId === category.id ? (
              <form className="category-edit-form" key={category.id} onSubmit={saveCategory}>
                <input aria-label="Category name" required maxLength={100} value={editingCategoryName} onChange={(event) => setEditingCategoryName(event.target.value)} />
                <input aria-label="Category description" maxLength={500} value={editingCategoryDescription} onChange={(event) => setEditingCategoryDescription(event.target.value)} placeholder="Description (optional)" />
                <select aria-label="Parent category" value={editingCategoryParentId} onChange={(event) => setEditingCategoryParentId(event.target.value)}><option value="">Main category</option>{categoryOptions.filter((option) => !editableCategoryIds.has(option.category.id)).map(({ category: optionCategory, depth: optionDepth, path: optionPath }) => <option key={optionCategory.id} value={optionCategory.id}>{`${"— ".repeat(optionDepth)}${optionPath}`}</option>)}</select>
                <button aria-label="Save category"><Check size={16} /></button>
                <button type="button" aria-label="Cancel category edit" onClick={() => setEditingCategoryId(null)}><X size={16} /></button>
              </form>
            ) : (
              <div key={category.id} style={{ paddingLeft: `${depth * 14}px` }}>
                <span title={path}>{category.name}{category.description && <small>{category.description}</small>}</span>
                <div className="category-actions">
                  <button aria-label={`Edit ${category.name}`} onClick={() => startEditingCategory(category)}><Pencil size={15} /></button>
                  <button aria-label={`Delete ${category.name}`} onClick={() => void removeCategory(category)}><X size={16} /></button>
                </div>
              </div>
            ))}
            {!categories.length && <span className="field-hint">No categories yet.</span>}
          </div>
        </section>
      </div>
    </div>
  );
}
