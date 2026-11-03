# CampusKart frontend

React, TypeScript, and Vite frontend for the CampusKart FastAPI service.

## Run locally

From this directory:

```powershell
npm.cmd install
npm.cmd run dev
```

The dev server runs at `http://localhost:5173`, which matches the backend's
default allowed frontend origin. Set `VITE_API_BASE_URL` when the API is hosted
somewhere other than `http://localhost:8000`.

## API-backed scope

The app uses the current `/api/v1` endpoints for product/category browsing,
authentication, seller applications, product listings, admin moderation, cart,
COD checkout, buyer wishlists, product reviews, recently viewed products, and Buy Again. Buyers can place orders,
view order history and tracking updates, save products for later, and create or
manage their own 1–5 star reviews. Admins can update order status. Online
payment and shipping-provider integration are not included.

The storefront includes Male, Female, and Special Gifts sections. Sellers and
admins can assign a product to multiple sections in Seller Studio; section
membership is independent of product categories.

Buyers can submit requests for products not listed on the site, optionally
attach a photo, and review admin responses from Request anything. Admins can
review and respond to all requests in the admin page; responses appear in the
buyer's request history and in-app notifications.

Account registration includes email verification. Users can request a
time-limited password-reset link from the sign-in page; reset and verification
links are delivered through the backend SMTP configuration.

Access tokens are kept in React memory. A 30-day HttpOnly refresh cookie lets
the frontend restore the signed-in session after a page refresh or browser
restart without storing bearer tokens in browser-accessible storage. Logging
out revokes the session; expired sessions require signing in again.
