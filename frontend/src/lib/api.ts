import type {
  Category,
  CategoryInput,
  Product,
  ProductInput,
  SellerApplication,
  CategoryTree,
  Cart,
  User,
} from "./types";

export interface BulkProductRowError {
  row: number;
  field: string;
  message: string;
}

export interface BulkProductImportResult {
  imported_count: number;
  products: Product[];
}

export class BulkProductUploadError extends Error {
  constructor(message: string, public readonly rowErrors: BulkProductRowError[] = []) {
    super(message);
    this.name = "BulkProductUploadError";
  }
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000")
  .replace(/\/+$/, "");
const API_PREFIX = `${API_BASE_URL}/api/v1`;

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof URLSearchParams)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_PREFIX}${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => null) as
      | { detail?: string | Array<{ msg?: string }> }
      | null;
    const detail = body?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg).filter(Boolean).join("; ")
      : detail;
    throw new Error(message || `Request failed (${response.status})`);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  listProducts: (skip = 0, limit = 100, categoryId?: number) => {
    const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
    if (categoryId !== undefined) {
      params.set("category_id", String(categoryId));
      params.set("include_descendants", "true");
    }
    return request<Product[]>(`/products?${params.toString()}`);
  },
  listAllProducts: async (categoryId?: number) => {
    const pageSize = 100;
    const products: Product[] = [];
    let skip = 0;
    let page: Product[];
    do {
      page = await api.listProducts(skip, pageSize, categoryId);
      products.push(...page);
      skip += page.length;
    } while (page.length === pageSize);
    return products;
  },
  getProduct: (id: number) => request<Product>(`/products/${id}`),
  createProduct: (input: ProductInput, token: string) =>
    request<Product>("/products", { method: "POST", body: JSON.stringify(input) }, token),
  uploadProducts: async (file: File, token: string): Promise<BulkProductImportResult> => {
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(`${API_PREFIX}/products/bulk`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    });
    const body = await response.json().catch(() => null) as
      | BulkProductImportResult
      | {
          detail?: string | {
            message?: string;
            errors?: BulkProductRowError[];
          };
        }
      | null;
    if (!response.ok) {
      const detail = body && "detail" in body ? body.detail : undefined;
      if (detail && typeof detail === "object") {
        throw new BulkProductUploadError(
          detail.message || "Some product rows need to be fixed.",
          detail.errors ?? [],
        );
      }
      throw new BulkProductUploadError(
        typeof detail === "string" ? detail : `Request failed (${response.status})`,
      );
    }
    return body as BulkProductImportResult;
  },
  updateProduct: (id: number, input: Partial<ProductInput>, token: string) =>
    request<Product>(`/products/${id}`, { method: "PATCH", body: JSON.stringify(input) }, token),
  deleteProduct: (id: number, token: string) =>
    request<void>(`/products/${id}`, { method: "DELETE" }, token),
  getCart: (token: string) => request<Cart>("/cart", {}, token),
  addCartItem: (product_id: number, quantity: number, token: string) =>
    request<Cart>("/cart/items", { method: "POST", body: JSON.stringify({ product_id, quantity }) }, token),
  updateCartItem: (productId: number, quantity: number, token: string) =>
    request<Cart>(`/cart/items/${productId}`, { method: "PATCH", body: JSON.stringify({ quantity }) }, token),
  removeCartItem: (productId: number, token: string) =>
    request<Cart>(`/cart/items/${productId}`, { method: "DELETE" }, token),
  listCategories: () => request<Category[]>("/categories"),
  listCategoryTree: () => request<CategoryTree[]>("/categories/tree"),
  createCategory: (input: CategoryInput, token: string) =>
    request<Category>("/categories", { method: "POST", body: JSON.stringify(input) }, token),
  updateCategory: (id: number, input: Partial<CategoryInput>, token: string) =>
    request<Category>(`/categories/${id}`, { method: "PATCH", body: JSON.stringify(input) }, token),
  deleteCategory: (id: number, token: string) =>
    request<void>(`/categories/${id}`, { method: "DELETE" }, token),
  register: (input: {
    full_name: string;
    email: string;
    password: string;
    phone_number: string;
  }) =>
    request<User>("/auth/register", { method: "POST", body: JSON.stringify(input) }),
  login: async (email: string, password: string) => {
    const form = new URLSearchParams({ username: email, password });
    const result = await request<{ access_token: string; token_type: string }>(
      "/auth/token",
      { method: "POST", body: form },
    );
    return result.access_token;
  },
  me: (token: string) => request<User>("/auth/me", {}, token),
  logout: (token: string) => request<void>("/auth/logout", { method: "POST" }, token),
  applyToSell: (message: string, token: string) =>
    request<SellerApplication>(
      "/auth/seller-applications",
      { method: "POST", body: JSON.stringify({ message: message || null }) },
      token,
    ),
  listSellerApplications: (token: string) =>
    request<SellerApplication[]>("/auth/seller-applications", {}, token),
  reviewSellerApplication: (
    id: number,
    decision: "approved" | "rejected",
    review_note: string,
    token: string,
  ) =>
    request<SellerApplication>(
      `/auth/seller-applications/${id}`,
      { method: "PATCH", body: JSON.stringify({ decision, review_note: review_note || null }) },
      token,
    ),
};
