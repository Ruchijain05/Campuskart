import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useAuth } from "./auth";

const MAX_COMPARE_PRODUCTS = 3;

interface ComparisonContextValue {
  productIds: number[];
  message: string;
  toggleProduct: (productId: number) => void;
  removeProduct: (productId: number) => void;
  replaceProducts: (productIds: number[]) => void;
  clearProducts: () => void;
}

const ComparisonContext = createContext<ComparisonContextValue | null>(null);

export function ComparisonProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [productIds, setProductIds] = useState<number[]>([]);
  const [message, setMessage] = useState("");

  useEffect(() => {
    setProductIds([]);
    setMessage("");
  }, [user?.id]);

  const toggleProduct = useCallback((productId: number) => {
    setMessage("");
    if (productIds.includes(productId)) {
      setProductIds(productIds.filter((id) => id !== productId));
      return;
    }
    if (productIds.length >= MAX_COMPARE_PRODUCTS) {
      setMessage("You can compare up to 3 products. Remove one to add another.");
      return;
    }
    setProductIds([...productIds, productId]);
  }, [productIds]);
  const removeProduct = useCallback((productId: number) => {
    setMessage("");
    setProductIds((current) => current.filter((id) => id !== productId));
  }, []);
  const replaceProducts = useCallback((nextIds: number[]) => {
    setMessage("");
    setProductIds([...new Set(nextIds)].slice(0, MAX_COMPARE_PRODUCTS));
  }, []);
  const clearProducts = useCallback(() => {
    setMessage("");
    setProductIds([]);
  }, []);
  const value = useMemo(
    () => ({ productIds, message, toggleProduct, removeProduct, replaceProducts, clearProducts }),
    [productIds, message, toggleProduct, removeProduct, replaceProducts, clearProducts],
  );
  return <ComparisonContext.Provider value={value}>{children}</ComparisonContext.Provider>;
}

export function useComparison() {
  const context = useContext(ComparisonContext);
  if (!context) throw new Error("useComparison must be used within ComparisonProvider");
  return context;
}
