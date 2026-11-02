import { useEffect, useState, type FormEvent } from "react";
import { Activity, AlertTriangle, Check, FolderPlus, IndianRupee, Package, PackageCheck, Pencil, ShoppingCart, ShieldCheck, Star, Store, UserPlus, UserRound, Users, X } from "lucide-react";
import { LoadingState, Notice, PageTitle } from "../../components/SiteLayout";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { buildCategoryTree, flattenCategoryTree, getCategoryDescendantIds } from "../../lib/categoryTree";
import { formatPrice } from "../../components/ProductCard";
import type { AdminDashboard, AdminDailySummary, Category, LowStockProduct, Order, OrderStatus, SellerApplication } from "../../lib/types";
import { ReturnsManagement } from "./ReturnsManagement";
import { AdminSupportTickets } from "./AdminSupportTickets";
import { CouponManagement } from "./CouponManagement";
import { ProductOffers } from "./ProductOffers";
import { ShippingManagement } from "./ShippingManagement";
import { InvoiceDownloadButton } from "../../components/InvoiceDownloadButton";
import { PayoutManagement } from "./PayoutManagement";
import { BundleManagement } from "./BundleManagement";
import { CampusPickupManagement } from "./CampusPickupManagement";
import { AdminProductRequests } from "./AdminProductRequests";

function AdminBarChart({ title, values, field, color, icon }: {
  title: string;
  values: AdminDailySummary[];
  field: "orders" | "registrations";
  color: string;
  icon: "orders" | "users";
}) {
  const data = values.map((item) => item[field]);
  const maxValue = Math.max(...data, 1);
  const Icon = icon === "orders" ? ShoppingCart : UserPlus;
  const left = 30;
  const top = 12;
  const chartHeight = 112;
  const chartWidth = 470;
  const step = chartWidth / Math.max(values.length, 1);
  const barWidth = Math.min(30, step * 0.52);
  return <section className="admin-chart-card">
    <div className="admin-chart-heading"><span><Icon size={16} /></span><div><h3>{title}</h3><small>Last 7 days</small></div></div>
    <svg className="admin-bar-chart" viewBox="0 0 530 166" role="img" aria-label={`${title} for the last seven days`}>
      {[0, 1, 2, 3].map((line) => {
        const y = top + (chartHeight / 3) * line;
        return <line key={line} x1={left} x2={left + chartWidth} y1={y} y2={y} className="admin-chart-gridline" />;
      })}
      {values.map((item, index) => {
        const value = item[field];
        const height = value ? Math.max(3, (value / maxValue) * chartHeight) : 0;
        const x = left + index * step + (step - barWidth) / 2;
        const y = top + chartHeight - height;
        const label = new Date(`${item.date}T00:00:00`).toLocaleDateString(undefined, { weekday: "short" });
        return <g key={item.date}>
          <rect x={x} y={y} width={barWidth} height={height} rx="4" fill={color} />
          <text x={x + barWidth / 2} y={Math.max(10, y - 5)} className="admin-chart-value" textAnchor="middle">{value || ""}</text>
          <text x={x + barWidth / 2} y="148" className="admin-chart-label" textAnchor="middle">{label}</text>
        </g>;
      })}
    </svg>
  </section>;
}

function AdminOverview({ data }: { data: AdminDashboard }) {
  const stats = [
    { label: "Total users", value: data.total_users, icon: Users, tone: "blue" },
    { label: "Buyers", value: data.buyers, icon: UserRound, tone: "violet" },
    { label: "Sellers", value: data.sellers, icon: Store, tone: "green" },
    { label: "Products", value: data.total_products, icon: Package, tone: "amber" },
    { label: "Orders", value: data.total_orders, icon: ShoppingCart, tone: "blue" },
    { label: "Total revenue", value: formatPrice(data.total_revenue), icon: IndianRupee, tone: "green" },
  ];
  return <section className="admin-overview" aria-label="Store overview">
    <div className="admin-overview-heading"><div><span className="eyebrow">STORE SNAPSHOT</span><h2>CampusKart at a glance</h2></div><p>Revenue shows non-cancelled order value. COD collection may still be pending.</p></div>
    <div className="admin-stat-grid">{stats.map(({ label, value, icon: Icon, tone }) => <article className="admin-stat-card" key={label}>
      <span className={`admin-stat-icon tone-${tone}`}><Icon size={18} /></span><small>{label}</small><strong>{value}</strong>
    </article>)}</div>
    <div className="admin-analytics-grid">
      <AdminBarChart title="Orders placed" values={data.daily_summary} field="orders" color="#6375d7" icon="orders" />
      <AdminBarChart title="New accounts" values={data.daily_summary} field="registrations" color="#55a889" icon="users" />
    </div>
    <section className="admin-activity-card"><div className="admin-activity-heading"><h3><Activity size={17} /> Recent activity</h3><span>Latest updates across the store</span></div>
      {data.recent_activities.length ? <div className="admin-activity-list">{data.recent_activities.map((item) => {
        const Icon = item.kind === "user" ? UserPlus : item.kind === "product" ? Package : item.kind === "order" ? ShoppingCart : item.kind === "review" ? Star : Store;
        return <article className="admin-activity-item" key={item.id}><span className={`admin-activity-icon activity-${item.kind}`}><Icon size={15} /></span><div><b>{item.title}</b><p>{item.detail}</p></div><time dateTime={item.created_at}>{new Date(item.created_at).toLocaleString()}</time></article>;
      })}</div> : <p className="admin-activity-empty">No activity yet.</p>}
    </section>
  </section>;
}

