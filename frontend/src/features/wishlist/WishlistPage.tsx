import { Heart, PackageOpen } from "lucide-react";
import { Link } from "react-router-dom";
import { LoadingState, Notice, PageTitle } from "../../components/SiteLayout";
import { ProductCard, formatPrice } from "../../components/ProductCard";
import { WishlistButton } from "../../components/WishlistButton";
import { useWishlist } from "../../lib/wishlist";

export function WishlistPage() {
  const { products, loading, error } = useWishlist();
  const availableProducts = products.filter((product) => product.is_active);
  const unavailableProducts = products.filter((product) => !product.is_active);
  return (
    <section className="content-narrow wishlist-page">
      <PageTitle eyebrow="YOUR CAMPUSKART" title="My wishlist" description="Save campus finds you want to come back to." />
      {error && <Notice tone="error">{error}</Notice>}
      {loading ? <LoadingState label="Loading your wishlist..." /> : products.length ? <>
        {availableProducts.length > 0 && <div className="product-grid wishlist-grid">{availableProducts.map((product) => <ProductCard key={product.id} product={product} />)}</div>}
        {unavailableProducts.length > 0 && <section className="wishlist-unavailable"><h2>Currently unavailable</h2>{unavailableProducts.map((product) => <article className="wishlist-unavailable-item" key={product.id}>
          {product.image_url ? <img src={product.image_url} alt="" /> : <div className="image-placeholder"><PackageOpen size={24} /></div>}
          <div><b>{product.name}</b><span>{formatPrice(product.price)} · Listing unavailable</span></div><WishlistButton productId={product.id} compact />
        </article>)}</section>}
      </> : <div className="cart-empty wishlist-empty"><Heart size={38} /><h2>Your wishlist is empty</h2><p>Save a product to keep it here for later.</p><Link className="button button-dark" to="/">Explore products</Link></div>}
    </section>
  );
}
