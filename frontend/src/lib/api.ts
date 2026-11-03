import type {
  Category,
  CategoryInput,
  Product,
  ProductInput,
  SellerApplication,
  CategoryTree,
  Cart,
  Order,
  OrderStatus,
  RazorpayPaymentStart,
  DeliveryAddress,
  ProductReview,
  ProductReviewInput,
  ProductReviewSummary,
  SellerDashboard,
  AdminDashboard,
  BuyAgainProduct,
  User,
  Notification,
  NotificationSummary,
  SellerOrder,
  SellerOrderItem,
  FulfillmentStatus,
  ProductQuestion,
  ReturnRequest,
  AdminReturnRequest,
  ReturnType,
  ReturnStatus,
  RefundStatus,
  ProductImage,
  ProductRecommendations,
  SavedAddress,
  SavedAddressInput,
  LowStockProduct,
  SupportTicket,
  SupportTicketCategory,
  SupportTicketStatus,
  SupportTicketDetail,
  AdminSupportTicket,
  AdminSupportTicketDetail,
  ProductRequest,
  AdminProductRequest,
  Coupon,
  CouponInput,
  CouponQuote,
  ProductOfferInput,
  ShippingSettings,
  OrderShippingInput,
  SellerPayoutHistory,
  AdminPayoutDashboard,
  AdminPayout,
  PayoutStatus,
  ProductBundle,
  ProductBundleInput,
  PickupLocation,
  PickupLocationInput,
  ShoppingSectionSlug,
  Conversation,
  ConversationDetail,
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

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000")
  .replace(/\/+$/, "");
const API_PREFIX = `${API_BASE_URL}/api/v1`;

let refreshedTokenHandler: ((token: string) => void) | null = null;
let refreshInFlight: Promise<string> | null = null;

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
  retryAfterRefresh = true,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof URLSearchParams) && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_PREFIX}${path}`, { ...options, headers });
  if (response.status === 401 && token && retryAfterRefresh) {
    const refreshedToken = await refreshAccessToken();
    return request<T>(path, options, refreshedToken, false);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null) as
      | { detail?: string | Array<{ msg?: string }> }
      | null;
    const detail = body?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg).filter(Boolean).join("; ")
      : detail;
    throw new ApiError(message || `Request failed (${response.status})`, response.status);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function refreshAccessToken(): Promise<string> {
  if (!refreshInFlight) {
    refreshInFlight = request<{ access_token: string; token_type: string }>(
      "/auth/refresh",
      { method: "POST", credentials: "include" },
    )
      .then(({ access_token }) => {
        refreshedTokenHandler?.(access_token);
        return access_token;
      })
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

export const api = {
  getRecommendations: (token: string) => request<ProductRecommendations>("/recommendations", {}, token),
  getPopularProducts: () => request<Product[]>("/recommendations/popular"),
  listRecentlyViewed: (token: string) => request<Product[]>("/recently-viewed", {}, token),
  listNotifications: (token: string) => request<NotificationSummary>("/notifications", {}, token),
  getUnreadNotificationCount: (token: string) => request<{ unread_count: number }>("/notifications/unread-count", {}, token),
  markNotificationRead: (id: number, token: string) =>
    request<Notification>(`/notifications/${id}/read`, { method: "PATCH" }, token),
  markAllNotificationsRead: (token: string) =>
    request<void>("/notifications/read", { method: "PATCH" }, token),
  recordRecentlyViewed: (productId: number, token: string) =>
    request<void>(`/recently-viewed/${productId}`, { method: "PUT" }, token),
  getAdminDashboard: (token: string) => request<AdminDashboard>("/admin/dashboard", {}, token),
  getSellerDashboard: (token: string) => request<SellerDashboard>("/seller/dashboard", {}, token),
  getSellerPayoutHistory: (token: string) => request<SellerPayoutHistory>("/seller/payouts", {}, token),
  getAdminPayoutDashboard: (token: string) => request<AdminPayoutDashboard>("/admin/payouts", {}, token),
  createAdminPayout: (input: { seller_id: number; amount: number; reference: string | null; note: string | null }, token: string) =>
    request<AdminPayout>("/admin/payouts", { method: "POST", body: JSON.stringify(input) }, token),
  updateAdminPayout: (id: number, input: { status: PayoutStatus; reference: string | null; note: string | null }, token: string) =>
    request<AdminPayout>(`/admin/payouts/${id}`, { method: "PATCH", body: JSON.stringify(input) }, token),
  listSellerLowStock: (token: string) => request<LowStockProduct[]>("/seller/low-stock", {}, token),
  listAdminLowStock: (token: string) => request<LowStockProduct[]>("/admin/low-stock", {}, token),
  createSupportTicket: (input: { subject: string; category: SupportTicketCategory; description: string }, token: string) =>
    request<SupportTicket>("/support/tickets", { method: "POST", body: JSON.stringify(input) }, token),
  listSupportTickets: (token: string) => request<SupportTicket[]>("/support/tickets", {}, token),
  getSupportTicket: (id: number, token: string) => request<SupportTicketDetail>(`/support/tickets/${id}`, {}, token),
  listAdminSupportTickets: (token: string) => request<AdminSupportTicket[]>("/admin/support/tickets", {}, token),
  getAdminSupportTicket: (id: number, token: string) => request<AdminSupportTicketDetail>(`/admin/support/tickets/${id}`, {}, token),
  replySupportTicket: (id: number, body: string, token: string) => request<AdminSupportTicketDetail>(`/admin/support/tickets/${id}/replies`, { method: "POST", body: JSON.stringify({ body }) }, token),
  updateSupportTicketStatus: (id: number, status: SupportTicketStatus, token: string) => request<AdminSupportTicketDetail>(`/admin/support/tickets/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) }, token),
  listProductRequests: (token: string) => request<ProductRequest[]>("/product-requests", {}, token),
  createProductRequest: (input: { product_name: string; quantity: number; message: string; photo: File | null }, token: string) => {
    const form = new FormData();
    form.append("product_name", input.product_name);
    form.append("quantity", String(input.quantity));
    form.append("message", input.message);
    if (input.photo) form.append("photo", input.photo);
    return request<ProductRequest>("/product-requests", { method: "POST", body: form }, token);
  },
  listAdminProductRequests: (token: string) => request<AdminProductRequest[]>("/admin/product-requests", {}, token),
  respondToProductRequest: (id: number, response: {
    can_arrange: boolean;
    price: number | null;
    expected_delivery_days: number | null;
    admin_message: string;
  }, token: string) => request<AdminProductRequest>(`/admin/product-requests/${id}/response`, { method: "PATCH", body: JSON.stringify(response) }, token),
  listSellerOrders: (token: string) => request<SellerOrder[]>("/seller/orders", {}, token),
  updateSellerItemFulfillment: (itemId: number, status: FulfillmentStatus, token: string) =>
    request<SellerOrderItem>(`/seller/orders/items/${itemId}/fulfillment`, { method: "PATCH", body: JSON.stringify({ status }) }, token),
  listProducts: (skip = 0, limit = 100, categoryId?: number, filters: {
    search?: string; minPrice?: string; maxPrice?: string; minRating?: string; inStock?: boolean; sort?: string; sectionSlug?: ShoppingSectionSlug;
  } = {}) => {
    const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
    if (categoryId !== undefined) {
      params.set("category_id", String(categoryId));
      params.set("include_descendants", "true");
    }
    if (filters.search) params.set("search", filters.search);
    if (filters.minPrice) params.set("min_price", filters.minPrice);
    if (filters.maxPrice) params.set("max_price", filters.maxPrice);
    if (filters.minRating) params.set("min_rating", filters.minRating);
    if (filters.inStock) params.set("in_stock", "true");
    if (filters.sort) params.set("sort", filters.sort);
    if (filters.sectionSlug) params.set("section_slug", filters.sectionSlug);
    return request<Product[]>(`/products?${params.toString()}`);
  },
  listAllProducts: async (categoryId?: number, filters: {
    search?: string; minPrice?: string; maxPrice?: string; minRating?: string; inStock?: boolean; sort?: string; sectionSlug?: ShoppingSectionSlug;
  } = {}) => {
    const pageSize = 100;
    const products: Product[] = [];
    let skip = 0;
    let page: Product[];
    do {
      page = await api.listProducts(skip, pageSize, categoryId, filters);
      products.push(...page);
      skip += page.length;
    } while (page.length === pageSize);
    return products;
  },
  listConversations: (token: string) => request<Conversation[]>("/conversations", {}, token),
  getConversation: (id: number, token: string) => request<ConversationDetail>(`/conversations/${id}`, {}, token),
  startConversation: (product_id: number, body: string, token: string) => request<ConversationDetail>("/conversations", { method: "POST", body: JSON.stringify({ product_id, body }) }, token),
  sendConversationMessage: (id: number, body: string, token: string) => request<ConversationDetail>(`/conversations/${id}/messages`, { method: "POST", body: JSON.stringify({ body }) }, token),
  updateConversationStatus: (id: number, status: "open" | "closed", token: string) => request<Conversation>(`/conversations/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) }, token),
  getUnreadChatCount: (token: string) => request<{ unread_count: number }>("/conversations/unread-count", {}, token),
  getProduct: (id: number) => request<Product>(`/products/${id}`),
  listBundles: () => request<ProductBundle[]>("/bundles"),
  getBundle: (id: number) => request<ProductBundle>(`/bundles/${id}`),
  placeBundleOrder: (id: number, quantity: number, address: DeliveryAddress, token: string, delivery_method?: "home_delivery" | "campus_pickup", pickup_location_id?: number) =>
    request<Order>(`/bundles/${id}/orders`, { method: "POST", body: JSON.stringify({ ...address, quantity, delivery_method, pickup_location_id }) }, token),
  listAdminBundles: (token: string) => request<ProductBundle[]>("/admin/bundles", {}, token),
  createBundle: (input: ProductBundleInput, token: string) =>
    request<ProductBundle>("/admin/bundles", { method: "POST", body: JSON.stringify(input) }, token),
  updateBundle: (id: number, input: ProductBundleInput, token: string) =>
    request<ProductBundle>(`/admin/bundles/${id}`, { method: "PUT", body: JSON.stringify(input) }, token),
  disableBundle: (id: number, token: string) =>
    request<ProductBundle>(`/admin/bundles/${id}`, { method: "DELETE" }, token),
  listAdminOfferProducts: (token: string) => request<Product[]>("/products/admin-offers/products", {}, token),
  saveProductOffer: (id: number, input: ProductOfferInput, token: string) =>
    request<Product>(`/products/admin-offers/${id}`, { method: "PUT", body: JSON.stringify(input) }, token),
  disableProductOffer: (id: number, token: string) =>
    request<Product>(`/products/admin-offers/${id}`, { method: "DELETE" }, token),
  listProductImages: (id: number) => request<ProductImage[]>(`/products/${id}/images`),
  uploadProductImages: (id: number, files: File[], token: string) => {
    const form = new FormData();
    files.forEach((file) => form.append("files", file));
    return request<ProductImage[]>(`/products/${id}/images`, { method: "POST", body: form }, token);
  },
  setPrimaryProductImage: (productId: number, imageId: number, token: string) =>
    request<ProductImage[]>(`/products/${productId}/images/${imageId}/primary`, { method: "PATCH" }, token),
  replaceProductImage: (productId: number, imageId: number, file: File, token: string) => {
    const form = new FormData();
    form.append("file", file);
    return request<ProductImage[]>(`/products/${productId}/images/${imageId}`, { method: "PUT", body: form }, token);
  },
  deleteProductImage: (productId: number, imageId: number, token: string) =>
    request<ProductImage[]>(`/products/${productId}/images/${imageId}`, { method: "DELETE" }, token),
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
  placeOrder: (address: DeliveryAddress, token: string, coupon_code?: string, delivery_method?: "home_delivery" | "campus_pickup", pickup_location_id?: number) =>
    request<Order>("/orders", { method: "POST", body: JSON.stringify({ ...address, coupon_code, delivery_method, pickup_location_id }) }, token),
  startRazorpayPayment: (address: DeliveryAddress, token: string, coupon_code?: string, delivery_method?: "home_delivery" | "campus_pickup", pickup_location_id?: number) =>
    request<RazorpayPaymentStart>("/payments/razorpay/orders", { method: "POST", body: JSON.stringify({ ...address, coupon_code, delivery_method, pickup_location_id }) }, token),
  verifyRazorpayPayment: (details: { razorpay_order_id: string; razorpay_payment_id: string; razorpay_signature: string }, token: string) =>
    request<Order>("/payments/razorpay/verify", { method: "POST", body: JSON.stringify(details) }, token),
  cancelRazorpayPayment: (orderId: number, token: string) =>
    request<Order>(`/payments/razorpay/orders/${orderId}/cancel`, { method: "POST" }, token),
  validateCoupon: (code: string, token: string) =>
    request<CouponQuote>("/coupons/validate", { method: "POST", body: JSON.stringify({ code }) }, token),
  listAdminCoupons: (token: string) => request<Coupon[]>("/coupons", {}, token),
  createCoupon: (coupon: CouponInput, token: string) =>
    request<Coupon>("/coupons", { method: "POST", body: JSON.stringify(coupon) }, token),
  updateCoupon: (id: number, coupon: Partial<CouponInput>, token: string) =>
    request<Coupon>(`/coupons/${id}`, { method: "PATCH", body: JSON.stringify(coupon) }, token),
  listAddresses: (token: string) => request<SavedAddress[]>("/addresses", {}, token),
  createAddress: (address: SavedAddressInput, token: string) =>
    request<SavedAddress>("/addresses", { method: "POST", body: JSON.stringify(address) }, token),
  updateAddress: (id: number, address: Partial<SavedAddressInput>, token: string) =>
    request<SavedAddress>(`/addresses/${id}`, { method: "PATCH", body: JSON.stringify(address) }, token),
  deleteAddress: (id: number, token: string) =>
    request<void>(`/addresses/${id}`, { method: "DELETE" }, token),
  listOrders: (token: string) => request<Order[]>("/orders", {}, token),
  downloadOrderInvoice: async (id: number, token: string): Promise<Blob> => {
    const response = await fetch(`${API_PREFIX}/orders/${id}/invoice`, { headers: { Authorization: `Bearer ${token}` } });
    if (!response.ok) {
      const body = await response.json().catch(() => null) as { detail?: string } | null;
      throw new Error(body?.detail || `Invoice download failed (${response.status})`);
    }
    return response.blob();
  },
  listBuyAgainProducts: (token: string) => request<BuyAgainProduct[]>("/orders/buy-again", {}, token),
  getOrder: (id: number, token: string) => request<Order>(`/orders/${id}`, {}, token),
  listAdminOrders: (token: string) => request<Order[]>("/orders/admin", {}, token),
  getShippingSettings: () => request<ShippingSettings>("/shipping/settings"),
  listPickupLocations: () => request<PickupLocation[]>("/pickup/locations"),
  listAdminPickupLocations: (token: string) => request<PickupLocation[]>("/pickup/locations/admin", {}, token),
  createPickupLocation: (input: PickupLocationInput, token: string) => request<PickupLocation>("/pickup/locations", { method: "POST", body: JSON.stringify(input) }, token),
  updatePickupLocation: (id: number, input: PickupLocationInput, token: string) => request<PickupLocation>(`/pickup/locations/${id}`, { method: "PUT", body: JSON.stringify(input) }, token),
  disablePickupLocation: (id: number, token: string) => request<PickupLocation>(`/pickup/locations/${id}`, { method: "DELETE" }, token),
  updateShippingSettings: (input: ShippingSettings, token: string) =>
    request<ShippingSettings>("/shipping/settings", { method: "PUT", body: JSON.stringify({ delivery_charge: input.delivery_charge, estimated_delivery_days: input.estimated_delivery_days }) }, token),
  updateOrderShipping: (id: number, input: OrderShippingInput, token: string) =>
    request<Order>(`/orders/${id}/shipping`, { method: "PATCH", body: JSON.stringify(input) }, token),
  markPickupReady: (id: number, token: string) => request<Order>(`/orders/${id}/pickup/ready`, { method: "PATCH" }, token),
  updateOrderStatus: (id: number, status: OrderStatus, token: string) =>
    request<Order>(`/orders/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) }, token),
  getWishlist: (token: string) => request<Product[]>("/wishlist", {}, token),
  addWishlistItem: (productId: number, token: string) =>
    request<Product[]>(`/wishlist/${productId}`, { method: "PUT" }, token),
  removeWishlistItem: (productId: number, token: string) =>
    request<Product[]>(`/wishlist/${productId}`, { method: "DELETE" }, token),
  getProductReviews: (productId: number) =>
    request<ProductReviewSummary>(`/products/${productId}/reviews`),
  getMyProductReview: (productId: number, token: string) =>
    request<ProductReview | null>(`/products/${productId}/reviews/mine`, {}, token),
  createProductReview: (productId: number, input: ProductReviewInput, token: string) =>
    request<ProductReview>(`/products/${productId}/reviews`, { method: "POST", body: JSON.stringify(input) }, token),
  updateProductReview: (reviewId: number, input: ProductReviewInput, token: string) =>
    request<ProductReview>(`/reviews/${reviewId}`, { method: "PATCH", body: JSON.stringify(input) }, token),
  deleteProductReview: (reviewId: number, token: string) =>
    request<void>(`/reviews/${reviewId}`, { method: "DELETE" }, token),
  listProductQuestions: (productId: number) =>
    request<ProductQuestion[]>(`/products/${productId}/questions`),
  askProductQuestion: (productId: number, question: string, token: string) =>
    request<ProductQuestion>(`/products/${productId}/questions`, { method: "POST", body: JSON.stringify({ question }) }, token),
  answerProductQuestion: (questionId: number, answer: string, token: string) =>
    request<ProductQuestion>(`/questions/${questionId}/answer`, { method: "PATCH", body: JSON.stringify({ answer }) }, token),
  listMyQuestions: (token: string) => request<ProductQuestion[]>("/questions/mine", {}, token),
  requestReturn: (orderId: number, request_type: ReturnType, reason: string, token: string) =>
    request<ReturnRequest>(`/orders/${orderId}/returns`, { method: "POST", body: JSON.stringify({ request_type, reason }) }, token),
  listMyReturns: (token: string) => request<ReturnRequest[]>("/returns", {}, token),
  listAdminReturns: (token: string) => request<AdminReturnRequest[]>("/admin/returns", {}, token),
  reviewReturn: (id: number, decision: Exclude<ReturnStatus, "pending">, review_note: string, token: string) =>
    request<AdminReturnRequest>(`/admin/returns/${id}/decision`, { method: "PATCH", body: JSON.stringify({ decision, review_note: review_note || null }) }, token),
  updateRefundStatus: (id: number, status: RefundStatus, token: string) =>
    request<AdminReturnRequest>(`/admin/returns/${id}/refund`, { method: "PATCH", body: JSON.stringify({ status }) }, token),
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
  forgotPassword: (email: string) =>
    request<{ message: string }>("/auth/forgot-password", { method: "POST", body: JSON.stringify({ email }) }),
  resetPassword: (token: string, password: string) =>
    request<{ message: string }>("/auth/reset-password", { method: "POST", body: JSON.stringify({ token, password }) }),
  verifyEmail: (token: string) =>
    request<{ message: string }>("/auth/verify-email", { method: "POST", body: JSON.stringify({ token }) }),
  resendVerification: (email: string) =>
    request<{ message: string }>("/auth/resend-verification", { method: "POST", body: JSON.stringify({ email }) }),
  login: async (email: string, password: string) => {
    const form = new URLSearchParams({ username: email, password });
    const result = await request<{ access_token: string; token_type: string }>(
      "/auth/token",
      { method: "POST", body: form, credentials: "include" },
    );
    return result.access_token;
  },
  refreshAccessToken,
  setRefreshedTokenHandler: (handler: ((token: string) => void) | null) => {
    refreshedTokenHandler = handler;
  },
  me: (token: string) => request<User>("/auth/me", {}, token),
  logout: (token: string) =>
    request<void>("/auth/logout", { method: "POST", credentials: "include" }, token),
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