export function AdminPage() {
  const { token } = useAuth();
  const [dashboard, setDashboard] = useState<AdminDashboard | null>(null);
  const [applications, setApplications] = useState<SellerApplication[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [lowStockProducts, setLowStockProducts] = useState<LowStockProduct[]>([]);
  const [updatingOrderId, setUpdatingOrderId] = useState<number | null>(null);
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
      const [pending, groups, allOrders, overview, lowStock] = await Promise.all([
        api.listSellerApplications(token),
        api.listCategories(),
        api.listAdminOrders(token),
        api.getAdminDashboard(token),
        api.listAdminLowStock(token),
      ]);
      setApplications(pending);
      setCategories(groups);
      setOrders(allOrders);
      setDashboard(overview);
      setLowStockProducts(lowStock);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load admin data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void loadData(); }, [token]);

  async function changeOrderStatus(orderId: number, nextStatus: OrderStatus) {
    if (!token) return;
    setError(""); setSuccess(""); setUpdatingOrderId(orderId);
    try {
      const updated = await api.updateOrderStatus(orderId, nextStatus, token);
      setOrders((items) => items.map((item) => item.id === orderId ? updated : item));
      setSuccess(`Order #${orderId} marked ${nextStatus}.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not update order status.");
    } finally { setUpdatingOrderId(null); }
  }

  function nextStatuses(orderStatus: OrderStatus): OrderStatus[] {
    const transitions: Record<OrderStatus, OrderStatus[]> = {
      placed: ["confirmed", "cancelled"],
      confirmed: ["shipped", "cancelled"],
      shipped: ["delivered"],
      delivered: [],
      cancelled: [],
    };
    return transitions[orderStatus];
  }

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
      {loading && !dashboard ? <div className="admin-overview-loading"><LoadingState label="Loading store overview..." /></div> : dashboard && <AdminOverview data={dashboard} />}
      <div className="admin-grid">
        <section className="admin-card admin-orders-card">
          <div className="form-card-heading"><span className="card-icon"><PackageCheck size={19} /></span><div><h2>Orders</h2><p>Track and update order progress.</p></div><span className="count-badge">{orders.length}</span></div>
          {loading ? <LoadingState label="Loading orders..." /> : orders.length ? <div className="admin-order-list">{orders.map((order) => {
            const availableStatuses = nextStatuses(order.status);
            return <article className="admin-order" key={order.id}>
              <div className="admin-order-heading"><div><b>ORDER #{order.id}</b><small>{new Date(order.created_at).toLocaleString()}</small></div><strong>{formatPrice(order.total)}</strong></div>
              {Number(order.discount_amount) > 0 && <small>Subtotal {formatPrice(order.subtotal)} · Coupon {order.coupon_code} · Discount −{formatPrice(order.discount_amount)}</small>}
              <p><b>{order.delivery_name}</b> · {order.delivery_phone}<br />{order.address_line}, {order.city}, {order.state} {order.postal_code}</p>
              <small>{order.items.map((item) => `${item.product_name} × ${item.quantity}`).join(" · ")}</small>
              <p><b>Payment:</b> {order.payment_method === "razorpay" ? "Razorpay" : order.payment_method === "coupon" ? "No payment due" : "Cash on Delivery"} · {order.payment_status}<br />{order.razorpay_order_id && <>Razorpay order ID: <code>{order.razorpay_order_id}</code><br /></>}{order.razorpay_payment_id && <>Razorpay payment ID: <code>{order.razorpay_payment_id}</code></>}</p>
              <InvoiceDownloadButton orderId={order.id} />
              <label>Order status<select value={order.status} disabled={!availableStatuses.length || updatingOrderId === order.id} onChange={(event) => void changeOrderStatus(order.id, event.target.value as OrderStatus)}>
                <option value={order.status}>{order.status}</option>
                {availableStatuses.map((status) => <option value={status} key={status}>{status}</option>)}
              </select></label>
            </article>;
          })}</div> : <div className="empty-admin"><span>✦</span><p>No orders yet.</p></div>}
        </section>
        <section className="admin-card admin-low-stock-card">
          <div className="form-card-heading"><span className="card-icon"><AlertTriangle size={19} /></span><div><h2>Low-stock products</h2><p>Active products at or below their seller-set threshold.</p></div><span className="count-badge">{lowStockProducts.length}</span></div>
          {loading ? <LoadingState label="Loading low-stock products..." /> : lowStockProducts.length ? <div className="admin-low-stock-list">{lowStockProducts.map((product) => <article key={product.id}>
            <div><b>{product.name}</b><small>Seller: {product.seller_name ?? "Unassigned"} · Product #{product.id}</small></div>
            <strong>{product.stock} left <span>/ threshold {product.low_stock_threshold}</span></strong>
          </article>)}</div> : <div className="empty-admin"><span>✓</span><p>No active products are below their thresholds.</p></div>}
        </section>
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
      <ProductOffers />
      <BundleManagement />
      <ShippingManagement />
      <CampusPickupManagement />
      <PayoutManagement />
      <CouponManagement />
      <AdminSupportTickets />
      <AdminProductRequests />
      <ReturnsManagement />
    </div>
  );
}
