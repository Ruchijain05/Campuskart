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
authentication, seller applications, product listings, and admin moderation.
Category browsing supports nested categories, while admins can organize the
category tree and sellers can assign products to a category path.
There are no cart, checkout, order, wishlist, review, or rating endpoints in the
backend, so those workflows are not represented as working features.

Access tokens are kept in React memory and are not written to browser storage.
Signing in again is required after a full page reload.
