import { useEffect, useMemo, useState } from "react";
import { ArrowDownRight, ArrowRight, BookOpen, ChevronDown, ChevronRight, Search, Sparkles } from "lucide-react";
import { Link, useSearchParams, useParams } from "react-router-dom";
import { Notice, LoadingState } from "../../components/SiteLayout";
import { ProductCard, formatPrice } from "../../components/ProductCard";
import { AddToCartButton } from "../../components/AddToCartButton";
import { api } from "../../lib/api";
import { buildCategoryTree } from "../../lib/categoryTree";
import type { Category, CategoryTree, Product } from "../../lib/types";

function CategoryBranch({
  category,
  depth,
  selectedCategoryId,
  onSelect,
  expandedCategoryIds,
  onToggle,
}: {
  category: CategoryTree;
  depth: number;
  selectedCategoryId: number | null;
  onSelect: (id: number) => void;
  expandedCategoryIds: Set<number>;
  onToggle: (id: number) => void;
}) {
  const isExpanded = expandedCategoryIds.has(category.id);
  const isSelected = selectedCategoryId === category.id;
  return (
    <div className={`shop-category-branch shop-category-depth-${Math.min(depth, 2)}`}>
      <div className="shop-category-row">
        <button
          type="button"
          className={isSelected ? "shop-category-button selected" : "shop-category-button"}
          onClick={() => onSelect(category.id)}
          aria-pressed={isSelected}
        >
          <span>{category.name}</span>
        </button>
        {category.children.length > 0 && (
          <button
            type="button"
            className="shop-category-toggle"
            onClick={() => onToggle(category.id)}
            aria-label={`${isExpanded ? "Collapse" : "Expand"} ${category.name}`}
            aria-expanded={isExpanded}
          >
            {isExpanded ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
          </button>
        )}
      </div>
      {isExpanded && category.children.length > 0 && (
        <div className="shop-category-children">
          {category.children.map((child) => (
            <CategoryBranch
              key={child.id}
              category={child}
              depth={depth + 1}
              selectedCategoryId={selectedCategoryId}
              onSelect={onSelect}
              expandedCategoryIds={expandedCategoryIds}
              onToggle={onToggle}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function HomePage() {
  const [searchParams] = useSearchParams();
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<CategoryTree[]>([]);
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | null>(null);
  const [expandedCategoryIds, setExpandedCategoryIds] = useState<Set<number>>(() => new Set());
  const [categoriesPanelOpen, setCategoriesPanelOpen] = useState(false);
  const [loadingProducts, setLoadingProducts] = useState(true);
  const [productsError, setProductsError] = useState("");
  const [categoriesError, setCategoriesError] = useState("");
  const query = (searchParams.get("q") ?? "").trim().toLowerCase();

  useEffect(() => {
    let active = true;
    setLoadingProducts(true);
    api.listAllProducts(selectedCategoryId ?? undefined)
      .then((items) => {
        if (!active) return;
        setProducts(items);
        setProductsError("");
      })
      .catch((reason: unknown) => {
        if (active) setProductsError(reason instanceof Error ? reason.message : "Could not load products.");
      })
      .finally(() => { if (active) setLoadingProducts(false); });
    return () => { active = false; };
  }, [selectedCategoryId]);

  useEffect(() => {
    let active = true;
    api.listCategoryTree()
      .then((groups) => {
        if (!active) return;
        setCategories(groups);
        setCategoriesError("");
      })
      .catch(async (treeReason: unknown) => {
        try {
          const flatCategories = await api.listCategories();
          if (!active) return;
          setCategories(buildCategoryTree(flatCategories.map((category: Category) => ({
            ...category,
            parent_id: category.parent_id ?? null,
          }))));
          setCategoriesError("Nested category browsing is unavailable; showing available categories.");
        } catch {
          if (!active) return;
          setCategoriesError(
            treeReason instanceof Error
              ? `Could not load categories: ${treeReason.message}`
              : "Could not load categories.",
          );
        }
      });
    return () => { active = false; };
  }, []);

  const shownProducts = useMemo(
    () => products.filter((product) => {
      const matchesSearch = !query || `${product.name} ${product.description ?? ""}`.toLowerCase().includes(query);
      return matchesSearch;
    }),
    [products, query],
  );
  const categoryPaths = useMemo(() => {
    const paths = new Map<number, string>();
    const visit = (nodes: CategoryTree[], parents: string[]) => {
      for (const node of nodes) {
        const path = [...parents, node.name];
        paths.set(node.id, path.join(" / "));
        visit(node.children, path);
      }
    };
    visit(categories, []);
    return paths;
  }, [categories]);
  const selectedCategoryPath = selectedCategoryId === null
    ? ""
    : categories.length
      ? categoryPaths.get(selectedCategoryId) ?? ""
      : "";

  function selectCategory(categoryId: number) {
    setSelectedCategoryId((current) => current === categoryId ? null : categoryId);
  }

  function toggleCategory(categoryId: number) {
    setExpandedCategoryIds((current) => {
      const next = new Set(current);
      if (next.has(categoryId)) next.delete(categoryId);
      else next.add(categoryId);
      return next;
    });
  }

  return (
    <div className="home-page">
      <section className="hero">
        <div className="hero-copy">
          <div className="hero-kicker"><span className="pulse-dot" /> YOUR CAMPUS, YOUR MARKETPLACE</div>
          <h1>Big campus energy.<br /><span>Better everyday finds.</span></h1>
          <p>Discover the stuff that makes student life easier — all in one place, made for your campus rhythm.</p>
          <a className="button button-dark" href="#catalog">Explore the finds <ArrowRight size={17} /></a>
          <div className="hero-social-proof"><span className="avatar-stack"><i>✦</i><i>↗</i><i>+</i></span><span>Find something that fits your day.</span></div>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="art-glow" />
          <div className="art-card art-card-main"><div className="art-product-box"><BookOpen size={74} strokeWidth={1.2} /></div><div><span className="art-mini-label">CAMPUS ESSENTIAL</span><b>Ideas start here.</b></div></div>
          <div className="art-sticker sticker-yellow"><Sparkles size={16} /> GOOD FINDS</div>
          <div className="art-sticker sticker-lilac">MADE FOR YOU <ArrowDownRight size={16} /></div>
          <div className="art-orbit orbit-one" /><div className="art-orbit orbit-two" />
          <div className="art-student">✦</div>
        </div>
        <div className="hero-bottom-note"><span>01</span> Find it. Love it. CampusKart it.</div>
      </section>

      <section className="value-strip" aria-label="Marketplace highlights">
        <div><span className="value-icon value-peach"><Search size={18} /></span><span><b>Find your thing</b><small>Browse campus-ready picks</small></span></div>
        <div><span className="value-icon value-lime"><BookOpen size={18} /></span><span><b>Made for student life</b><small>Useful finds, all in one spot</small></span></div>
        <div><span className="value-icon value-blue"><Sparkles size={18} /></span><span><b>Student-to-student</b><small>Community starts here</small></span></div>
      </section>

      <section className="featured-categories" aria-labelledby="featured-categories-heading">
        <div className="featured-categories-heading">
          <span className="eyebrow">BROWSE THE CAMPUS EDIT</span>
          <h2 id="featured-categories-heading">Shop by category</h2>
          <p>Find useful things for study, daily life, and your room.</p>
        </div>
        <div className="featured-category-grid">
          {[
            { name: "Stationery", image: "/category-images/stationery.png", matchNames: ["stationery"] },
            { name: "Electronics", image: "/category-images/electronics.png", matchNames: ["electronics"] },
            { name: "Grocery", image: "/category-images/grocery.png", matchNames: ["grocery", "groceries"] },
            { name: "Personal Care", image: "/category-images/personal-care.png", matchNames: ["personal care"] },
            { name: "Hostel Essentials", image: "/category-images/hostel-essentials.png", matchNames: ["hostel essentials"] },
          ].map(({ name, image, matchNames }) => {
            const category = categories.find(
              (item) => item.parent_id === null && matchNames.includes(item.name.trim().toLowerCase()),
            );
            return (
              <button
                key={name}
                type="button"
                className={`featured-category-card${selectedCategoryId === category?.id ? " is-selected" : ""}`}
                disabled={!category}
                aria-pressed={selectedCategoryId === category?.id}
                onClick={() => category && setSelectedCategoryId((current) => current === category.id ? null : category.id)}
              >
                <img src={image} alt="" loading="lazy" />
                <span>{name}<ArrowRight size={16} /></span>
              </button>
            );
          })}
        </div>
      </section>

      <div className="catalog-layout" id="catalog">
        <aside className={`shop-categories-section${categoriesPanelOpen ? " is-open" : ""}`} aria-labelledby="shop-categories-heading">
          <button
            type="button"
            className="shop-category-mobile-toggle"
            onClick={() => setCategoriesPanelOpen((open) => !open)}
            aria-expanded={categoriesPanelOpen}
            aria-controls="shop-category-sidebar"
          >
            <span>Shop by Categories</span>
            {categoriesPanelOpen ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
          </button>
          <div className="shop-category-sidebar" id="shop-category-sidebar">
            <div className="shop-category-sidebar-heading">
              <span className="eyebrow">BROWSE THE STORE</span>
              <h2 id="shop-categories-heading">Shop by Categories</h2>
            </div>
            <button
              type="button"
              className={selectedCategoryId === null ? "shop-category-button shop-category-all selected" : "shop-category-button shop-category-all"}
              onClick={() => setSelectedCategoryId(null)}
              aria-pressed={selectedCategoryId === null}
            >
              All products
            </button>
            {categories.length ? (
              <nav className="shop-category-tree" aria-label="Product categories">
                {categories.map((category) => (
                  <CategoryBranch
                    key={category.id}
                    category={category}
                    depth={0}
                    selectedCategoryId={selectedCategoryId}
                    onSelect={selectCategory}
                    expandedCategoryIds={expandedCategoryIds}
                    onToggle={toggleCategory}
                  />
                ))}
              </nav>
            ) : !loadingProducts && !categoriesError ? (
              <div className="empty-category-state">Categories are being organized. Check back soon.</div>
            ) : null}
            {categoriesError && <Notice>{categoriesError}</Notice>}
          </div>
        </aside>

      <section className="catalog-section">
        <div className="section-heading">
          <div><span className="eyebrow">{selectedCategoryPath || "THE CAMPUS EDIT"}</span><h2>{query ? `Results for “${searchParams.get("q")}”` : selectedCategoryPath ? `Finds in ${selectedCategoryPath}` : "A little something for your everyday"}</h2><p>Useful picks for classes, late nights, and everything between.</p></div>
          <span className="product-count">{shownProducts.length} {shownProducts.length === 1 ? "find" : "finds"}</span>
        </div>
        {selectedCategoryId !== null && <button className="clear-category-filter" onClick={() => setSelectedCategoryId(null)}>Show all categories</button>}
        {productsError && <Notice tone="error">{productsError}</Notice>}
        {loadingProducts ? <LoadingState label="Finding your next favorite..." /> : shownProducts.length ? (
          <div className="product-grid">
            {shownProducts.map((product) => <ProductCard key={product.id} product={product} categoryName={product.category_id === null ? undefined : categoryPaths.get(product.category_id)} />)}
          </div>
        ) : (
          <div className="empty-state"><span className="empty-emoji">✦</span><h3>No finds just yet</h3><p>{query ? "Try another search or clear your filters." : "Check back soon — new campus finds are on their way."}</p>{query && <Link className="button button-outline" to="/">Clear search</Link>}</div>
        )}
      </section>
      </div>

      <section className="sell-banner">
        <div><span className="eyebrow">HAVE SOMETHING TO SHARE?</span><h2>Your next side hustle<br />could start right here.</h2><p>Turn your great finds into someone else's favorite.</p></div>
        <Link className="button button-dark" to="/sell">Become a seller <ArrowRight size={17} /></Link>
        <div className="sell-banner-spark">✳</div>
      </section>
    </div>
  );
}

export function ProductPage() {
  const { productId } = useParams();
  const [product, setProduct] = useState<Product | null>(null);
  const [categoryPath, setCategoryPath] = useState("");
  const [error, setError] = useState("");
  const [imageFailed, setImageFailed] = useState(false);

  useEffect(() => {
    setImageFailed(false);
    setProduct(null);
    setCategoryPath("");
    setError("");
    const id = Number(productId);
    if (!Number.isInteger(id) || id < 1) {
      setError("That product link is not valid.");
      return;
    }
    let active = true;
    api.getProduct(id)
      .then((item) => {
        if (active) setProduct(item);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Could not load this product.");
      });
    return () => { active = false; };
  }, [productId]);

  useEffect(() => {
    if (product?.category_id == null) return;
    let active = true;
    api.listCategoryTree()
      .then((categories) => {
        if (!active) return;
        const findCategory = (nodes: CategoryTree[], parents: string[] = []): string | null => {
          for (const node of nodes) {
            const path = [...parents, node.name];
            if (node.id === product?.category_id) return path.join(" / ");
            const child = findCategory(node.children, path);
            if (child) return child;
          }
          return null;
        };
        setCategoryPath(findCategory(categories) ?? "");
      })
      .catch(async () => {
        try {
          const categories = await api.listCategories();
          if (!active) return;
          const category = categories.find((item) => item.id === product?.category_id);
          setCategoryPath(category?.name ?? "");
        } catch {
          if (active) setCategoryPath("");
        }
      });
    return () => { active = false; };
  }, [product?.category_id]);

  if (error) return <div className="content-narrow"><Notice tone="error">{error}</Notice><Link to="/" className="text-link">Back to the catalog</Link></div>;
  if (!product) return <LoadingState label="Loading product..." />;

  return (
    <section className="product-detail content-narrow">
      <div className="breadcrumb"><Link to="/">Discover</Link><span>/</span><span>{product.name}</span></div>
      <div className="detail-grid">
        <div className="detail-image">
          {product.image_url && !imageFailed ? <img src={product.image_url} alt={product.name} onError={() => setImageFailed(true)} /> : <div className="image-placeholder detail-placeholder"><BookOpen size={64} /><span>Campus find</span></div>}
        </div>
        <div className="detail-copy">
          <span className="eyebrow">{categoryPath || "CAMPUS FIND"}</span>
          <h1>{product.name}</h1>
          <div className="detail-price">{formatPrice(product.price)}</div>
          <div className="detail-rule" />
          <p className="detail-description">{product.description || "A great find for your campus routine."}</p>
          <div className="detail-stock"><span className={product.stock > 0 ? "stock-indicator" : "stock-indicator unavailable"} />{product.stock > 0 ? `${product.stock} available` : "Currently unavailable"}</div>
          <div className="detail-info-card"><span>✦</span><p>Found something you love? Reach out to the seller through your campus community.</p></div>
          <AddToCartButton productId={product.id} disabled={product.stock < 1} />
          <Link className="button button-outline detail-back" to="/">Keep exploring <ArrowRight size={16} /></Link>
        </div>
      </div>
    </section>
  );
}
