"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAdminAuth } from "../../lib/auth/context";
import { AdminSidebar } from "../../components/layout/admin-sidebar";
import { AdminHeader } from "../../components/layout/admin-header";

export default function AdminProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { user, loading } = useAdminAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (!loading) {
      if (!user) {
        router.replace("/login");
      } else if (!user.is_platform_admin) {
        router.replace("/unauthorized");
      }
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-[#070b14]">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-sky-500 border-t-transparent" />
          <p className="text-xs font-medium text-slate-400 tracking-wider uppercase">
            Verifying Admin Authorization...
          </p>
        </div>
      </div>
    );
  }

  if (!user || !user.is_platform_admin) {
    return null;
  }

  return (
    <div className="min-h-screen bg-[#070b14] flex">
      {/* Sidebar */}
      <div className={`hidden md:block ${collapsed ? "w-16" : "w-64"} shrink-0 transition-all duration-200`}>
        <AdminSidebar collapsed={collapsed} setCollapsed={setCollapsed} />
      </div>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          <div className="fixed inset-0 bg-black/60 backdrop-blur-xs" onClick={() => setMobileOpen(false)} />
          <div className="relative z-10 w-64 h-full">
            <AdminSidebar collapsed={false} setCollapsed={() => setMobileOpen(false)} />
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <AdminHeader collapsed={collapsed} setMobileOpen={setMobileOpen} />
        <main className="flex-1 p-5 md:p-6 w-full">
          {children}
        </main>
      </div>
    </div>
  );
}
