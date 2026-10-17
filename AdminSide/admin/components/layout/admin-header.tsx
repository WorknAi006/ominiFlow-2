"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAdminAuth } from "../../lib/auth/context";
import { useTheme } from "../../lib/theme/context";
import {
  Search,
  Menu,
  Bell,
  Sun,
  Moon,
  LogOut,
  Building2,
  Users,
  Layers,
  MessageSquare,
  Activity,
  Shield,
  FileText,
  Settings,
  CheckCircle2,
  X,
  ExternalLink,
} from "lucide-react";

interface SearchResult {
  title: string;
  category: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const searchableItems: SearchResult[] = [
  { title: "Dashboard Overview", category: "Navigation", href: "/admin/dashboard", icon: Activity },
  { title: "Manage Tenants", category: "Organization", href: "/admin/tenants", icon: Building2 },
  { title: "User Directory", category: "Organization", href: "/admin/users", icon: Users },
  { title: "Connected Channels (WhatsApp, IG, FB)", category: "Channels", href: "/admin/channels", icon: Layers },
  { title: "Platform Conversations", category: "Messaging", href: "/admin/conversations", icon: MessageSquare },
  { title: "System Health & Engine Services", category: "Infrastructure", href: "/admin/system-health", icon: Activity },
  { title: "Security Center & Threat Monitoring", category: "Governance", href: "/admin/security", icon: Shield },
  { title: "Audit Trail Logs", category: "Governance", href: "/admin/audit-logs", icon: FileText },
  { title: "Platform Settings", category: "System", href: "/admin/settings", icon: Settings },
];

export function AdminHeader({
  collapsed,
  setMobileOpen,
}: {
  collapsed: boolean;
  setMobileOpen?: (o: boolean) => void;
}) {
  const router = useRouter();
  const { user, logout } = useAdminAuth();
  const { theme, toggleTheme } = useTheme();

  // Search Palette State
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Notifications State
  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(1);
  const notifRef = useRef<HTMLDivElement>(null);

  // Global Command+K Keyboard Shortcut Listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setIsSearchOpen((prev) => !prev);
      } else if (e.key === "Escape") {
        setIsSearchOpen(false);
        setIsNotifOpen(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Focus search input when modal opens
  useEffect(() => {
    if (isSearchOpen) {
      setTimeout(() => searchInputRef.current?.focus(), 50);
    }
  }, [isSearchOpen]);

  // Close notifications when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setIsNotifOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filteredItems = searchableItems.filter(
    (item) =>
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <>
      <header className="h-16 border-b border-slate-800/80 bg-[#070c18]/90 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-20">
        {/* Left Search Bar Trigger */}
        <div className="flex items-center gap-3 flex-1 max-w-xl">
          <button
            onClick={() => setMobileOpen && setMobileOpen(true)}
            className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800/60 md:hidden"
          >
            <Menu className="w-5 h-5" />
          </button>

          <button
            onClick={() => setIsSearchOpen(true)}
            className="relative flex items-center w-full max-w-md bg-[#0d1527] hover:bg-[#101b33] border border-slate-800/90 hover:border-slate-700 text-left text-xs rounded-lg pl-9 pr-10 py-2 transition-all cursor-pointer group shadow-inner"
          >
            <Search className="w-4 h-4 text-slate-500 group-hover:text-sky-400 absolute left-3 transition-colors" />
            <span className="text-slate-500 group-hover:text-slate-300 transition-colors truncate">
              Search tenants, users, channels, conversations...
            </span>
            <div className="absolute right-2.5 flex items-center">
              <kbd className="text-[10px] font-mono bg-slate-800/90 text-slate-400 px-1.5 py-0.5 rounded border border-slate-700/80 group-hover:border-sky-500/40 group-hover:text-sky-400 transition-colors">
                ⌘K
              </kbd>
            </div>
          </button>
        </div>

        {/* Right Controls */}
        <div className="flex items-center gap-3">
          {/* Notifications with interactive Dropdown */}
          <div className="relative" ref={notifRef}>
            <button
              onClick={() => setIsNotifOpen(!isNotifOpen)}
              className="relative p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors cursor-pointer"
              title="Notifications"
            >
              <Bell className="w-4 h-4" />
              {unreadCount > 0 && (
                <span className="absolute top-1 right-1 w-4 h-4 bg-rose-500 text-white rounded-full text-[9px] font-bold flex items-center justify-center animate-pulse">
                  {unreadCount}
                </span>
              )}
            </button>

            {/* Notification Popover */}
            {isNotifOpen && (
              <div className="absolute right-0 top-11 w-80 bg-[#0d1527] border border-slate-800 rounded-2xl shadow-2xl overflow-hidden z-50 animate-in fade-in zoom-in-95 duration-100">
                <div className="p-3.5 border-b border-slate-800/80 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-white">System Notifications</span>
                    {unreadCount > 0 && (
                      <span className="px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-400 text-[10px] font-semibold">
                        {unreadCount} new
                      </span>
                    )}
                  </div>
                  {unreadCount > 0 && (
                    <button
                      onClick={() => setUnreadCount(0)}
                      className="text-[10px] text-sky-400 hover:text-sky-300 font-medium cursor-pointer"
                    >
                      Mark all as read
                    </button>
                  )}
                </div>

                <div className="divide-y divide-slate-800/60 max-h-72 overflow-y-auto">
                  <div className="p-3 hover:bg-slate-800/30 transition-colors">
                    <div className="flex items-start gap-2.5">
                      <div className="w-6 h-6 rounded-full bg-emerald-500/15 text-emerald-400 flex items-center justify-center shrink-0 mt-0.5">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                      </div>
                      <div>
                        <p className="text-xs font-medium text-white">Core Backend Online</p>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                          FastAPI ASGI workers and PostgreSQL 16 connection pool verified healthy.
                        </p>
                        <span className="text-[9px] text-slate-500 mt-1 block">Just now</span>
                      </div>
                    </div>
                  </div>

                  <div className="p-3 hover:bg-slate-800/30 transition-colors">
                    <div className="flex items-start gap-2.5">
                      <div className="w-6 h-6 rounded-full bg-sky-500/15 text-sky-400 flex items-center justify-center shrink-0 mt-0.5">
                        <Shield className="w-3.5 h-3.5" />
                      </div>
                      <div>
                        <p className="text-xs font-medium text-white">Super Admin Session Verified</p>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                          Authenticated as platform administrator on control plane.
                        </p>
                        <span className="text-[9px] text-slate-500 mt-1 block">5m ago</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="p-2.5 bg-[#090f20] border-t border-slate-800/80 text-center">
                  <Link
                    href="/admin/system-health"
                    onClick={() => setIsNotifOpen(false)}
                    className="text-[11px] text-sky-400 hover:text-sky-300 font-medium"
                  >
                    View System Health & Logs →
                  </Link>
                </div>
              </div>
            )}
          </div>

          {/* Real Light / Dark Mode Toggle Button */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors cursor-pointer"
            title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
          >
            {theme === "dark" ? (
              <Sun className="w-4 h-4 text-amber-300 hover:text-amber-200 transition-colors" />
            ) : (
              <Moon className="w-4 h-4 text-sky-600 hover:text-sky-500 transition-colors" />
            )}
          </button>

          {/* Admin Profile */}
          <div className="flex items-center gap-2.5 pl-2">
            <div className="w-8 h-8 rounded-full bg-sky-600 text-white flex items-center justify-center text-xs font-bold border border-sky-400/30 shadow-sm shadow-sky-500/20">
              {user?.first_name ? user.first_name[0].toUpperCase() : "P"}
            </div>
            <div className="hidden lg:flex flex-col text-left">
              <span className="text-xs font-semibold text-white leading-tight">
                {user ? `${user.first_name} ${user.last_name || ""}`.trim() : "Platform Admin"}
              </span>
              <span className="text-[10px] text-slate-400 font-medium leading-tight">
                Super Administrator
              </span>
            </div>
            <button
              onClick={logout}
              title="Sign Out"
              className="hidden sm:flex ml-1 p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors cursor-pointer"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Global Interactive Command+K Search Modal */}
      {isSearchOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 px-4 bg-black/70 backdrop-blur-xs animate-in fade-in duration-150">
          <div
            className="relative w-full max-w-xl bg-[#0b1325] border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-150"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Input */}
            <div className="flex items-center px-4 py-3 border-b border-slate-800 bg-[#0e172e]">
              <Search className="w-5 h-5 text-sky-400 mr-3" />
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search across tenants, channels, users, settings..."
                className="flex-1 bg-transparent text-sm text-white placeholder-slate-500 outline-none"
              />
              <button
                onClick={() => setIsSearchOpen(false)}
                className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Results List */}
            <div className="max-h-80 overflow-y-auto p-2 space-y-1">
              {filteredItems.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-500">
                  No matching results found for &quot;{searchQuery}&quot;
                </div>
              ) : (
                filteredItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <button
                      key={item.href}
                      onClick={() => {
                        setIsSearchOpen(false);
                        router.push(item.href);
                      }}
                      className="w-full flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-sky-600/15 hover:border-sky-500/30 border border-transparent text-left transition-colors group cursor-pointer"
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-slate-800/80 group-hover:bg-sky-500/20 text-slate-400 group-hover:text-sky-400 transition-colors">
                          <Icon className="w-4 h-4" />
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-white group-hover:text-sky-300">
                            {item.title}
                          </p>
                          <p className="text-[10px] text-slate-500">{item.category}</p>
                        </div>
                      </div>
                      <ExternalLink className="w-3.5 h-3.5 text-slate-600 group-hover:text-sky-400" />
                    </button>
                  );
                })
              )}
            </div>

            {/* Footer */}
            <div className="px-4 py-2 border-t border-slate-800/80 bg-[#090f20] flex items-center justify-between text-[11px] text-slate-500">
              <span>Navigate with mouse or keyboard</span>
              <span className="font-mono text-[10px]">ESC to close</span>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
