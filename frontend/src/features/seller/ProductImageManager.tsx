import { useEffect, useRef, useState } from "react";
import { ImagePlus, Star, Trash2, Upload } from "lucide-react";
import { Notice } from "../../components/SiteLayout";
import { api } from "../../lib/api";
import type { Product, ProductImage } from "../../lib/types";

export function ProductImageManager({ product, token, onPrimaryChange }: {
  product: Product;
  token: string;
  onPrimaryChange: (imageUrl: string | null) => void;
}) {
  const [images, setImages] = useState<ProductImage[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let active = true;
    api.listProductImages(product.id).then((items) => { if (active) setImages(items); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Could not load product images."); });
    return () => { active = false; };
  }, [product.id]);

  async function update(action: () => Promise<ProductImage[]>) {
    setBusy(true);
    setError("");
    try {
      const items = await action();
      setImages(items);
      onPrimaryChange(items.find((image) => image.is_primary)?.image_url ?? null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not update product images.");
    } finally { setBusy(false); }
  }

  function chooseFiles(selected: FileList | null) {
    const chosen = Array.from(selected ?? []);
    if (chosen.length + images.length > 8) {
      setError("A product can have up to 8 images.");
      setFiles([]);
      return;
    }
    setError("");
    setFiles(chosen);
  }

  return <section className="product-image-manager" aria-label="Product image management">
    <div className="image-manager-heading"><ImagePlus size={16} /><b>Product images</b><span>{images.length}/8</span></div>
    <p>Add JPEG, PNG, or WebP images (up to 5 MB each). The primary image appears on product cards.</p>
    {error && <Notice tone="error">{error}</Notice>}
    <div className="image-manager-grid">{images.map((image) => <article className="image-manager-item" key={image.id}>
      <img src={image.image_url} alt="Product" />
      {image.is_primary && <span className="primary-image-tag">Primary</span>}
      <div className="image-manager-actions">
        {!image.is_primary && <button type="button" disabled={busy} onClick={() => void update(() => api.setPrimaryProductImage(product.id, image.id, token))} aria-label="Set as primary"><Star size={14} /></button>}
        <label className="image-replace-button" title="Replace image"><Upload size={14} /><input type="file" accept="image/jpeg,image/png,image/webp" disabled={busy} onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) void update(() => api.replaceProductImage(product.id, image.id, file, token));
          event.target.value = "";
        }} /></label>
        <button type="button" disabled={busy} onClick={() => void update(() => api.deleteProductImage(product.id, image.id, token))} aria-label="Delete image"><Trash2 size={14} /></button>
      </div>
    </article>)}</div>
    <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={(event) => chooseFiles(event.target.files)} disabled={busy || images.length >= 8} />
    <button type="button" className="button button-outline" disabled={busy || !files.length} onClick={() => void update(async () => {
      const items = await api.uploadProductImages(product.id, files, token);
      setFiles([]);
      if (input.current) input.current.value = "";
      return items;
    })}>Upload {files.length || "selected"} image{files.length === 1 ? "" : "s"}</button>
  </section>;
}
