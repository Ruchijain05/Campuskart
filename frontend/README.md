# CampusKart frontend

React, TypeScript, and Vite frontend for the CampusKart FastAPI service.

## Run locally

Create `.env.local` from `.env.example`, then set the Supabase project URL and
the publishable (or legacy anon) key. Never put the Supabase service-role key
in a `VITE_` variable or in this frontend project.

```powershell
Copy-Item .env.example .env.local
npm.cmd install
npm.cmd run dev
```

The dev server runs at `http://localhost:5173`. Configure that URL in the
Supabase Auth redirect allow list. Set `VITE_API_BASE_URL` when the API is
hosted somewhere other than `http://localhost:8000`.

## Authentication

Supabase Auth handles email/password registration, email confirmation, password
recovery, Google OAuth, and browser sessions. The frontend uses PKCE and sends
the current Supabase access token to the FastAPI service; the API verifies it
against the Supabase project's signing-key endpoint and resolves the CampusKart
role from its own `users` table.

## API-backed scope

The app uses the current `/api/v1` endpoints for product/category browsing,
authentication, seller applications, product listings, admin moderation, cart,
COD checkout, buyer wishlists, product reviews, recently viewed products, and
Buy Again. Buyers can place orders, view order history and tracking updates,
save products for later, and create or manage their own 1–5 star reviews.
Admins can update order status. Online payment and shipping-provider
integration are not included.

The storefront includes Male, Female, and Special Gifts sections. Sellers and
admins can assign a product to multiple sections in Seller Studio; section
membership is independent of product categories.

Buyers can submit requests for products not listed on the site, optionally
attach a photo, and review admin responses from Request anything. Admins can
review and respond to all requests in the admin page; responses appear in the
buyer's request history and in-app notifications.
