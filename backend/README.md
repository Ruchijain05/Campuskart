# CampusKart backend

FastAPI API using SQLAlchemy 2.x, MySQL/PyMySQL, Alembic, and OAuth2 Bearer JWT
authentication. The product and category read endpoints remain public; write
operations are protected by roles.

## Setup

From the `backend` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If `.env` does not exist, create it from `.env.example`. If it already exists,
keep its database settings and merge in missing auth and SMTP settings instead of
overwriting it.

Set `DATABASE_URL` to the CampusKart MySQL database and set `JWT_SECRET_KEY` to
a randomly generated value of at least 32 characters. Generate a key with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the generated value into `.env`; do not commit `.env`. The signing key is
required and the example's empty value is intentionally unusable.

### Email notifications

Configure SMTP in the backend `.env` file. Set `SMTP_HOST`, `SMTP_PORT`, and
`SMTP_FROM_EMAIL`; also set `SMTP_USERNAME` and `SMTP_PASSWORD` when the relay
requires authentication. SMTP credentials come from environment settings and
must not be committed. Port 587 commonly uses `SMTP_USE_TLS=true` and
`SMTP_USE_SSL=false`; port 465 commonly uses `SMTP_USE_SSL=true` and
`SMTP_USE_TLS=false`. If the host or sender is not configured, non-account email
notifications are skipped while in-app notifications continue to work.
Registration fails explicitly if its verification email cannot be delivered.
Mail delivery failures do not undo orders or admin decisions.

Account registration and recovery require working SMTP delivery. Set
`FRONTEND_BASE_URL` to the public frontend origin for email links. Verification
links expire after 60 minutes and password-reset links after 30 minutes by
default; configure `EMAIL_VERIFICATION_TOKEN_MINUTES` and
`PASSWORD_RESET_TOKEN_MINUTES` to change those limits. Tokens are random,
single-use, and stored only as hashes. New accounts must verify their email
before signing in; existing users are marked verified by migration to preserve
current accounts.

## Database migrations

Back up the database before applying schema changes. Automatic
`create_all()` has been replaced by Alembic migrations so existing products
receive the new nullable seller ownership column safely.

For a **new empty database**:

```powershell
alembic upgrade head
```

For an **existing database** created by the earlier CampusKart backend, verify
that its `categories` and `products` tables match the original catalog schema,
then mark that schema as the Alembic baseline and apply the auth migration:

```powershell
alembic stamp 0001_catalog
alembic upgrade head
```

The existing products retain their data and have `seller_id=NULL`; only admins
can modify those legacy products. Do not stamp a database that does not already
have the catalog baseline tables.

Product image galleries use the additive `0013_product_images` migration. It
creates a gallery table and copies each existing `products.image_url` into it
as the primary image, while leaving the original product column intact. Apply
it with `alembic upgrade head` before using seller image management. Uploaded
files are stored under `MEDIA_ROOT` (default: `backend/uploads`) and served
from `/media/`; keep that directory persistent and backed up with the database.
Existing external image URLs do not need to be copied to disk.

Saved buyer delivery addresses use the additive `0014_delivery_addresses`
migration. It creates an account-owned address table and does not alter or
remove existing orders or account data. Apply with `alembic upgrade head`.

Seller-configurable low-stock thresholds and alert de-duplication use the
additive `0015_low_stock_alerts` migration. Existing products receive a
threshold of 5; existing seller products already at/below that threshold get a
single in-app alert and are marked alerted. Apply with `alembic upgrade head`
before editing thresholds or using seller/admin low-stock views.

Buyer support requests and admin replies use the additive
`0016_support_tickets` migration. It creates ticket and reply tables without
changing existing accounts, orders, or notifications. Apply with
`alembic upgrade head` before opening the support pages.

Student product requests use the additive `0028_product_requests` migration.
It creates a separate request table and leaves existing catalog, account, and
order data unchanged. Buyers can submit a request with an optional JPEG, PNG,
or WebP photo (up to 5 MB); admins can respond with availability, price, and
estimated delivery time. Responses create in-app notifications for the buyer.
Apply with `alembic upgrade head` before using the request pages. Request
photos are stored under `MEDIA_ROOT/product-requests/` and are served from
`/media/`; back up this directory along with other uploaded media.

