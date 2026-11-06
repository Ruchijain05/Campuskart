# CampusKart backend

FastAPI API using SQLAlchemy 2.x, PostgreSQL, Alembic, and Supabase Auth. Product
and category reads remain public; protected API operations use CampusKart roles
stored in PostgreSQL.

## Setup

Create a Supabase project. In its database settings, copy the PostgreSQL
connection string. Use the direct connection or a **session** pooler URL (not a
transaction pooler for Alembic), set the SQLAlchemy driver to `psycopg`, and
require SSL. URL-encode special characters in the database password. Keep this
URL private in `backend/.env`.

From the `backend` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

If `.env` already exists, merge the PostgreSQL/Supabase variables into it;
retain unrelated SMTP, Razorpay, and media settings. Set at least:

- `DATABASE_URL` - Supabase PostgreSQL connection URL
- `SUPABASE_URL` - `https://<project-ref>.supabase.co`
- `SUPABASE_SECRET_KEY` - backend-only key used by the admin bootstrap
- `FRONTEND_ORIGINS` - JSON list of the allowed frontend origins

Never commit `.env`, expose `SUPABASE_SECRET_KEY` to the browser, or put
the database URL in a `VITE_` variable.

### Supabase Auth setup

1. In Supabase **Authentication > URL Configuration**, set the Site URL to the
   frontend origin (locally `http://localhost:5173`). Add redirect URLs for
   `http://localhost:5173/login`, `http://localhost:5173/account`, and
   `http://localhost:5173/reset-password`, plus the equivalent production URLs.
2. In **Authentication > Providers**, enable Email and Google. Keep email
   confirmation enabled. Configure a custom SMTP provider in Supabase Auth for
   production confirmation and password-reset email delivery.
3. For Google, create a Google OAuth client. Add the Supabase callback URL shown
   in the Google provider settings as an authorized redirect URI, then enter
   the Google client ID and secret in Supabase Auth. The application redirect
   URLs from step 1 remain the allowed post-login destinations.
4. In Supabase **Project Settings > Auth > JWT Signing Keys**, use an asymmetric
   `ES256` signing key. The API verifies tokens using the public JWKS endpoint;
   it does not need the JWT signing secret. Set `SUPABASE_JWT_AUDIENCE` to
   `authenticated` (the default).
5. In Supabase **Project Settings > API Keys**, copy the project URL and
   publishable key into `frontend/.env.local` as `VITE_SUPABASE_URL` and
   `VITE_SUPABASE_PUBLISHABLE_KEY`. Put the secret key in the backend `.env` as
   `SUPABASE_SECRET_KEY` for the one-time admin bootstrap. The legacy
   `SUPABASE_SERVICE_ROLE_KEY` setting remains accepted for existing setups.
   Never use a secret/service-role key in the frontend.

The migrations enable Row Level Security on application tables without adding
browser policies. The browser uses Supabase for Auth only; application data is
accessed through the FastAPI service, which connects using the private database
URL.

### Schema and catalog migration

The Supabase `public` schema should not already contain CampusKart tables.
Leave Supabase-managed schemas such as `auth` and `storage` untouched. From
`backend`, run the complete schema migration chain:

```powershell
alembic upgrade head
```

This creates the PostgreSQL schema, adds the Supabase Auth UUID link while
keeping CampusKart's integer user IDs, removes the old password/session tables,
and enables RLS. Do not stamp a fresh project or run these migrations against
the old MySQL database.

By default, no old accounts or user-linked data are migrated. To optionally
bring over **categories and products only**, set `MYSQL_SOURCE_URL` temporarily
to the old MySQL connection in backend `.env`, keep `DATABASE_URL` pointed at
Supabase PostgreSQL, then run:

```powershell
python -m scripts.migrate_catalog
```

The script refuses non-empty target catalog tables, copies IDs and category
relationships, preserves each product's `image_url`, clears seller ownership,
and resets PostgreSQL ID sequences. It does not copy users, orders, galleries,
section assignments, uploaded files, or other user-linked data. Back up both
source and target before running it.

### Admin bootstrap

Create a new admin after the schema is migrated (and after optional catalog
migration):

```powershell
python -m scripts.create_admin
```

The script prompts for the new admin email and password without echoing the
password. It creates a confirmed Supabase Auth user and a corresponding
CampusKart `admin` profile. The password is managed by Supabase; only the
backend service-role key can run this bootstrap, and a second admin is refused
once one exists. Existing MySQL user accounts and their Argon2 hashes are not
imported.

### Run the services

