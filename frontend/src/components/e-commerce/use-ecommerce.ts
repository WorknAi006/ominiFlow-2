import { useState, useEffect } from "react";
import { 
  EcommerceOverview, 
  ProductList, 
  OrderList, 
  fetchEcommerceOverview, 
  fetchProducts, 
  fetchOrders,
  updateOrderStatus
} from "@/lib/ecommerce/browser";

export function useEcommerce() {
  const [overview, setOverview] = useState<EcommerceOverview | null>(null);
  const [products, setProducts] = useState<ProductList>({ items: [], total: 0 });
  const [orders, setOrders] = useState<OrderList>({ items: [], total: 0 });
  
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [activeMenu, setActiveMenu] = useState("Overview");
  
  const loadOverview = async () => {
    try {
      const data = await fetchEcommerceOverview();
      setOverview(data);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const loadProducts = async () => {
    try {
      const data = await fetchProducts();
      setProducts(data);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const loadOrders = async () => {
    try {
      const data = await fetchOrders();
      setOrders(data);
    } catch (e: any) {
      setError(e.message);
    }
  };

  useEffect(() => {
    let mounted = true;
    
    setIsLoading(true);
    setError(null);
    
    const loadAll = async () => {
      try {
        if (activeMenu === "Overview") await loadOverview();
        else if (activeMenu === "Products") await loadProducts();
        else if (activeMenu === "Orders") await loadOrders();
      } catch (e: any) {
        if (mounted) setError(e.message);
      } finally {
        if (mounted) setIsLoading(false);
      }
    };
    
    loadAll();

    return () => { mounted = false; };
  }, [activeMenu]);

  const handleUpdateOrderStatus = async (orderId: string, status: string) => {
    try {
      await updateOrderStatus(orderId, status);
      await loadOrders(); // Refresh orders after update
    } catch (e: any) {
      setError(e.message);
    }
  };

  return {
    activeMenu,
    setActiveMenu,
    overview,
    products,
    orders,
    isLoading,
    error,
    handleUpdateOrderStatus,
  };
}
