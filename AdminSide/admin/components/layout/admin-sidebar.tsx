"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Activity,
  Building2,
  Users,
  Layers,
  MessageSquare,
  BarChart3,
  Gem,
  CreditCard,
  Shield,
  FileText,
  Webhook,
  Wrench,
  Settings,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

const navSections: Array<{ title: string; items: NavItem[] }> = [
  {
    title: "OVERVIEW",
    items: [
      { name: "Dashboard", href: "/admin/dashboard", icon: LayoutDashboard },
      { name: "System Health", href: "/admin/system-health", icon: Activity },
    ],
  },
  {
    title: "ORGANIZATION",
    items: [
      { name: "Tenants", href: "/admin/tenants", icon: Building2 },
      { name: "Users", href: "/admin/users", icon: Users },
      { name: "Channels", href: "/admin/channels", icon: Layers },
      { name: "Conversations", href: "/admin/conversations", icon: MessageSquare },
    ],
  },
  {
    title: "PLATFORM & BILLING",
    items: [
      { name: "API Usage", href: "/admin/api-usage", icon: BarChart3 },
      { name: "Plans", href: "/admin/plans", icon: Gem },
      { name: "Billing", href: "/admin/billing", icon: CreditCard },
    ],
  },
  {
    title: "GOVERNANCE & OPS",
    items: [
      { name: "Security Center", href: "/admin/security", icon: Shield },
      { name: "Audit Logs", href: "/admin/audit-logs", icon: FileText },
    ],
  },
  {
    title: "OPERATIONS",
    items: [
      { name: "Webhooks", href: "/admin/webhooks", icon: Webhook },
      { name: "Maintenance", href: "/admin/maintenance", icon: Wrench },
    ],
  },
  {
    title: "SYSTEM",
    items: [
      { name: "Settings", href: "/admin/settings", icon: Settings },
    ],
  },
];

export function AdminSidebar({
  collapsed,
  setCollapsed,
}: {
  collapsed: boolean;
  setCollapsed: (c: boolean) => void;
}) {
  const pathname = usePathname();

  return (
    <aside
      className={`fixed top-0 left-0 bottom-0 z-30 flex flex-col bg-[#070c18] border-r border-slate-800/80 transition-all duration-200 select-none ${
        collapsed ? "w-16" : "w-64"
      }`}
    >
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-slate-800/80 shrink-0">
        <Link href="/admin/dashboard" className="flex items-center gap-2.5 overflow-hidden">
          <div className="w-8 h-8 rounded-lg bg-sky-500/15 border border-sky-400/40 flex items-center justify-center text-sky-400 font-bold text-sm shrink-0 shadow-sm shadow-sky-500/20">
            Ω
          </div>
          {!collapsed && (
            <div className="flex flex-col">
              <div className="flex items-center">
                <span className="font-bold text-sm tracking-tight text-white">Omniflow</span>
              </div>
              <span className="text-[10px] text-slate-400 font-medium leading-tight">
                Platform Control Plane
              </span>
            </div>
          )}
        </Link>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="text-slate-500 hover:text-white p-1 rounded hover:bg-slate-800/60 text-xs hidden md:flex items-center justify-center"
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Navigation List - fits seamlessly without clipping */}
      <div className="flex-1 overflow-y-auto px-2.5 py-2 space-y-2.5 scrollbar-thin scrollbar-thumb-slate-800">
        {navSections.map((section, idx) => (
          <div key={idx} className="space-y-0.5">
            {!collapsed && (
              <h3 className="text-[9px] uppercase font-bold text-slate-500 px-2.5 tracking-wider mb-1 mt-1">
                {section.title}
              </h3>
            )}
            {section.items.map((item) => {
              const Icon = item.icon;
              const isActive =
                pathname === item.href ||
                (item.href !== "/dashboard" && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? "bg-sky-600/20 text-sky-400 border border-sky-500/30 shadow-sm shadow-sky-500/10"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
                  }`}
                  title={collapsed ? item.name : undefined}
                >
                  <Icon className={`w-4 h-4 shrink-0 ${isActive ? "text-sky-400" : "text-slate-400"}`} />
                  {!collapsed && <span className="truncate flex-1">{item.name}</span>}
                  {!collapsed && item.badge && (
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 border border-slate-700">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </div>
    </aside>
  );
}