```powershell
uvicorn app.main:app --reload
```

Interactive API docs are at `http://localhost:8000/docs`; health is at
`http://localhost:8000/health`.

### Email notifications

Configure SMTP in the backend `.env` for order, seller-application, and other
business notifications. Supabase Auth uses its own SMTP configuration for
confirmation and password-reset emails. Port 587 commonly uses
`SMTP_USE_TLS=true` and `SMTP_USE_SSL=false`; port 465 commonly uses
`SMTP_USE_SSL=true` and `SMTP_USE_TLS=false`. Keep SMTP credentials private.

## Authentication

Supabase Auth owns passwords, email confirmation, recovery, OAuth, and browser
sessions. The frontend stores and refreshes the Supabase session using the
Supabase JavaScript client with PKCE. The FastAPI API validates the bearer JWT
against the project's JWKS endpoint, then loads the linked CampusKart profile
and role from PostgreSQL. App roles are never accepted from browser metadata.

## API

### Authentication

Supabase Auth handles registration, email confirmation, password recovery, Google sign-in, and session refresh. The API verifies Supabase access tokens and resolves the CampusKart role from `users`; new authenticated users are provisioned as buyers. Only the admin bootstrap command can initially create an admin.

- Supabase client: email/password and Google OAuth; sessions use PKCE
- `GET /api/v1/auth/me` - current CampusKart profile and role
- `POST /api/v1/auth/seller-applications` - buyer submits/re-submits an application
- `GET /api/v1/auth/seller-applications` - admin lists pending applications
- `PATCH /api/v1/auth/seller-applications/{application_id}` - admin approves or rejects

Protected API calls use `Authorization: Bearer <supabase_access_token>`. The
frontend uses only the Supabase publishable/anon key; the secret/service-role key and
database URL belong only in the backend environment.

### Shopping cart

- `GET /api/v1/cart` — read the signed-in account's cart
- `POST /api/v1/cart/items` — add a product and quantity; adding an existing product increases its quantity
- `PATCH /api/v1/cart/items/{product_id}` — set a cart item's quantity
- `DELETE /api/v1/cart/items/{product_id}` — remove a cart item

Cart routes require a valid signed-in account. The API checks that products are active and quantities do not exceed current stock. Cart items do not reserve or reduce inventory until an order is placed. Apply the additive `0004_user_cart` migration with `alembic upgrade head` before using these routes against a database.

### Orders and checkout

- `POST /api/v1/orders` — place an order from the signed-in account's cart using Cash on Delivery and a delivery address
- `GET /api/v1/orders` — list the signed-in account's orders
- `GET /api/v1/orders/{order_id}` — read one of that account's orders
- `GET /api/v1/orders/admin` — admin list of all orders
- `PATCH /api/v1/orders/{order_id}/status` — admin status update (`placed`, `confirmed`, `shipped`, `delivered`, `cancelled`)

Order placement rechecks active product listings and stock, saves item and price snapshots, reduces stock, and clears the cart in one transaction. Admin status changes follow the order flow; cancellation is allowed before shipment and restores stock in the same transaction. COD payments begin as pending. The existing order status column supports tracking without a new database migration.

- `GET /api/v1/orders/buy-again` — buyer-only list of distinct products from the signed-in buyer's past orders, with current availability and stock information.

Deleted or inactive products and products with no stock remain visible as unavailable. Additions use the existing cart endpoint, which rechecks current availability and stock.

### Wishlist

- `GET /api/v1/wishlist` — list the signed-in buyer's saved products
- `PUT /api/v1/wishlist/{product_id}` — save a product (safe to repeat)
- `DELETE /api/v1/wishlist/{product_id}` — remove a saved product

Wishlist routes are buyer-only. The additive `0006_wishlist` migration creates the saved-product table; apply it with `alembic upgrade head` before using the feature.

### Product reviews and ratings

- `GET /api/v1/products/{product_id}/reviews` — public review list and average rating
- `GET /api/v1/products/{product_id}/reviews/mine` — the signed-in buyer's review for a product, if any
- `POST /api/v1/products/{product_id}/reviews` — create a 1–5 star rating and written review
- `PATCH /api/v1/reviews/{review_id}` and `DELETE /api/v1/reviews/{review_id}` — edit or remove the buyer's own review

Each buyer can have one review per product. Review routes that read or change a buyer's own review require the buyer role. The additive `0007_product_reviews` migration creates the review table; apply it with `alembic upgrade head` before using the feature.

### Recently viewed products

