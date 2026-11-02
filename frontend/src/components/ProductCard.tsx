import { useState } from "react";
import { ArrowUpRight, PackageOpen } from "lucide-react";
import { Link } from "react-router-dom";
import type { Product } from "../lib/types";
import { AddToCartButton } from "./AddToCartButton";
import { WishlistButton } from "./WishlistButton";
import { CompareControl } from "./CompareControl";

const money = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 });
export function formatPrice(price: string | number) { return money.format(Number(price)); }

export function ProductCard({ product, categoryName }: { product: Product; categoryName?: string }) {
  const [imageFailed, setImageFailed] = useState(false);
  return (
    <article className="product-card">
      <Link to={`/products/${product.id}`} className="product-image-wrap">
        {product.image_url && !imageFailed ? <img src={product.image_url} alt={product.name} loading="lazy" onError={() => setImageFailed(true)} /> : <div className="image-placeholder"><PackageOpen size={36} /><span>Campus find</span></div>}
        <span className="product-arrow"><ArrowUpRight size={17} /></span>
      </Link>
      <div className="product-card-body">
        {categoryName && <span className="product-category">{categoryName}</span>}
        <Link to={`/products/${product.id}`} className="product-name">{product.name}</Link>
        <p className="product-description">{product.description || "A great find for your campus routine."}</p>
        <div className="product-card-bottom">
          <strong>{product.offer_active && product.offer_price != null ? <><span className="offer-price">{formatPrice(product.offer_price)}</span> <del>{formatPrice(product.price)}</del></> : formatPrice(product.price)}</strong>
          {product.offer_active && <span className="offer-badge">{Number(product.discount_percentage ?? 0)}% off</span>}
          <span className={product.stock > 0 ? "stock-available" : "stock-unavailable"}>{product.stock > 0 ? "Available" : "Out of stock"}</span>
        </div>
        <AddToCartButton productId={product.id} disabled={product.stock < 1} compact />
        <WishlistButton productId={product.id} compact />
        <CompareControl productId={product.id} compact />
      </div>
    </article>
  );
}
