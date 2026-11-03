export type UserRole = "buyer" | "seller" | "admin";
export type ShoppingSectionSlug = "male" | "female" | "special_gifts";

export interface ShoppingSection {
  slug: ShoppingSectionSlug;
  name: string;
}

export const SHOPPING_SECTIONS: ShoppingSection[] = [
  { slug: "male", name: "Male" },
  { slug: "female", name: "Female" },
  { slug: "special_gifts", name: "Special Gifts" },
];

export interface User {
  id: number;
  full_name: string;
  email: string;
  phone_number: string;
  role: UserRole;
  is_email_verified: boolean;
  created_at: string;
}

export interface Product {
  id: number;
  name: string;
  description: string | null;
  price: string | number;
  stock: number;
  low_stock_threshold: number;
  image_url: string | null;
  is_active: boolean;
  category_id: number | null;
  sections: ShoppingSection[];
  seller_id: number | null;
  created_at: string;
  updated_at: string;
  offer_discount_type: "fixed" | "percentage" | null;
  offer_discount_value: string | number | null;
  offer_starts_at: string | null;
  offer_ends_at: string | null;
  offer_is_active: boolean;
  offer_active: boolean;
  offer_price: string | number | null;
  discount_percentage: string | number | null;
}

export interface ProductImage {
  id: number;
  product_id: number;
  image_url: string;
  is_primary: boolean;
  created_at: string;
}

export interface ProductRecommendations {
  recommended: Product[];
  popular: Product[];
  is_personalized: boolean;
}

export interface ProductQuestion {
  id: number;
  product_id: number;
  product_name: string;
  buyer_name: string;
  question: string;
  answer: string | null;
  created_at: string;
  answered_at: string | null;
}

export interface CartLine {
  product_id: number;
  product_name: string;
  unit_price: string | number;
  quantity: number;
  stock: number;
  image_url: string | null;
  available: boolean;
  line_total: string | number;
}

export interface Cart {
  items: CartLine[];
  total: string | number;
}

export interface OrderItem {
  id: number;
  product_id: number | null;
  product_name: string;
  unit_price: string | number;
  quantity: number;
  line_total: string | number;
  fulfillment_status?: FulfillmentStatus;
}

export type FulfillmentStatus = "processing" | "packed" | "shipped" | "delivered";

export interface SellerOrderItem {
  id: number;
  product_id: number | null;
  product_name: string;
  unit_price: string | number;
  quantity: number;
  line_total: string | number;
  fulfillment_status: FulfillmentStatus;
}

export interface SellerOrder {
  id: number;
  status: OrderStatus;
  payment_method: string;
  payment_status: string;
  delivery_name: string;
  delivery_phone: string;
  address_line: string;
  city: string;
  state: string;
  postal_code: string;
  seller_subtotal: string | number;
  created_at: string;
  items: SellerOrderItem[];
}

export interface Order {
  id: number;
  status: OrderStatus;
  payment_method: string;
  payment_status: string;
  razorpay_order_id: string | null;
  razorpay_payment_id: string | null;
  delivery_name: string;
  delivery_phone: string;
  address_line: string;
  city: string;
  state: string;
  postal_code: string;
  coupon_code: string | null;
  discount_description: string | null;
  delivery_method: "home_delivery" | "campus_pickup";
  pickup_location_id: number | null;
  pickup_location_name: string | null;
  pickup_status: "not_applicable" | "awaiting_pickup" | "ready" | "collected";
  subtotal: string | number;
  discount_amount: string | number;
  shipping_fee: string | number;
  estimated_delivery_at: string | null;
  courier_name: string | null;
  tracking_id: string | null;
  total: string | number;
  created_at: string;
  items: OrderItem[];
}

