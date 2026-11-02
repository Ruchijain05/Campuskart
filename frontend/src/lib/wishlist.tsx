import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "./api";
import { useAuth } from "./auth";
import type { Product } from "./types";

interface WishlistContextValue {
  products: Product[];
  loading: boolean;
  error: string;
  contains: (productId: number) => boolean;
  add: (productId: number) => Promise<void>;
  remove: (productId: number) => Promise<void>;
}

const WishlistContext = createContext<WishlistContextValue | null>(null);

export function WishlistProvider({ children }: { children: ReactNode }) {
  const { token, user } = useAuth();
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    if (!token || user?.role !== "buyer") {
      setProducts([]); setError(""); setLoading(false);
      return () => { active = false; };
    }
    setLoading(true);
    api.getWishlist(token)
      .then((items) => { if (active) { setProducts(items); setError(""); } })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Could not load your wishlist."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token, user?.role]);

  const requireBuyerToken = useCallback(() => {
    if (!token || user?.role !== "buyer") throw new Error("Sign in as a buyer to use your wishlist.");
    return token;
  }, [token, user?.role]);
  const add = useCallback(async (productId: number) => {
    setError(""); setProducts(await api.addWishlistItem(productId, requireBuyerToken()));
  }, [requireBuyerToken]);
  const remove = useCallback(async (productId: number) => {
    setError(""); setProducts(await api.removeWishlistItem(productId, requireBuyerToken()));
  }, [requireBuyerToken]);
  const productIds = useMemo(() => new Set(products.map((product) => product.id)), [products]);
  const contains = useCallback((productId: number) => productIds.has(productId), [productIds]);
  const value = useMemo(() => ({ products, loading, error, contains, add, remove }), [products, loading, error, contains, add, remove]);
  return <WishlistContext.Provider value={value}>{children}</WishlistContext.Provider>;
}

export function useWishlist() {
  const context = useContext(WishlistContext);
  if (!context) throw new Error("useWishlist must be used within WishlistProvider");
  return context;
}
