"use client";

import Link from "next/link";
import { useEcommerce } from "./use-ecommerce";

const ChevronLeftIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polyline points="15 18 9 12 15 6" /></svg>);

// Icons
const ZapIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>);
const SettingsIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" /><circle cx="12" cy="12" r="3" /></svg>);
const StoreIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><polyline points="9 22 9 12 15 12 15 22" /></svg>);
const BoxIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><polyline points="3.27 6.96 12 12.01 20.73 6.96" /><line x1="12" y1="22.08" x2="12" y2="12" /></svg>);
const BagIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" /><line x1="3" y1="6" x2="21" y2="6" /><path d="M16 10a4 4 0 0 1-8 0" /></svg>);
const CreditCardIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><rect x="1" y="4" width="22" height="16" rx="2" ry="2" /><line x1="1" y1="10" x2="23" y2="10" /></svg>);
const SlidersIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><line x1="4" y1="21" x2="4" y2="14" /><line x1="4" y1="10" x2="4" y2="3" /><line x1="12" y1="21" x2="12" y2="12" /><line x1="12" y1="8" x2="12" y2="3" /><line x1="20" y1="21" x2="20" y2="16" /><line x1="20" y1="12" x2="20" y2="3" /><line x1="1" y1="14" x2="7" y2="14" /><line x1="9" y1="8" x2="15" y2="8" /><line x1="17" y1="16" x2="23" y2="16" /></svg>);
const GridIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /></svg>);

