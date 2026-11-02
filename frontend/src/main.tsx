import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./app/App";
import { AuthProvider } from "./lib/auth";
import { CartProvider } from "./lib/cart";
import { WishlistProvider } from "./lib/wishlist";
import { ComparisonProvider } from "./lib/comparison";
import { NotificationsProvider } from "./lib/notifications";
import "./styles/global.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AuthProvider>
      <ComparisonProvider>
        <NotificationsProvider>
          <CartProvider>
            <WishlistProvider>
              <App />
            </WishlistProvider>
          </CartProvider>
        </NotificationsProvider>
      </ComparisonProvider>
    </AuthProvider>
  </React.StrictMode>,
);
