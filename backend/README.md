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
keep its database settings and merge in the missing auth settings instead of
overwriting it.

Set `DATABASE_URL` to the CampusKart MySQL database and set `JWT_SECRET_KEY` to
a randomly generated value of at least 32 characters. Generate a key with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the generated value into `.env`; do not commit `.env`. The signing key is
required and the example's empty value is intentionally unusable.

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
The server stores a hash of each active token identifier, so logout revokes the
current token immediately. Expired tokens require signing in again.

Open `http://localhost:8000/docs`, click **Authorize**, enter the account email
in the **username** field and the password, then authorize. Swagger obtains an
access token from `/api/v1/auth/token`, retains it for its UI session, and sends
it as an `Authorization: Bearer ...` header on protected requests. No token
copying, cookies, or CSRF header is needed. Click **Authorize** again with
credentials after the token expires.

## API

### Authentication

- `POST /api/v1/auth/token` — OAuth2 form login (`username` is the account email); returns a Bearer access token
- `POST /api/v1/auth/register` — register as a buyer (sign in separately using **Authorize**)
- `POST /api/v1/auth/logout` — revoke the current access token
- `GET /api/v1/auth/me` — current authenticated account
- `POST /api/v1/auth/seller-applications` — buyer submits/re-submits an application
- `GET /api/v1/auth/seller-applications` — admin lists pending applications
- `PATCH /api/v1/auth/seller-applications/{application_id}` — admin approves or rejects

Registration requires name, email, a password of 8–128 characters with at least one letter, one number, and one special character, and a phone
number containing exactly 10 digits.
Email verification is not enabled; successful registration activates the
account immediately.

### Shopping cart

- `GET /api/v1/cart` — read the signed-in account's cart
- `POST /api/v1/cart/items` — add a product and quantity; adding an existing product increases its quantity
- `PATCH /api/v1/cart/items/{product_id}` — set a cart item's quantity
- `DELETE /api/v1/cart/items/{product_id}` — remove a cart item

Cart routes require a valid signed-in account. The API checks that products are active and quantities do not exceed current stock. Cart items do not reserve or reduce inventory; checkout and payment are not included. Apply the additive `0004_user_cart` migration with `alembic upgrade head` before using these routes against a database.
### Catalog and roles

- `GET /api/v1/products` and `GET /api/v1/products/{product_id}` — public
- `GET /api/v1/products?category_id={id}&include_descendants=true` — public products in a category and its subcategories
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

Email verification, password reset, and email delivery are not included yet.
