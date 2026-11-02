import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, PackageOpen, ShoppingBag } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { LoadingState, Notice, PageTitle } from "../../components/SiteLayout";
import { formatPrice } from "../../components/ProductCard";
import { api } from "../../lib/api";
import type { ProductBundle } from "../../lib/types";

function BundlePrice({ bundle }: { bundle: ProductBundle }) {
  return <div className="bundle-price-row"><strong>{formatPrice(bundle.payable_price)}</strong><del>{formatPrice(bundle.original_price)}</del><span className="offer-badge">{Number(bundle.discount_percentage)}% off</span></div>;
}

function BundleCard({ bundle }: { bundle: ProductBundle }) {
  const photos = bundle.items.slice(0, 3).filter((item) => item.image_url);
  return <article className="bundle-card">
    <Link className="bundle-card-images" to={`/bundles/${bundle.id}`} aria-label={`View ${bundle.name}`}>
      {photos.length ? photos.map((item) => <img src={item.image_url!} alt="" key={item.product_id} loading="lazy" />) : <div className="image-placeholder"><PackageOpen size={32} /><span>Bundle deal</span></div>}
    </Link>
    <div className="bundle-card-body"><span className="eyebrow">BUNDLE DEAL · {bundle.items.length} PRODUCTS</span><Link to={`/bundles/${bundle.id}`}><h2>{bundle.name}</h2></Link><p>{bundle.description || bundle.items.map((item) => item.product_name).join(" + ")}</p><BundlePrice bundle={bundle} /><Link className="button button-dark" to={`/bundles/${bundle.id}`}>View bundle <ArrowRight size={15} /></Link></div>
  </article>;
}

export function BundlesPage() {
  const [bundles, setBundles] = useState<ProductBundle[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    api.listBundles().then((items) => { if (active) setBundles(items); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Could not load bundles."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  return <section className="content-narrow bundles-page"><PageTitle eyebrow="CAMPUSKART DEALS" title="Product bundles" description="Useful combinations, together at one special price." />{error && <Notice tone="error">{error}</Notice>}{loading ? <LoadingState label="Loading bundles..." /> : bundles.length ? <div className="bundle-grid">{bundles.map((bundle) => <BundleCard key={bundle.id} bundle={bundle} />)}</div> : <div className="cart-empty"><PackageOpen size={38} /><h2>No bundles available right now</h2><p>Check back soon for bundle deals.</p><Link to="/" className="button button-dark">Explore products</Link></div>}</section>;
}

export function BundleDetailPage() {
  const { bundleId } = useParams();
  const [bundle, setBundle] = useState<ProductBundle | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    if (!bundleId) return;
    api.getBundle(Number(bundleId)).then((item) => { if (active) setBundle(item); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Could not load this bundle."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [bundleId]);
  if (loading) return <LoadingState label="Loading bundle..." />;
  if (error || !bundle) return <section className="content-narrow"><Notice tone="error">{error || "Bundle not found."}</Notice><Link to="/bundles" className="text-link">Back to bundles</Link></section>;
  return <section className="content-narrow bundle-detail-page"><Link className="bundle-back-link" to="/bundles"><ArrowLeft size={15} /> All bundles</Link><PageTitle eyebrow="BUNDLE DEAL" title={bundle.name} description={bundle.description || "Get these products together at a special price."} />
    <div className="bundle-detail-layout"><div className="bundle-detail-products">{bundle.items.map((item) => <article className="bundle-detail-product" key={item.product_id}>{item.image_url ? <img src={item.image_url} alt={item.product_name} /> : <div className="image-placeholder"><PackageOpen size={25} /></div>}<div><b>{item.product_name}</b><small>{item.quantity} included · {formatPrice(item.unit_price)} each</small></div></article>)}</div>
      <aside className="checkout-card bundle-purchase-summary"><span className="eyebrow">BUNDLE SUMMARY</span><div className="checkout-summary-line"><span>Regular combined price</span><b><del>{formatPrice(bundle.original_price)}</del></b></div><div className="checkout-summary-line checkout-discount-line"><span>Bundle savings</span><b>−{formatPrice(bundle.discount_amount)}</b></div><div className="checkout-summary-total"><span>Special bundle price</span><strong>{formatPrice(bundle.payable_price)}</strong></div>{bundle.available ? <Link className="button button-dark" to={`/bundles/${bundle.id}/checkout`}><ShoppingBag size={16} /> Buy bundle</Link> : <button className="button button-dark" disabled>Currently unavailable</button>}<small>{bundle.max_bundles} bundle{bundle.max_bundles === 1 ? "" : "s"} available</small></aside>
    </div>
  </section>;
}