- `GET /api/v1/recently-viewed` — list the signed-in buyer's most recently viewed products
- `PUT /api/v1/recently-viewed/{product_id}` — record a product view for the signed-in buyer

Both routes are buyer-only. Viewing history is stored per account, is separate from wishlists, and keeps the latest 20 products. Apply the additive `0008_recently_viewed` migration with `alembic upgrade head` before using the feature.
### Catalog and roles

- `GET /api/v1/products` and `GET /api/v1/products/{product_id}` — public
- `GET /api/v1/products?category_id={id}&include_descendants=true` — public products in a category and its subcategories
- `GET /api/v1/products?section_slug=male|female|special_gifts` — public products assigned to a shopping section
- `POST /api/v1/products` — seller or admin
- `PATCH /api/v1/products/{product_id}` and `DELETE /api/v1/products/{product_id}` — seller may manage only their own products; admin may manage all
- `GET /api/v1/categories` and `GET /api/v1/categories/{category_id}` — public flat category list/details, including `parent_id`
- `GET /api/v1/categories/tree` — public nested category tree
- `POST /api/v1/categories`, `PATCH /api/v1/categories/{category_id}`, and `DELETE /api/v1/categories/{category_id}` — admin only

Categories may be nested by setting `parent_id` when creating or updating a
category. The hierarchy migration adds the nullable self-reference and seeds
the Electronics → Mobiles → Chargers, Grocery → Snacks → Biscuits, and
Stationery → Pens → Notebooks examples without replacing the existing catalog
or product IDs. Parent categories with children must be reorganized before
they can be deleted.

Products can also be assigned independently to multiple Male, Female, and
Special Gifts shopping sections using `section_slugs` on create/update. These
assignments are stored separately from categories; existing products remain
unassigned after the additive `0027_product_sections` migration.

## Frontend request example

```typescript
const { data: { session } } = await supabase.auth.getSession();
if (!session) throw new Error("Please sign in.");

const response = await fetch("http://localhost:8000/api/v1/auth/me", {
  headers: { Authorization: `Bearer ${session.access_token}` },
});
```

### Seller dashboard

- `GET /api/v1/seller/dashboard` — seller-only summary of that seller's products, non-cancelled orders, units sold, revenue, and five recent orders containing their products.

The endpoint derives its seller ID from the authenticated account and does not accept a seller ID from the request. Product counts include all current listings. Sales, order counts, and revenue exclude cancelled orders. Recent order summaries include only the seller's own items and subtotal, including orders later cancelled.

### Admin dashboard

- `GET /api/v1/admin/dashboard` — admin-only totals for users, buyers, sellers, products, orders, and non-cancelled order value, plus seven-day registration and order counts and recent account, listing, order, review, and seller-application activity.

The endpoint requires an admin account. Revenue is the value of non-cancelled orders; COD collection is not tracked as completed revenue. Recent activity lists record creation events and the current order status; order status changes are not stored as a separate activity log.
# Razorpay test checkout

Online checkout is optional; Cash on Delivery continues to work without Razorpay credentials. To enable test payments, generate **Test Mode** API keys in the Razorpay Dashboard and put the `rzp_test_...` Key ID and its Key Secret in `backend/.env` as `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`. The secret stays on the backend; do not put it in frontend environment variables or commit `.env`.

Apply pending additive database migrations before starting the updated API:

```powershell
cd backend
alembic upgrade head
```

### Coupons and discounts

- `GET /api/v1/coupons` — admin list of coupons
- `POST /api/v1/coupons` — admin creates a fixed-amount or percentage coupon, with optional minimum order, maximum discount, usage limit, and active dates
- `PATCH /api/v1/coupons/{coupon_id}` — admin edits or disables a coupon
- `POST /api/v1/coupons/validate` — buyer checks a code against their current cart

Checkout sends the coupon code again when placing a COD or Razorpay order. The backend rechecks eligibility and usage limits, calculates the discount, and records the subtotal, code, discount, and final total on the order. Existing orders receive their old total as their subtotal in the additive `0018_coupons` migration. Pending Razorpay orders reserve one coupon use; cancelling a pending payment releases it. A coupon discount that covers the full order creates an order with no payment due.

The API creates Razorpay Orders from the server-calculated discounted cart total, reserves stock while payment is pending, checks the Checkout signature and captured payment with Razorpay, then marks the order paid. Closing or failing the Checkout cancels the pending order and restores stock. Razorpay test transactions are simulated and do not collect real money. Set the Razorpay Dashboard to auto-capture payments so captured transactions can complete the order flow.
