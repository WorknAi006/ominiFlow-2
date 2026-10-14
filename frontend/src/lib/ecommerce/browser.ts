export type EcommerceOverview = {
  total_products: number;
  total_orders: number;
  pending_orders: number;
  total_revenue: number;
};

export type Product = {
  id: string;
  name: string;
  sku: string | null;
  description: string | null;
  price: number;
  currency: string;
  is_available: boolean;
  created_at: string;
  updated_at: string;
};

export type ProductList = {
  items: Product[];
  total: number;
};

export type OrderItem = {
  id: string;
  product_id: string | null;
  quantity: number;
  unit_price: number;
  total_price: number;
};

export type Order = {
  id: string;
  contact_id: string | null;
  order_number: string;
  status: string;
  currency: string;
  total_amount: number;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
};

export type OrderList = {
  items: Order[];
  total: number;
};

export async function fetchEcommerceOverview(): Promise<EcommerceOverview> {
  const response = await fetch("/api/ecommerce/overview", {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || "Failed to load overview.");
  }
  return payload;
}

export async function fetchProducts(skip: number = 0, limit: number = 100, search?: string): Promise<ProductList> {
  const params = new URLSearchParams({ skip: skip.toString(), limit: limit.toString() });
  if (search) params.append("search", search);
  
  const response = await fetch(`/api/ecommerce/products?${params.toString()}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || "Failed to load products.");
  }
  return payload;
}

export async function fetchOrders(skip: number = 0, limit: number = 100, search?: string): Promise<OrderList> {
  const params = new URLSearchParams({ skip: skip.toString(), limit: limit.toString() });
  if (search) params.append("search", search);
  
  const response = await fetch(`/api/ecommerce/orders?${params.toString()}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || "Failed to load orders.");
  }
  return payload;
}

export async function updateOrderStatus(orderId: string, status: string): Promise<Order> {
  const response = await fetch(`/api/ecommerce/orders/${orderId}`, {
    method: "PATCH",
    headers: { 
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ status }),
    cache: "no-store",
  });
  
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || "Failed to update order status.");
  }
  return payload;
}
