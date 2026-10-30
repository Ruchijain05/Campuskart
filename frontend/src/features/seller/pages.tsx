import { useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowDownToLine, ArrowRight, BadgePlus, CircleHelp, Package, Search, Store, Upload } from "lucide-react";
import { Link } from "react-router-dom";
import { LoadingState, Notice, PageTitle } from "../../components/SiteLayout";
import { api, BulkProductUploadError, type BulkProductRowError } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { buildCategoryTree, flattenCategoryTree } from "../../lib/categoryTree";
import type { Category, Product } from "../../lib/types";

export function SellerApplicationPage() {
  const { user, token } = useAuth();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      setError("Sign in with a buyer account before applying.");
      return;
    }
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      const application = await api.applyToSell(message, token);
      setSuccess(`Your application is ${application.status}. An admin will review it.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not submit your application.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="content-narrow seller-apply-page">
      <div className="seller-hero">
        <div className="seller-hero-icon"><Store size={27} /></div>
        <span className="eyebrow">SELLER COMMUNITY</span>
        <h1>Your good finds<br />deserve a bigger audience.</h1>
        <p>Apply to become a CampusKart seller and share the things your campus community needs.</p>
      </div>
      <div className="application-grid">
        <form className="application-card" onSubmit={submit}>
          <h2>Let's get you started</h2>
          {user?.role === "seller" && <Notice tone="success">You're already approved as a seller. <Link to="/seller/products">Visit Seller Studio</Link>.</Notice>}
          {!user && <Notice>Sign in with your buyer account to apply. <Link to="/login">Sign in</Link>.</Notice>}
          {error && <Notice tone="error">{error}</Notice>}
          {success && <Notice tone="success">{success}</Notice>}
          <label>Tell us what you'd like to sell <span className="optional-label">OPTIONAL</span><textarea rows={5} maxLength={2000} value={message} onChange={(event) => setMessage(event.target.value)} placeholder="What are you excited to bring to your campus community?" /></label>
          <button className="button button-dark" disabled={!user || user.role !== "buyer" || busy}>{busy ? "Sending application..." : "Submit application"} <ArrowRight size={16} /></button>
          <small className="field-hint">Only buyer accounts can apply. You can apply again if a previous application was rejected.</small>
        </form>
        <aside className="application-aside">
          <h3>What happens next?</h3>
          <div className="timeline"><span>01</span><div><b>Send your application</b><p>Tell us a little about your seller plans.</p></div></div>
          <div className="timeline"><span>02</span><div><b>Our team reviews it</b><p>An admin will review your application.</p></div></div>
          <div className="timeline"><span>03</span><div><b>Start listing</b><p>Approved? Your seller tools will be ready.</p></div></div>
          <div className="aside-note"><CircleHelp size={17} /> Seller applications are reviewed by CampusKart admins.</div>
        </aside>
      </div>
    </div>
  );
}

const emptyProduct = {
  name: "",
  description: "",
  price: "",
  stock: "0",
  image_url: "",
  category_id: "",
};

function downloadProductTemplate() {
  const contents = [
    "name,price,stock,image_url,category_id,description",
    '"Example textbook",250.00,5,,,"Gently used course textbook"',
  ].join("\r\n");
  const url = URL.createObjectURL(new Blob([contents], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "campuskart-products-template.csv";
  link.click();
  URL.revokeObjectURL(url);
}

export function SellerProductsPage() {
  const { token, user } = useAuth();
  const [categories, setCategories] = useState<Category[]>([]);
  const [form, setForm] = useState(emptyProduct);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);
  const [productId, setProductId] = useState("");
  const [loadedProduct, setLoadedProduct] = useState<Product | null>(null);
  const [editForm, setEditForm] = useState(emptyProduct);
  const [savingEdit, setSavingEdit] = useState(false);
  const [manageError, setManageError] = useState("");
  const [loadingProduct, setLoadingProduct] = useState(false);
  const [bulkFile, setBulkFile] = useState<File | null>(null);
  const [bulkErrors, setBulkErrors] = useState<BulkProductRowError[]>([]);
  const [bulkError, setBulkError] = useState("");
  const [bulkSuccess, setBulkSuccess] = useState("");
  const [uploadingBulk, setUploadingBulk] = useState(false);
  const bulkFileInput = useRef<HTMLInputElement>(null);
  const categoryOptions = flattenCategoryTree(buildCategoryTree(categories));

  useEffect(() => {
    let active = true;
    api.listCategories().then((items) => {
      if (active) setCategories(items);
    }).catch((reason: unknown) => {
      if (active) setError(reason instanceof Error ? reason.message : "Could not load categories.");
    });
    return () => { active = false; };
  }, []);

  function setField(key: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function submitBulkUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !bulkFile) return;
    setUploadingBulk(true);
    setBulkErrors([]);
    setBulkError("");
    setBulkSuccess("");
    try {
      const result = await api.uploadProducts(bulkFile, token);
      setBulkSuccess(`Imported ${result.imported_count} products successfully.`);
      setBulkFile(null);
      if (bulkFileInput.current) bulkFileInput.current.value = "";
    } catch (reason) {
      if (reason instanceof BulkProductUploadError) {
        setBulkError(reason.message);
        setBulkErrors(reason.rowErrors);
      } else {
        setBulkError(reason instanceof Error ? reason.message : "Could not import products.");
      }
    } finally {
      setUploadingBulk(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      const input = {
        name: form.name,
        description: form.description.trim() || null,
        price: Number(form.price),
        stock: Number(form.stock),
        image_url: form.image_url.trim() || null,
        category_id: form.category_id ? Number(form.category_id) : null,
      };
      const product = await api.createProduct(input, token);
      setForm(emptyProduct);
      setSuccess(`“${product.name}” is now listed as product #${product.id}.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not create product.");
    } finally {
      setBusy(false);
    }
  }

  async function loadProduct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setManageError("");
    setLoadedProduct(null);
    const id = Number(productId);
    if (!Number.isInteger(id) || id < 1) {
      setManageError("Enter a valid product ID.");
      return;
    }
    setLoadingProduct(true);
    try {
      const product = await api.getProduct(id);
      setLoadedProduct(product);
      setEditForm({
        name: product.name,
        description: product.description ?? "",
        price: String(product.price),
        stock: String(product.stock),
        image_url: product.image_url ?? "",
        category_id: product.category_id ? String(product.category_id) : "",
      });
    } catch (reason) {
      setManageError(reason instanceof Error ? reason.message : "Could not find that product.");
    } finally {
      setLoadingProduct(false);
    }
  }

  async function saveProduct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !loadedProduct) return;
    setSavingEdit(true);
    setManageError("");
    try {
      const updated = await api.updateProduct(loadedProduct.id, {
        name: editForm.name,
        description: editForm.description.trim() || null,
        price: Number(editForm.price),
        stock: Number(editForm.stock),
        image_url: editForm.image_url.trim() || null,
        category_id: editForm.category_id ? Number(editForm.category_id) : null,
      }, token);
      setLoadedProduct(updated);
      setSuccess(`“${updated.name}” updated.`);
    } catch (reason) {
      setManageError(reason instanceof Error ? reason.message : "Could not update product.");
    } finally {
      setSavingEdit(false);
    }
  }

  async function deleteProduct() {
    if (!token || !loadedProduct || !window.confirm(`Delete "${loadedProduct.name}"?`)) return;
    setManageError("");
    try {
      await api.deleteProduct(loadedProduct.id, token);
      setLoadedProduct(null);
      setSuccess("Product deleted.");
    } catch (reason) {
      setManageError(reason instanceof Error ? reason.message : "Could not delete product.");
    }
  }

  return (
    <div className="seller-dashboard">
      <PageTitle eyebrow="SELLER STUDIO" title="Make your next listing." description="Add a product to the campus marketplace and keep your details up to date." />
      {error && <Notice tone="error">{error}</Notice>}
      {success && <Notice tone="success">{success}</Notice>}
      <div className="seller-dashboard-grid">
        <form className="form-card" onSubmit={submit}>
          <div className="form-card-heading"><span className="card-icon"><BadgePlus size={19} /></span><div><h2>List a product</h2><p>Give your campus community the details.</p></div></div>
          <div className="field-grid">
            <label className="field-full">Product name<input required minLength={1} maxLength={150} value={form.name} onChange={(event) => setField("name", event.target.value)} placeholder="e.g. Chemistry lab coat" /></label>
            <label>Price (₹)<input type="number" min="0.01" step="0.01" required value={form.price} onChange={(event) => setField("price", event.target.value)} placeholder="0.00" /></label>
            <label>Available quantity<input type="number" min="0" step="1" required value={form.stock} onChange={(event) => setField("stock", event.target.value)} /></label>
            <label className="field-full">Category<select value={form.category_id} onChange={(event) => setField("category_id", event.target.value)}><option value="">No category</option>{categoryOptions.map(({ category, depth, path }) => <option key={category.id} value={category.id}>{`${"— ".repeat(depth)}${path}`}</option>)}</select></label>
            <label className="field-full">Image URL<input type="url" value={form.image_url} onChange={(event) => setField("image_url", event.target.value)} placeholder="https://..." /></label>
            <label className="field-full">Description<textarea rows={4} value={form.description} onChange={(event) => setField("description", event.target.value)} placeholder="What should buyers know?" /></label>
          </div>
          <button className="button button-dark" disabled={busy}>{busy ? "Publishing..." : "Publish product"} <ArrowRight size={16} /></button>
          {user?.role === "admin" && <small className="field-hint">Products created as an admin are not assigned to a seller account.</small>}
        </form>
        <aside className="manage-card">
          <span className="card-icon"><Package size={19} /></span><h2>Manage a product</h2>
          <p>Enter a product ID to check it. Sellers can edit or remove their own listings; admins can manage any listing.</p>
          <form className="manage-search" onSubmit={loadProduct}><span><Search size={17} /><input type="number" min="1" required value={productId} onChange={(event) => setProductId(event.target.value)} placeholder="Product ID" /></span><button aria-label="Find product"><ArrowRight size={17} /></button></form>
          {loadingProduct && <LoadingState label="Looking up product..." />}
          {manageError && <Notice tone="error">{manageError}</Notice>}
              {loadedProduct && <form className="managed-product" onSubmit={saveProduct}>
                <b>Edit {loadedProduct.name}</b>
                <label>Product name<input required minLength={1} maxLength={150} value={editForm.name} onChange={(event) => setEditForm((current) => ({ ...current, name: event.target.value }))} /></label>
                <div className="field-grid">
                  <label>Price (₹)<input type="number" min="0.01" step="0.01" required value={editForm.price} onChange={(event) => setEditForm((current) => ({ ...current, price: event.target.value }))} /></label>
                  <label>Quantity<input type="number" min="0" required value={editForm.stock} onChange={(event) => setEditForm((current) => ({ ...current, stock: event.target.value }))} /></label>
                  <label className="field-full">Category<select value={editForm.category_id} onChange={(event) => setEditForm((current) => ({ ...current, category_id: event.target.value }))}><option value="">No category</option>{categoryOptions.map(({ category, depth, path }) => <option key={category.id} value={category.id}>{`${"— ".repeat(depth)}${path}`}</option>)}</select></label>
                  <label className="field-full">Image URL<input type="url" value={editForm.image_url} onChange={(event) => setEditForm((current) => ({ ...current, image_url: event.target.value }))} placeholder="https://..." /></label>
                  <label className="field-full">Description<textarea rows={3} value={editForm.description} onChange={(event) => setEditForm((current) => ({ ...current, description: event.target.value }))} /></label>
                </div>
                <button className="button button-dark" disabled={savingEdit}>{savingEdit ? "Saving..." : "Save changes"}</button>
                <button type="button" className="button button-danger" onClick={deleteProduct}>Delete listing</button>
                <small>Product ownership is verified by the backend.</small>
              </form>}
          <div className="aside-note"><CircleHelp size={17} /> Your account must have seller or admin access.</div>
        </aside>
      </div>
      <form className="form-card bulk-upload-card" onSubmit={submitBulkUpload}>
        <div className="form-card-heading">
          <span className="card-icon"><Upload size={19} /></span>
          <div><h2>Bulk product upload</h2><p>Add multiple listings from a CSV or Excel workbook.</p></div>
        </div>
        <div className="bulk-upload-guidance">
          <p>Use the template columns: <b>name, price, stock</b> are required; description, image_url, and category_id are optional.</p>
          <button type="button" className="button button-outline bulk-template-button" onClick={downloadProductTemplate}>
            <ArrowDownToLine size={15} /> Download CSV template
          </button>
          <details className="bulk-category-help">
            <summary>Find category IDs</summary>
            <ul>
              {categoryOptions.map(({ category, path }) => (
                <li key={category.id}><code>{category.id}</code> — {path}</li>
              ))}
            </ul>
          </details>
          <small className="field-hint">CSV or XLSX, up to 5 MB and 500 product rows. If any row has an error, nothing is imported.</small>
        </div>
        <label className="bulk-file-label">
          Choose a file
          <input
            ref={bulkFileInput}
            type="file"
            accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            onChange={(event) => {
              setBulkFile(event.target.files?.[0] ?? null);
              setBulkErrors([]);
              setBulkError("");
              setBulkSuccess("");
            }}
          />
        </label>
        {bulkFile && <p className="bulk-selected-file">{bulkFile.name}</p>}
        {bulkError && <Notice tone="error">{bulkError}</Notice>}
        {bulkSuccess && <Notice tone="success">{bulkSuccess}</Notice>}
        {bulkErrors.length > 0 && (
          <div className="bulk-row-errors" role="alert">
            <b>Fix these rows and upload the file again:</b>
            <ul>
              {bulkErrors.map((item, index) => (
                <li key={`${item.row}-${item.field}-${index}`}>
                  <b>Row {item.row}</b> · {item.field}: {item.message}
                </li>
              ))}
            </ul>
          </div>
        )}
        <button className="button button-dark" disabled={!bulkFile || uploadingBulk}>
          {uploadingBulk ? "Validating and importing..." : "Validate and import products"}
          <ArrowRight size={16} />
        </button>
      </form>
    </div>
  );
}
