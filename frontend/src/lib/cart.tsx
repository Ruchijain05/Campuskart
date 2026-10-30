import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "./api";
import { useAuth } from "./auth";
import type { Cart } from "./types";

interface CartContextValue {
  cart: Cart;
  itemCount: number;
  loading: boolean;
  error: string;
  addItem: (productId: number, quantity?: number) => Promise<void>;
  updateItem: (productId: number, quantity: number) => Promise<void>;
  removeItem: (productId: number) => Promise<void>;
}

const emptyCart: Cart = { items: [], total: "0.00" };
const CartContext = createContext<CartContextValue | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const { token } = useAuth();
  const [cart, setCart] = useState<Cart>(emptyCart);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    if (!token) {
      setCart(emptyCart);
      setError("");
      setLoading(false);
      return () => { active = false; };
    }
    setLoading(true);
    api.getCart(token)
      .then((nextCart) => { if (active) { setCart(nextCart); setError(""); } })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Could not load your cart."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token]);

  const requireToken = useCallback(() => {
    if (!token) throw new Error("Sign in to add products to your cart.");
    return token;
  }, [token]);
  const addItem = useCallback(async (productId: number, quantity = 1) => {
    setError("");
    setCart(await api.addCartItem(productId, quantity, requireToken()));
  }, [requireToken]);
  const updateItem = useCallback(async (productId: number, quantity: number) => {
    setError("");
    setCart(await api.updateCartItem(productId, quantity, requireToken()));
  }, [requireToken]);
  const removeItem = useCallback(async (productId: number) => {
    setError("");
    setCart(await api.removeCartItem(productId, requireToken()));
  }, [requireToken]);
  const itemCount = cart.items.reduce((sum, item) => sum + item.quantity, 0);
  const value = useMemo(() => ({ cart, itemCount, loading, error, addItem, updateItem, removeItem }), [cart, itemCount, loading, error, addItem, updateItem, removeItem]);
  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const context = useContext(CartContext);
  if (!context) throw new Error("useCart must be used within CartProvider");
  return context;
}