export type UserRole = "buyer" | "seller" | "admin";

export interface User {
  id: number;
  full_name: string;
  email: string;
  phone_number: string;
  role: UserRole;
  created_at: string;
}

export interface Product {
  id: number;
  name: string;
  description: string | null;
  price: string | number;
  stock: number;
  image_url: string | null;
  is_active: boolean;
  category_id: number | null;
  created_at: string;
  updated_at: string;
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

export interface ProductInput {
  name: string;
  description: string | null;
  price: number;
  stock: number;
  image_url: string | null;
  category_id: number | null;
}

export interface CategoryInput {
  name: string;
  description: string | null;
  parent_id: number | null;
}