Product image galleries use the additive `0013_product_images` migration. It
creates a gallery table and copies each existing `products.image_url` into it
as the primary image, while leaving the original product column intact. Apply
it with `alembic upgrade head` before using seller image management. Uploaded
files are stored under `MEDIA_ROOT` (default: `backend/uploads`) and served
from `/media/`; keep that directory persistent and backed up with the database.
Existing external image URLs do not need to be copied to disk.

Create the first admin interactively after migrating:

```powershell
python -m scripts.create_admin
```

The script reads the password without echoing it and refuses to bootstrap if an
admin already exists. Public registration always creates a buyer.

Start the API:

```powershell
uvicorn app.main:app --reload
```

Interactive docs are at `http://localhost:8000/docs`; health is at
`http://localhost:8000/health`.

## Authentication

Passwords use Argon2 hashing. Access JWTs expire after 15 minutes by default.
Browser sign-in sessions last 30 days by default and can be configured with
`REFRESH_SESSION_DAYS`. The browser stores a random refresh token in an HttpOnly,
SameSite cookie; the server stores only its hash. Access tokens remain in memory,
and the app obtains a fresh one from the cookie when it starts. Logging out
revokes the entire browser session immediately.

Set `REFRESH_COOKIE_SECURE=true` when serving the frontend over HTTPS. For
frontends and APIs on different sites, configure
`REFRESH_COOKIE_SAMESITE=none` and keep `REFRESH_COOKIE_SECURE=true`; the API
also checks that refresh and cookie-based logout requests come from a configured
`FRONTEND_ORIGINS` origin.

Open `http://localhost:8000/docs`, click **Authorize**, enter the account email
in the **username** field and the password, then authorize. Swagger obtains an
access token from `/api/v1/auth/token`, retains it for its UI session, and sends
it as an `Authorization: Bearer ...` header on protected requests. No token
copying is needed. Swagger continues to use its bearer token directly; browser
session restoration is handled by the CampusKart frontend.

## API

### Authentication

- `POST /api/v1/auth/token` — OAuth2 form login (`username` is the account email); returns a Bearer access token
- `POST /api/v1/auth/refresh` — exchange the browser's HttpOnly refresh cookie for an access token
- `POST /api/v1/auth/forgot-password` — send password-reset instructions without disclosing whether an account exists
- `POST /api/v1/auth/reset-password` — set a new password with a valid one-time reset token and revoke existing sessions
- `POST /api/v1/auth/verify-email` — verify an email address with a one-time token
- `POST /api/v1/auth/resend-verification` — resend a verification link without disclosing account state
- `POST /api/v1/auth/register` — register as a buyer (verify email before signing in)
- `POST /api/v1/auth/logout` — revoke the browser session and clear its refresh cookie
- `GET /api/v1/auth/me` — current authenticated account
- `POST /api/v1/auth/seller-applications` — buyer submits/re-submits an application
- `GET /api/v1/auth/seller-applications` — admin lists pending applications
- `PATCH /api/v1/auth/seller-applications/{application_id}` — admin approves or rejects

Registration requires name, email, a password of 8–128 characters with at least one letter, one number, and one special character, and a phone
number containing exactly 10 digits.

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

```javascript
const response = await fetch("http://localhost:8000/api/v1/auth/token", {
  method: "POST",
  headers: { "Content-Type": "application/x-www-form-urlencoded" },
  body: new URLSearchParams({ username: email, password }),
});
const { access_token } = await response.json();

const profile = await fetch("http://localhost:8000/api/v1/auth/me", {
  headers: { Authorization: `Bearer ${access_token}` },
});
```

For production browser apps, use a standard authorization-code flow with PKCE
rather than persisting access tokens in JavaScript storage. The password flow
is provided for first-party Swagger use and trusted clients.

Shipping-provider integration is not included. Configured SMTP sends account
verification and password-reset links, order confirmations and status updates,
return/refund decisions and status updates, and seller application decisions.

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
