import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { SiteLayout } from "../components/SiteLayout";
import { ProtectedRoute } from "../components/ProtectedRoute";
import { AccountPage } from "../features/account/pages";
import { AddressesPage } from "../features/account/AddressesPage";
import { AdminPage } from "../features/admin/pages";
import { LoginPage, RegisterPage } from "../features/auth/pages";
import { CartPage } from "../features/cart/CartPage";
import { CheckoutPage } from "../features/cart/CheckoutPage";
import { MyOrdersPage, OrderDetailPage } from "../features/orders/pages";
import { BuyAgainPage } from "../features/orders/BuyAgainPage";
import { ComparePage } from "../features/compare/ComparePage";
import { WishlistPage } from "../features/wishlist/WishlistPage";
import { HomePage, ProductPage, ShoppingSectionPage } from "../features/catalog/pages";
import { SellerApplicationPage, SellerProductsPage } from "../features/seller/pages";
import { NotificationsPage } from "../features/notifications/NotificationsPage";
import { SellerOrdersPage } from "../features/seller/SellerOrdersPage";
import { MyQuestionsPage } from "../features/questions/MyQuestionsPage";
import { MyReturnsPage } from "../features/returns/MyReturnsPage";
import { SupportPage } from "../features/support/SupportPage";
import { BundlesPage, BundleDetailPage } from "../features/bundles/pages";
import { BundleCheckoutPage } from "../features/bundles/BundleCheckoutPage";
import { MessagesPage } from "../features/messages/MessagesPage";
import { ProductRequestsPage } from "../features/requests/ProductRequestsPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<SiteLayout />}>
          <Route index element={<HomePage />} />
          <Route path="products/:productId" element={<ProductPage />} />
          <Route path="sections/:sectionSlug" element={<ShoppingSectionPage />} />
          <Route path="bundles" element={<BundlesPage />} />
          <Route path="bundles/:bundleId" element={<BundleDetailPage />} />
          <Route path="login" element={<LoginPage />} />
          <Route path="register" element={<RegisterPage />} />
          <Route path="sell" element={<SellerApplicationPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="account" element={<AccountPage />} />
            <Route path="cart" element={<CartPage />} />
            <Route path="checkout" element={<CheckoutPage />} />
            <Route path="orders" element={<MyOrdersPage />} />
            <Route path="orders/:orderId" element={<OrderDetailPage />} />
          </Route>
          <Route element={<ProtectedRoute roles={["buyer"]} />}>
            <Route path="bundles/:bundleId/checkout" element={<BundleCheckoutPage />} />
            <Route path="addresses" element={<AddressesPage />} />
            <Route path="support" element={<SupportPage />} />
            <Route path="requests" element={<ProductRequestsPage />} />
            <Route path="my-questions" element={<MyQuestionsPage />} />
            <Route path="returns" element={<MyReturnsPage />} />
            <Route path="notifications" element={<NotificationsPage />} />
            <Route path="wishlist" element={<WishlistPage />} />
            <Route path="buy-again" element={<BuyAgainPage />} />
            <Route path="compare" element={<ComparePage />} />
          </Route>
          <Route element={<ProtectedRoute roles={["buyer", "seller"]} />}>
            <Route path="messages" element={<MessagesPage />} />
            <Route path="messages/:conversationId" element={<MessagesPage />} />
          </Route>
          <Route element={<ProtectedRoute roles={["seller", "admin"]} />}>
            <Route path="seller/products" element={<SellerProductsPage />} />
          </Route>
          <Route element={<ProtectedRoute roles={["seller"]} />}>
            <Route path="seller/orders" element={<SellerOrdersPage />} />
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
