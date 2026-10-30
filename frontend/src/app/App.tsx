import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { SiteLayout } from "../components/SiteLayout";
import { ProtectedRoute } from "../components/ProtectedRoute";
import { AccountPage } from "../features/account/pages";
import { AdminPage } from "../features/admin/pages";
import { LoginPage, RegisterPage } from "../features/auth/pages";
import { CartPage } from "../features/cart/CartPage";
import { HomePage, ProductPage } from "../features/catalog/pages";
import { SellerApplicationPage, SellerProductsPage } from "../features/seller/pages";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<SiteLayout />}>
          <Route index element={<HomePage />} />
          <Route path="products/:productId" element={<ProductPage />} />
          <Route path="login" element={<LoginPage />} />
          <Route path="register" element={<RegisterPage />} />
          <Route path="sell" element={<SellerApplicationPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="account" element={<AccountPage />} />
            <Route path="cart" element={<CartPage />} />
          </Route>
          <Route element={<ProtectedRoute roles={["seller", "admin"]} />}>
            <Route path="seller/products" element={<SellerProductsPage />} />
          </Route>
          <Route element={<ProtectedRoute roles={["admin"]} />}>
            <Route path="admin" element={<AdminPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}