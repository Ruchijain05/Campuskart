import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, Star, X } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { LoadingState, Notice, PageTitle } from "../../components/SiteLayout";
import { formatPrice } from "../../components/ProductCard";
import { api } from "../../lib/api";
import { useComparison } from "../../lib/comparison";
import type { Product, ProductReviewSummary } from "../../lib/types";

interface ComparedProduct {
  id: number;
  product: Product | null;
  reviews: ProductReviewSummary | null;
  error: string;
}

function parseProductIds(value: string | null): number[] {
  if (!value) return [];
  return [...new Set(value.split(",").map(Number).filter((id) => Number.isInteger(id) && id > 0))].slice(0, 3);
}

export function ComparePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { productIds, replaceProducts } = useComparison();
  const queryIds = useMemo(() => parseProductIds(searchParams.get("products")), [searchParams]);
  const ids = queryIds.length ? queryIds : productIds;
  const [items, setItems] = useState<ComparedProduct[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (queryIds.length) replaceProducts(queryIds);
  }, [queryIds, replaceProducts]);

  useEffect(() => {
    let active = true;
    if (!ids.length) {
      setItems([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    Promise.all(ids.map(async (id): Promise<ComparedProduct> => {
      const [productResult, reviewsResult] = await Promise.allSettled([
        api.getProduct(id),
        api.getProductReviews(id),
      ]);
      if (productResult.status === "rejected") {
        const reason: unknown = productResult.reason;
        return { id, product: null, reviews: null, error: reason instanceof Error ? reason.message : "This product is unavailable." };
      }
      return {
        id,
        product: productResult.value,
        reviews: reviewsResult.status === "fulfilled" ? reviewsResult.value : null,
        error: "",
      };
    })).then((result) => { if (active) setItems(result); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [ids.join(",")]);

  function removeProduct(productId: number) {
    const nextIds = ids.filter((id) => id !== productId);
    replaceProducts(nextIds);
    setSearchParams(nextIds.length ? { products: nextIds.join(",") } : {}, { replace: true });
  }

  return <section className="content-narrow compare-page">
    <PageTitle eyebrow="CAMPUSKART COMPARISON" title="Compare your picks" description="Review prices, details, ratings, and availability side by side." />
    {loading ? <LoadingState label="Loading product comparisons..." /> : ids.length < 2 ? <div className="compare-empty"><ArrowLeft size={24} /><h2>Select at least two products</h2><p>Choose up to three products from the catalog, then compare them here.</p><Link className="button button-dark" to="/">Back to products</Link></div> : <>
      {ids.length > 3 && <Notice tone="error">You can compare no more than three products at a time.</Notice>}
      <div className="compare-table-wrap"><table className="compare-table">
        <thead><tr><th scope="col">Product details</th>{items.map(({ id, product, error }) => <th scope="col" key={id}>
          <div className="compare-product-heading">
            {product?.image_url ? <img src={product.image_url} alt="" /> : <div className="compare-product-placeholder">{error ? "?" : "CK"}</div>}
            <div><b>{product?.name ?? `Product #${id}`}</b></div>
            <button type="button" aria-label={`Remove ${product?.name ?? `product ${id}`} from comparison`} onClick={() => removeProduct(id)}><X size={15} /></button>
          </div>
        </th>)}</tr></thead>
        <tbody>
          <tr><th scope="row">Price</th>{items.map(({ id, product, error }) => <td key={id}>{product ? <strong className="compare-price">{formatPrice(product.price)}</strong> : <span className="compare-unavailable">{error || "Unavailable"}</span>}</td>)}</tr>
          <tr><th scope="row">Description</th>{items.map(({ id, product }) => <td key={id}>{product?.description || (product ? "No description provided." : <span className="compare-unavailable">Product is unavailable.</span>)}</td>)}</tr>
          <tr><th scope="row">Rating</th>{items.map(({ id, product, reviews }) => <td key={id}>{!product ? <span className="compare-unavailable">Unavailable</span> : reviews ? reviews.review_count ? <span className="compare-rating"><Star size={15} fill="currentColor" /><b>{Number(reviews.average_rating).toFixed(1)} / 5</b><small>{reviews.review_count} {reviews.review_count === 1 ? "review" : "reviews"}</small></span> : <span className="compare-no-rating">No ratings yet</span> : <span className="compare-no-rating">Ratings unavailable</span>}</td>)}</tr>
          <tr><th scope="row">Availability</th>{items.map(({ id, product }) => <td key={id}>{!product ? <span className="compare-unavailable">No longer available</span> : product.stock > 0 ? <span className="compare-stock">In stock · {product.stock} available</span> : <span className="compare-unavailable">Out of stock</span>}</td>)}</tr>
        </tbody>
      </table></div>
    </>}
  </section>;
}
