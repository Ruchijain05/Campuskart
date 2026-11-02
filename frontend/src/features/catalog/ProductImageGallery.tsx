import { useEffect, useState } from "react";
import { BookOpen } from "lucide-react";
import { api } from "../../lib/api";
import type { ProductImage } from "../../lib/types";

export function ProductImageGallery({ productId, productName, fallbackImage }: {
  productId: number;
  productName: string;
  fallbackImage: string | null;
}) {
  const [images, setImages] = useState<ProductImage[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    setImages([]);
    setFailed(false);
    api.listProductImages(productId).then((items) => {
      if (active) {
        setImages(items);
        setSelected(items.find((image) => image.is_primary)?.image_url ?? items[0]?.image_url ?? fallbackImage);
      }
    }).catch(() => {
      if (active) setSelected(fallbackImage);
    });
    return () => { active = false; };
  }, [productId, fallbackImage]);

  const visibleImages = images.length ? images : fallbackImage ? [{
    id: -1, product_id: productId, image_url: fallbackImage, is_primary: true, created_at: "",
  }] : [];

  return <div className="product-image-gallery">
    <div className="detail-image">
      {selected && !failed
        ? <img src={selected} alt={productName} onError={() => setFailed(true)} />
        : <div className="image-placeholder detail-placeholder"><BookOpen size={64} /><span>Campus find</span></div>}
    </div>
    {visibleImages.length > 1 && <div className="product-image-thumbnails" aria-label="Product images">
      {visibleImages.map((image) => <button key={image.id} type="button" className={selected === image.image_url ? "is-selected" : ""}
        onClick={() => { setSelected(image.image_url); setFailed(false); }} aria-label={`View ${productName} image`} aria-pressed={selected === image.image_url}>
        <img src={image.image_url} alt="" />
      </button>)}
    </div>}
  </div>;
}