export interface PickupLocation {
  id: number;
  name: string;
  address_line: string;
  city: string;
  state: string;
  postal_code: string;
  instructions: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PickupLocationInput {
  name: string;
  address_line: string;
  city: string;
  state: string;
  postal_code: string;
  instructions: string | null;
  is_active: boolean;
}

export type CouponDiscountType = "fixed" | "percentage";

export interface Coupon {
  id: number;
  code: string;
  discount_type: CouponDiscountType;
  discount_value: string | number;
  minimum_order_amount: string | number;
  maximum_discount: string | number | null;
  usage_limit: number | null;
  used_count: number;
  starts_at: string | null;
  ends_at: string | null;
  is_active: boolean;
  created_at: string;
}

export interface CouponInput {
  code: string;
  discount_type: CouponDiscountType;
  discount_value: number;
  minimum_order_amount: number;
  maximum_discount: number | null;
  usage_limit: number | null;
  starts_at: string | null;
  ends_at: string | null;
  is_active: boolean;
}

export interface CouponQuote {
  code: string;
  discount_type: CouponDiscountType;
  discount_value: string | number;
  subtotal: string | number;
  discount_amount: string | number;
  total: string | number;
}

export interface RazorpayPaymentStart {
  key_id: string;
  razorpay_order_id: string;
  amount: number;
  currency: string;
  order: Order;
}

export type ReturnType = "return" | "refund";
export type ReturnStatus = "pending" | "approved" | "rejected";
export type RefundStatus = "pending" | "processing" | "refunded" | "failed" | "not_applicable";

export interface ReturnRequest {
  id: number;
  order_id: number;
  request_type: ReturnType;
  reason: string;
  status: ReturnStatus;
  refund_status: RefundStatus;
  review_note: string | null;
  order_status: string;
  order_total: string | number;
  payment_method: string;
  created_at: string;
  reviewed_at: string | null;
  refund_updated_at: string | null;
}

export interface AdminReturnRequest extends ReturnRequest {
  buyer_id: number;
  buyer_name: string;
  buyer_email: string;
}

export interface BuyAgainProduct {
  product_id: number | null;
  product_name: string;
  price: string | number;
  image_url: string | null;
  stock: number;
  available: boolean;
  unavailable_reason: string | null;
  last_ordered_at: string;
  last_quantity: number;
}

export interface SellerDashboardOrder {
  id: number;
  status: OrderStatus;
  created_at: string;
  item_count: number;
  subtotal: string | number;
  products: string[];
}

export interface SellerDashboard {
  total_products: number;
  total_orders: number;
  total_sales: number;
  total_revenue: string | number;
  recent_orders: SellerDashboardOrder[];
}

export type PayoutStatus = "pending" | "processing" | "paid" | "failed";

export interface SellerEarnings {
  total_sales: number;
  gross_sales: string | number;
  earnings: string | number;
  eligible_earnings: string | number;
  pending_payments: string | number;
  available_for_payout: string | number;
}

export interface SellerPayout {
  id: number;
  seller_id: number;
  amount: string | number;
  status: PayoutStatus;
  reference: string | null;
  note: string | null;
  created_at: string;
  updated_at: string;
  paid_at: string | null;
}

export interface SellerPayoutHistory {
  earnings: SellerEarnings;
  payouts: SellerPayout[];
}

export interface AdminSellerEarnings extends SellerEarnings {
  seller_id: number;
  seller_name: string;
  seller_email: string;
}

export interface AdminPayout extends SellerPayout {
  seller_name: string;
  seller_email: string;
}

export interface AdminPayoutDashboard {
  sellers: AdminSellerEarnings[];
  payouts: AdminPayout[];
}

export interface AdminDailySummary {
  date: string;
  orders: number;
  registrations: number;
}

export interface AdminActivity {
  id: string;
  kind: "user" | "product" | "order" | "review" | "application";
  title: string;
  detail: string;
  created_at: string;
}

export interface AdminDashboard {
  total_users: number;
  buyers: number;
  sellers: number;
  total_products: number;
  total_orders: number;
  total_revenue: string | number;
  daily_summary: AdminDailySummary[];
  recent_activities: AdminActivity[];
}

export type OrderStatus = "placed" | "confirmed" | "shipped" | "delivered" | "cancelled";

export interface DeliveryAddress {
  delivery_name: string;
  delivery_phone: string;
  address_line: string;
  city: string;
  state: string;
  postal_code: string;
}

export interface SavedAddress {
  id: number;
  full_name: string;
  phone_number: string;
  address_line: string;
  city: string;
  state: string;
  pin_code: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export type SavedAddressInput = Omit<SavedAddress, "id" | "created_at" | "updated_at">;

export interface ProductReview {
  id: number;
  product_id: number;
  reviewer_name: string;
  rating: number;
  body: string;
  created_at: string;
  updated_at: string;
}

export interface ProductReviewSummary {
  average_rating: string | number | null;
  review_count: number;
  reviews: ProductReview[];
}

export interface ProductReviewInput {
  rating: number;
  body: string;
}

export interface Category {
  id: number;
  name: string;
  description: string | null;
  parent_id: number | null;
}

export interface CategoryTree extends Category {
  children: CategoryTree[];
}

export interface SellerApplication {
  id: number;
  user_id: number;
  message: string | null;
  status: "pending" | "approved" | "rejected";
  reviewed_by: number | null;
  review_note: string | null;
  created_at: string;
  reviewed_at: string | null;
}

export interface Notification {
  id: number;
  kind: string;
  title: string;
  message: string;
  link: string | null;
  is_read: boolean;
  created_at: string;
}

export interface NotificationSummary {
  unread_count: number;
  notifications: Notification[];
}

export type ConversationStatus = "open" | "closed";
export interface ConversationMessage {
  id: number;
  sender_id: number;
  sender_name: string;
  body: string;
  is_read: boolean;
  created_at: string;
}
export interface Conversation {
  id: number;
  product_id: number;
  product_name: string;
  product_image_url: string | null;
  buyer_id: number;
  buyer_name: string;
  seller_id: number;
  seller_name: string;
  other_party_name: string;
  status: ConversationStatus;
  last_message: string | null;
  updated_at: string;
  unread_count: number;
}
export interface ConversationDetail extends Conversation { messages: ConversationMessage[]; }

export interface ProductInput {
  name: string;
  description: string | null;
  price: number;
  stock: number;
  low_stock_threshold: number;
  image_url: string | null;
  category_id: number | null;
  section_slugs: ShoppingSectionSlug[];
}

export interface ProductOfferInput {
  discount_type: "fixed" | "percentage";
  discount_value: number;
  starts_at: string;
  ends_at: string;
  is_active: boolean;
}

export interface BundleComponentInput { product_id: number; quantity: number; }
export interface BundleComponent {
  product_id: number;
  product_name: string;
  image_url: string | null;
  quantity: number;
  unit_price: string | number;
  available_stock: number;
}
export interface ProductBundle {
  id: number;
  name: string;
  description: string | null;
  special_price: string | number;
  payable_price: string | number;
  original_price: string | number;
  discount_amount: string | number;
  discount_percentage: string | number;
  is_active: boolean;
  available: boolean;
  max_bundles: number;
  created_at: string;
  updated_at: string;
  items: BundleComponent[];
}
export interface ProductBundleInput {
  name: string;
  description: string | null;
  special_price: number;
  items: BundleComponentInput[];
  is_active: boolean;
}

export interface ShippingSettings {
  delivery_charge: string | number;
  estimated_delivery_days: number;
  updated_at: string | null;
}

export interface OrderShippingInput {
  estimated_delivery_at: string | null;
  courier_name: string | null;
  tracking_id: string | null;
}

export interface LowStockProduct {
  id: number;
  name: string;
  stock: number;
  low_stock_threshold: number;
  seller_id: number | null;
  seller_name: string | null;
  image_url: string | null;
}

export type SupportTicketCategory = "order" | "product" | "payment" | "account" | "other";
export type SupportTicketStatus = "open" | "in_progress" | "resolved" | "closed";

export interface SupportTicketMessage {
  id: number;
  sender_role: string;
  sender_name: string;
  body: string;
  created_at: string;
}

export interface SupportTicket {
  id: number;
  subject: string;
  category: SupportTicketCategory;
  description: string;
  status: SupportTicketStatus;
  created_at: string;
  updated_at: string;
}

export interface SupportTicketDetail extends SupportTicket {
  messages: SupportTicketMessage[];
}

export interface AdminSupportTicket extends SupportTicket {
  buyer_id: number;
  buyer_name: string;
  buyer_email: string;
}

export interface AdminSupportTicketDetail extends AdminSupportTicket {
  messages: SupportTicketMessage[];
}

export type ProductRequestStatus = "pending" | "responded";

export interface ProductRequest {
  id: number;
  product_name: string;
  quantity: number;
  photo_url: string | null;
  message: string;
  status: ProductRequestStatus;
  can_arrange: boolean | null;
  price: string | number | null;
  expected_delivery_days: number | null;
  admin_message: string | null;
  created_at: string;
  updated_at: string;
  responded_at: string | null;
}

export interface AdminProductRequest extends ProductRequest {
  buyer_id: number;
  buyer_name: string;
  buyer_email: string;
}

export interface CategoryInput {
  name: string;
  description: string | null;
  parent_id: number | null;
}