export function EcommerceClient() {
  const {
    activeMenu,
    setActiveMenu,
    overview,
    products,
    orders,
    isLoading,
    error,
    handleUpdateOrderStatus,
  } = useEcommerce();

  const menuItems = [
    { id: "Overview", title: "Overview", subtitle: "High-level view of your...", icon: StoreIcon },
    { id: "Products", title: "Products", subtitle: "Browse and manage...", icon: BoxIcon },
    { id: "Orders", title: "Orders", subtitle: "Track orders coming from...", icon: BagIcon },
    { id: "Payments", title: "Payments", subtitle: "Monitor payment status an...", icon: CreditCardIcon },
    { id: "Commerce Settings", title: "Commerce Settings", subtitle: "Configure e-commerce rul...", icon: SlidersIcon },
    { id: "Order Settings", title: "Order Settings", subtitle: "Configure order messages,...", icon: SettingsIcon },
  ];

  return (
    <div className="bg-[#f8f9fa] min-h-screen font-sans">
      <div className="p-8 mx-auto max-w-7xl">
        
        {/* Header */}
        <div className="flex justify-between items-start mb-8">
          <div>
            <h1 className="text-[26px] font-bold text-slate-800 leading-tight">E-commerce</h1>
            <p className="text-[15px] text-slate-500 mt-0.5">Manage your WhatsApp storefront, products, orders and payments</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Main Content Area */}
        <div className="flex bg-white border border-slate-200 rounded-2xl min-h-[600px] overflow-hidden shadow-sm">
          
          {/* Left Menu Sidebar */}
          <div className="w-[300px] border-r border-slate-200 flex flex-col bg-white">
            <div className="p-5 flex items-center justify-between border-b border-transparent">
              <div>
                <h2 className="font-bold text-slate-900 text-lg">E-commerce</h2>
                <p className="text-sm text-slate-500">Internal Storefront Data</p>
              </div>
              <button className="text-slate-400 hover:text-slate-600">
                <ChevronLeftIcon className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 py-3 px-3 space-y-1">
              {menuItems.map((item) => {
                const isActive = activeMenu === item.id;
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveMenu(item.id)}
                    className={`w-full text-left flex items-start gap-4 px-4 py-3 rounded-xl transition-colors ${
                      isActive 
                        ? "bg-[#e8f5e9] text-[#00b050]" 
                        : "hover:bg-slate-50 text-slate-600"
                    }`}
                  >
                    <Icon className={`w-6 h-6 mt-0.5 ${isActive ? "text-[#00b050]" : "text-slate-400"}`} />
                    <div>
                      <div className={`font-bold text-[15px] ${isActive ? "text-[#00b050]" : "text-slate-700"}`}>
                        {item.title}
                      </div>
                      <div className={`text-[13px] ${isActive ? "text-[#2e7d32]/80" : "text-slate-400"}`}>
                        {item.subtitle}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Right Content */}
          <div className="flex-1 bg-white p-10 overflow-y-auto max-h-[800px]">
            {isLoading ? (
               <div className="flex justify-center items-center h-64 text-slate-400">Loading...</div>
            ) : (
              <>
                {activeMenu === "Overview" && (
                  <div className="max-w-3xl">
                    <div className="mb-10">
                      <h2 className="text-[26px] font-bold text-slate-900 mb-1">Ecommerce Overview</h2>
                      <p className="text-[17px] text-slate-500">High-level metrics for your storefront.</p>
                    </div>

                    <div className="grid grid-cols-2 gap-6 mb-10">
                      <div className="border border-slate-200 rounded-2xl p-6 shadow-sm bg-white">
                        <div className="text-4xl font-black text-slate-900 mb-2">{overview?.total_products || 0}</div>
                        <div className="text-base font-bold text-slate-800">Total Products</div>
                      </div>
                      <div className="border border-slate-200 rounded-2xl p-6 shadow-sm bg-white">
                        <div className="text-4xl font-black text-slate-900 mb-2">{overview?.total_orders || 0}</div>
                        <div className="text-base font-bold text-slate-800">Total Orders</div>
                      </div>
                      <div className="border border-slate-200 rounded-2xl p-6 shadow-sm bg-white">
                        <div className="text-4xl font-black text-slate-900 mb-2">{overview?.pending_orders || 0}</div>
                        <div className="text-base font-bold text-slate-800">Pending Orders</div>
                      </div>
                      <div className="border border-slate-200 rounded-2xl p-6 shadow-sm bg-white">
                        <div className="text-4xl font-black text-slate-900 mb-2">${(overview?.total_revenue || 0).toFixed(2)}</div>
                        <div className="text-base font-bold text-slate-800">Total Revenue</div>
                      </div>
                    </div>
                  </div>
                )}

                {activeMenu === "Products" && (
                  <div className="max-w-4xl">
                    <div className="mb-8 flex justify-between items-center">
                      <div>
                        <h2 className="text-[26px] font-bold text-slate-900 mb-1">Products</h2>
                        <p className="text-[17px] text-slate-500">Manage your product catalog ({products.total} total)</p>
                      </div>
                    </div>

                    {products.items.length === 0 ? (
                      <div className="text-slate-500 text-center py-12 border border-slate-200 rounded-xl">No products found.</div>
                    ) : (
                      <div className="overflow-hidden border border-slate-200 rounded-xl">
                        <table className="w-full text-left text-sm">
                          <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
                            <tr>
                              <th className="px-6 py-4 font-semibold">Product Name</th>
                              <th className="px-6 py-4 font-semibold">SKU</th>
                              <th className="px-6 py-4 font-semibold">Price</th>
                              <th className="px-6 py-4 font-semibold">Status</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-200">
                            {products.items.map(p => (
                              <tr key={p.id} className="hover:bg-slate-50">
                                <td className="px-6 py-4 font-medium text-slate-900">{p.name}</td>
                                <td className="px-6 py-4 text-slate-500">{p.sku || "-"}</td>
                                <td className="px-6 py-4 text-slate-900">${p.price.toFixed(2)} {p.currency}</td>
                                <td className="px-6 py-4">
                                  {p.is_available ? (
                                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">In Stock</span>
                                  ) : (
                                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">Out of Stock</span>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}

                {activeMenu === "Orders" && (
                  <div className="max-w-4xl">
                    <div className="mb-8 flex justify-between items-center">
                      <div>
                        <h2 className="text-[26px] font-bold text-slate-900 mb-1">Orders</h2>
                        <p className="text-[17px] text-slate-500">Track and manage orders ({orders.total} total)</p>
                      </div>
                    </div>

                    {orders.items.length === 0 ? (
                      <div className="text-slate-500 text-center py-12 border border-slate-200 rounded-xl">No orders found.</div>
                    ) : (
                      <div className="overflow-hidden border border-slate-200 rounded-xl">
                        <table className="w-full text-left text-sm">
                          <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
                            <tr>
                              <th className="px-6 py-4 font-semibold">Order Number</th>
                              <th className="px-6 py-4 font-semibold">Date</th>
                              <th className="px-6 py-4 font-semibold">Total</th>
                              <th className="px-6 py-4 font-semibold">Status</th>
                              <th className="px-6 py-4 font-semibold">Actions</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-200">
                            {orders.items.map(o => (
                              <tr key={o.id} className="hover:bg-slate-50">
                                <td className="px-6 py-4 font-medium text-slate-900">{o.order_number}</td>
                                <td className="px-6 py-4 text-slate-500">{new Date(o.created_at).toLocaleDateString()}</td>
                                <td className="px-6 py-4 text-slate-900">${o.total_amount.toFixed(2)} {o.currency}</td>
                                <td className="px-6 py-4">
                                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 capitalize">
                                    {o.status.replace("_", " ")}
                                  </span>
                                </td>
                                <td className="px-6 py-4">
                                  <select 
                                    className="text-sm border-slate-300 rounded-md shadow-sm"
                                    value={o.status}
                                    onChange={(e) => handleUpdateOrderStatus(o.id, e.target.value)}
                                  >
                                    <option value="pending">Pending</option>
                                    <option value="processing">Processing</option>
                                    <option value="shipped">Shipped</option>
                                    <option value="delivered">Delivered</option>
                                    <option value="cancelled">Cancelled</option>
                                  </select>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}

                {/* Dummy content for other tabs */}
                {!["Overview", "Products", "Orders"].includes(activeMenu) && (
                  <div className="h-full flex flex-col items-center justify-center text-center pb-20">
                    <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4">
                      <SettingsIcon className="w-8 h-8 text-slate-300" />
                    </div>
                    <h3 className="text-xl font-bold text-slate-700 mb-2">{activeMenu} Module</h3>
                    <p className="text-slate-500 max-w-sm">This section is currently under development or not selected in the provided mockups.</p>
                  </div>
                )}
              </>
            )}
          </div>
          
        </div>
      </div>
    </div>
  );
}
