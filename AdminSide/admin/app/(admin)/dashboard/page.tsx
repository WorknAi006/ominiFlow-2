"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { adminApi } from "../../../lib/api/admin-client";
import { AdminDashboardStats } from "../../../lib/types/admin";
import {
  WhatsAppLogo,
  InstagramLogo,
  MessengerLogo,
  WebChatLogo,
} from "../../../components/icons/channel-logos";
import {
  Building2,
  Users,
  Layers,
  MessageSquare,
  Zap,
  Database,
  Box,
  HelpCircle,
  Calendar,
  BarChart3,
  ChevronRight,
} from "lucide-react";

export default function AdminDashboardPage() {
  const [stats, setStats] = useState<AdminDashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState({ date: "", time: "" });

  // Live ticking date and time formatted exactly as shown in reference
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const dateStr = now.toLocaleDateString("en-US", {
        weekday: "long",
        month: "short",
        day: "numeric",
        year: "numeric",
      });
      const timeStr = now.toLocaleTimeString("en-US", {
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
      });
      setCurrentTime({ date: dateStr, time: timeStr });
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const fetchStats = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await adminApi.getDashboard();
      setStats(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard metrics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  // Compute 7 days labels for the usage chart
  const last7Days = Array.from({ length: 7 }).map((_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (6 - i));
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  });

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="flex justify-between items-center">
          <div className="space-y-2">
            <div className="h-7 w-56 bg-slate-800 rounded-lg" />
            <div className="h-4 w-96 bg-slate-800/60 rounded" />
          </div>
          <div className="h-14 w-48 bg-slate-800 rounded-xl" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-36 bg-[#0a1222] border border-slate-800 rounded-2xl" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300">
        <h3 className="font-semibold text-sm mb-1">Failed to load platform stats</h3>
        <p className="text-xs mb-4">{error}</p>
        <button
          onClick={fetchStats}
          className="px-3.5 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-5 w-full">
      {/* 1. Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Platform Overview</h1>
          <p className="text-xs text-slate-400 mt-1">
            Monitor and manage your entire Omniflow platform from one place.
          </p>
        </div>

        {/* Date and Time Card */}
        <div className="flex items-center gap-3 bg-[#0c1424] border border-slate-800/90 rounded-xl px-4 py-2 self-start sm:self-auto shadow-sm">
          <Calendar className="w-4 h-4 text-slate-400" />
          <div className="flex flex-col text-right">
            <span className="text-[11px] text-slate-400 font-medium">
              {currentTime.date || "Monday, Oct 8, 2026"}
            </span>
            <span className="text-base font-bold text-white tracking-tight leading-none mt-0.5">
              {currentTime.time || "12:53 PM"}
            </span>
          </div>
        </div>
      </div>

      {/* 2. Top KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {/* Total Tenants */}
        <Link
          href="/tenants"
          className="group relative overflow-hidden bg-[#0a1222] hover:bg-[#0c162a] border border-slate-800/90 hover:border-sky-500/40 rounded-2xl p-4.5 shadow-sm transition-all block"
        >
          <Building2 className="w-20 h-20 text-slate-800/25 absolute right-2 top-2 pointer-events-none group-hover:scale-105 transition-transform" />
          <div className="flex items-start gap-3.5">
            <div className="w-11 h-11 rounded-xl bg-sky-500/15 border border-sky-500/30 text-sky-400 flex items-center justify-center shrink-0 shadow-sm shadow-sky-500/10">
              <Building2 className="w-5 h-5" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300">
                <span>Total Tenants</span>
                <HelpCircle className="w-3.5 h-3.5 text-slate-500" />
              </div>
              <div className="text-3xl font-bold text-white tracking-tight mt-1">
                {stats.total_tenants}
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5 truncate">
                Organizations using Omniflow
              </p>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800/80 text-[11px] text-slate-400 flex items-center gap-1.5 font-medium">
            <span>{stats.active_tenants} active</span>
            <span>•</span>
            <span>{stats.suspended_tenants} suspended</span>
            <span>•</span>
            <span>0 trial</span>
          </div>
        </Link>

        {/* Global Users */}
        <Link
          href="/users"
          className="group relative overflow-hidden bg-[#0a1222] hover:bg-[#0c162a] border border-slate-800/90 hover:border-purple-500/40 rounded-2xl p-4.5 shadow-sm transition-all block"
        >
          <Users className="w-20 h-20 text-slate-800/25 absolute right-2 top-2 pointer-events-none group-hover:scale-105 transition-transform" />
          <div className="flex items-start gap-3.5">
            <div className="w-11 h-11 rounded-xl bg-purple-500/15 border border-purple-500/30 text-purple-400 flex items-center justify-center shrink-0 shadow-sm shadow-purple-500/10">
              <Users className="w-5 h-5" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300">
                <span>Global Users</span>
                <HelpCircle className="w-3.5 h-3.5 text-slate-500" />
              </div>
              <div className="text-3xl font-bold text-white tracking-tight mt-1">
                {stats.total_users}
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5 truncate">
                All user accounts across tenants
              </p>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800/80 text-[11px] text-slate-400 flex items-center gap-1.5 font-medium">
            <span className="text-emerald-400 font-bold">●</span>
            <span className="text-emerald-400 font-semibold">{stats.total_users} active</span>
            <span>•</span>
            <span>0 inactive</span>
          </div>
        </Link>

        {/* Connected Channels */}
        <Link
          href="/channels"
          className="group relative overflow-hidden bg-[#0a1222] hover:bg-[#0c162a] border border-slate-800/90 hover:border-emerald-500/40 rounded-2xl p-4.5 shadow-sm transition-all block"
        >
          <Layers className="w-20 h-20 text-slate-800/25 absolute right-2 top-2 pointer-events-none group-hover:scale-105 transition-transform" />
          <div className="flex items-start gap-3.5">
            <div className="w-11 h-11 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 flex items-center justify-center shrink-0 shadow-sm shadow-emerald-500/10">
              <Layers className="w-5 h-5" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300">
                <span>Connected Channels</span>
                <HelpCircle className="w-3.5 h-3.5 text-slate-500" />
              </div>
              <div className="text-3xl font-bold text-white tracking-tight mt-1">
                {stats.connected_channels}
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5 truncate">
                Live WhatsApp, Instagram, Facebook & Web Chat
              </p>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800/80 text-[11px] text-slate-400 flex items-center gap-1.5 font-medium">
            <span>{stats.connected_channels} connected</span>
            <span>•</span>
            <span>0 with issues</span>
          </div>
        </Link>

        {/* Processed Messages */}
        <Link
          href="/conversations"
          className="group relative overflow-hidden bg-[#0a1222] hover:bg-[#0c162a] border border-slate-800/90 hover:border-amber-500/40 rounded-2xl p-4.5 shadow-sm transition-all block"
        >
          <MessageSquare className="w-20 h-20 text-slate-800/25 absolute right-2 top-2 pointer-events-none group-hover:scale-105 transition-transform" />
          <div className="flex items-start gap-3.5">
            <div className="w-11 h-11 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-400 flex items-center justify-center shrink-0 shadow-sm shadow-amber-500/10">
              <MessageSquare className="w-5 h-5" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300">
                <span>Processed Messages</span>
                <HelpCircle className="w-3.5 h-3.5 text-slate-500" />
              </div>
              <div className="text-3xl font-bold text-white tracking-tight mt-1">
                {stats.total_messages}
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5 truncate">
                Total messages across all conversations
              </p>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800/80 text-[11px] text-slate-400 flex items-center gap-1.5 font-medium">
            <span>0 today</span>
            <span>•</span>
            <span>0 this week</span>
          </div>
        </Link>
      </div>

      {/* 3. Middle Section: System Services */}
      <div className="bg-[#0a1222] border border-slate-800/90 rounded-2xl p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-white">System Services</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Core platform infrastructure status and performance.
            </p>
          </div>
          <Link
            href="/system-health"
            className="text-xs text-sky-400 hover:text-sky-300 font-medium flex items-center gap-1"
          >
            <span>View All Services</span>
            <span>→</span>
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
          {/* FastAPI Application */}
          <Link
            href="/system-health"
            className="bg-[#0e172a]/70 hover:bg-[#121d36] border border-slate-800/90 hover:border-emerald-500/40 rounded-xl p-4 flex flex-col justify-between transition-all group"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="p-2 rounded-xl bg-emerald-500/15 text-emerald-400 shrink-0">
                  <Zap className="w-4 h-4" />
                </div>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-800/40 text-[10px] font-semibold text-emerald-400 shrink-0">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  Healthy
                </span>
              </div>
              <h3 className="text-xs font-bold text-white group-hover:text-emerald-400 transition-colors">
                FastAPI Application
              </h3>
              <p className="text-[11px] text-slate-400 mt-1 mb-3 leading-relaxed">
                Backend API services responding normally.
              </p>
            </div>
            <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
              <span className="text-slate-500">Runtime</span>
              <span className="font-mono text-slate-300 text-[10px] whitespace-nowrap">
                Python 3.13 / Uvicorn
              </span>
            </div>
          </Link>

          {/* PostgreSQL Database */}
          <Link
            href="/system-health"
            className="bg-[#0e172a]/70 hover:bg-[#121d36] border border-slate-800/90 hover:border-sky-500/40 rounded-xl p-4 flex flex-col justify-between transition-all group"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="p-2 rounded-xl bg-sky-500/15 text-sky-400 shrink-0">
                  <Database className="w-4 h-4" />
                </div>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-800/40 text-[10px] font-semibold text-emerald-400 shrink-0">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  Healthy
                </span>
              </div>
              <h3 className="text-xs font-bold text-white group-hover:text-sky-400 transition-colors">
                PostgreSQL Database
              </h3>
              <p className="text-[11px] text-slate-400 mt-1 mb-3 leading-relaxed">
                Database cluster is running and accessible.
              </p>
            </div>
            <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
              <span className="text-slate-500">Version</span>
              <span className="font-mono text-slate-300 text-[10px] whitespace-nowrap">
                PostgreSQL 16.15
              </span>
            </div>
          </Link>

          {/* Redis Broker */}
          <Link
            href="/system-health"
            className="bg-[#0e172a]/70 hover:bg-[#121d36] border border-slate-800/90 hover:border-indigo-500/40 rounded-xl p-4 flex flex-col justify-between transition-all group"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="p-2 rounded-xl bg-indigo-500/15 text-indigo-400 shrink-0">
                  <Box className="w-4 h-4" />
                </div>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-800/40 text-[10px] font-semibold text-emerald-400 shrink-0">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  Healthy
                </span>
              </div>
              <h3 className="text-xs font-bold text-white group-hover:text-indigo-400 transition-colors">
                Redis Broker
              </h3>
              <p className="text-[11px] text-slate-400 mt-1 mb-3 leading-relaxed">
                Message broker and cache operational.
              </p>
            </div>
            <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
              <span className="text-slate-500">Version</span>
              <span className="font-mono text-slate-300 text-[10px] whitespace-nowrap">
                Redis 8.10 (MSYS2)
              </span>
            </div>
          </Link>
        </div>
      </div>

      {/* 4. Bottom Section: Usage Chart, Channel Status & Tenant Distribution */}
      <div className="grid grid-cols-12 gap-4">
        {/* Col 1: Platform Usage (Last 7 days) */}
        <div className="col-span-12 xl:col-span-5 bg-[#0a1222] border border-slate-800/90 rounded-2xl p-5 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
            <div>
              <h2 className="text-sm font-semibold text-white">
                Platform Usage (Last 7 days)
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Messages and API requests across all channels.
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs shrink-0">
              <div className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-full bg-sky-500" />
                <span>Messages</span>
              </div>
              <div className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-full bg-purple-500" />
                <span>API Requests</span>
              </div>
            </div>
          </div>

          {/* Chart Canvas Area */}
          <div className="relative h-48 w-full flex flex-col justify-between pt-2">
            {/* Gridlines with Y axis labels */}
            {[200, 150, 100, 50, 0].map((val) => (
              <div key={val} className="flex items-center w-full gap-3">
                <span className="text-[10px] text-slate-500 font-mono w-6 text-right">
                  {val}
                </span>
                <div className="flex-1 border-b border-dashed border-slate-800/60" />
              </div>
            ))}

            {/* Centered Empty State */}
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center px-4 pointer-events-none">
              <div className="w-10 h-10 rounded-xl bg-slate-800/60 text-slate-400 flex items-center justify-center mb-2">
                <BarChart3 className="w-5 h-5" />
              </div>
              <p className="text-xs font-semibold text-white">No usage data yet</p>
              <p className="text-[11px] text-slate-400 max-w-xs mt-0.5 leading-relaxed">
                Message and API activity will appear here once tenants start using the platform.
              </p>
            </div>
          </div>

          {/* X Axis Dates */}
          <div className="flex justify-between pl-9 pr-2 mt-3 pt-2 border-t border-slate-800/60 text-[10px] text-slate-500 font-mono">
            {last7Days.map((d, i) => (
              <span key={i}>{d}</span>
            ))}
          </div>
        </div>

        {/* Col 2: Channel Status (100% Real Authentic Logos + Interactive Navigation) */}
        <div className="col-span-12 md:col-span-6 xl:col-span-4 bg-[#0a1222] border border-slate-800/90 rounded-2xl p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-0.5">
              <h2 className="text-sm font-semibold text-white">Channel Status</h2>
              <Link
                href="/channels"
                className="text-xs text-sky-400 hover:text-sky-300 font-medium flex items-center gap-1"
              >
                <span>Manage</span>
                <span>→</span>
              </Link>
            </div>
            <p className="text-xs text-slate-400 mb-3.5">
              Live status of connected communication channels.
            </p>

            <div className="space-y-2">
              {/* WhatsApp with Official Brand Logo */}
              <Link
                href="/channels"
                className="group flex items-center justify-between py-2 px-2.5 rounded-xl hover:bg-[#0e172e] border border-transparent hover:border-slate-800 transition-all cursor-pointer"
                title="Manage WhatsApp Channels"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-7 h-7 flex items-center justify-center shrink-0 drop-shadow-sm group-hover:scale-110 transition-transform">
                    <WhatsAppLogo className="w-6 h-6" />
                  </div>
                  <span className="text-xs font-semibold text-slate-200 group-hover:text-white transition-colors whitespace-nowrap">
                    WhatsApp
                  </span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-[#0e1628] border border-slate-800 text-slate-400 font-medium whitespace-nowrap group-hover:border-slate-700">
                    Not Connected
                  </span>
                  <span className="text-xs text-slate-400 flex items-center gap-0.5 font-mono group-hover:text-sky-400 transition-colors">
                    0 <ChevronRight className="w-3.5 h-3.5" />
                  </span>
                </div>
              </Link>

              {/* Instagram with Official Brand Logo */}
              <Link
                href="/channels"
                className="group flex items-center justify-between py-2 px-2.5 rounded-xl hover:bg-[#0e172e] border border-transparent hover:border-slate-800 transition-all cursor-pointer"
                title="Manage Instagram Channels"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-7 h-7 flex items-center justify-center shrink-0 drop-shadow-sm group-hover:scale-110 transition-transform">
                    <InstagramLogo className="w-6 h-6" />
                  </div>
                  <span className="text-xs font-semibold text-slate-200 group-hover:text-white transition-colors whitespace-nowrap">
                    Instagram
                  </span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-[#0e1628] border border-slate-800 text-slate-400 font-medium whitespace-nowrap group-hover:border-slate-700">
                    Not Connected
                  </span>
                  <span className="text-xs text-slate-400 flex items-center gap-0.5 font-mono group-hover:text-sky-400 transition-colors">
                    0 <ChevronRight className="w-3.5 h-3.5" />
                  </span>
                </div>
              </Link>

              {/* Facebook Messenger with Official Brand Logo */}
              <Link
                href="/channels"
                className="group flex items-center justify-between py-2 px-2.5 rounded-xl hover:bg-[#0e172e] border border-transparent hover:border-slate-800 transition-all cursor-pointer"
                title="Manage Facebook Messenger Channels"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-7 h-7 flex items-center justify-center shrink-0 drop-shadow-sm group-hover:scale-110 transition-transform">
                    <MessengerLogo className="w-6 h-6" />
                  </div>
                  <span className="text-xs font-semibold text-slate-200 group-hover:text-white transition-colors whitespace-nowrap">
                    Facebook Messenger
                  </span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-[#0e1628] border border-slate-800 text-slate-400 font-medium whitespace-nowrap group-hover:border-slate-700">
                    Not Connected
                  </span>
                  <span className="text-xs text-slate-400 flex items-center gap-0.5 font-mono group-hover:text-sky-400 transition-colors">
                    0 <ChevronRight className="w-3.5 h-3.5" />
                  </span>
                </div>
              </Link>

              {/* Web Chat with Official Brand Logo */}
              <Link
                href="/channels"
                className="group flex items-center justify-between py-2 px-2.5 rounded-xl hover:bg-[#0e172e] border border-transparent hover:border-slate-800 transition-all cursor-pointer"
                title="Manage Web Chat Channels"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-7 h-7 flex items-center justify-center shrink-0 drop-shadow-sm group-hover:scale-110 transition-transform">
                    <WebChatLogo className="w-6 h-6" />
                  </div>
                  <span className="text-xs font-semibold text-slate-200 group-hover:text-white transition-colors whitespace-nowrap">
                    Web Chat
                  </span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-[#0e1628] border border-slate-800 text-slate-400 font-medium whitespace-nowrap group-hover:border-slate-700">
                    Not Connected
                  </span>
                  <span className="text-xs text-slate-400 flex items-center gap-0.5 font-mono group-hover:text-sky-400 transition-colors">
                    0 <ChevronRight className="w-3.5 h-3.5" />
                  </span>
                </div>
              </Link>
            </div>
          </div>
        </div>

        {/* Col 3: Tenant Distribution */}
        <div className="col-span-12 md:col-span-6 xl:col-span-3 bg-[#0a1222] border border-slate-800/90 rounded-2xl p-5 shadow-sm flex flex-col justify-between">
          <div>
            <h2 className="text-sm font-semibold text-white">Tenant Distribution</h2>
            <p className="text-xs text-slate-400 mt-0.5 mb-4">
              Tenants by plan type.
            </p>

            <div className="flex items-center gap-4">
              {/* Donut Chart SVG */}
              <div className="relative w-20 h-20 shrink-0 flex items-center justify-center">
                <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
                  {/* Background Circle */}
                  <path
                    className="text-slate-800/80 stroke-current"
                    strokeWidth="4"
                    fill="none"
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                  <span className="text-base font-bold text-white leading-tight">
                    {stats.total_tenants}
                  </span>
                  <span className="text-[9px] text-slate-400 leading-tight">Tenants</span>
                </div>
              </div>

              {/* Legend */}
              <div className="flex-1 min-w-0 space-y-1.5 text-[11px]">
                <div className="flex items-center justify-between gap-1">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span className="w-2 h-2 rounded-full bg-sky-500 shrink-0" />
                    <span className="text-slate-300 truncate">Pro</span>
                  </div>
                  <span className="text-slate-500 font-mono text-[10px] whitespace-nowrap">
                    0 (0%)
                  </span>
                </div>
                <div className="flex items-center justify-between gap-1">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span className="w-2 h-2 rounded-full bg-purple-500 shrink-0" />
                    <span className="text-slate-300 truncate">Business</span>
                  </div>
                  <span className="text-slate-500 font-mono text-[10px] whitespace-nowrap">
                    0 (0%)
                  </span>
                </div>
                <div className="flex items-center justify-between gap-1">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
                    <span className="text-slate-300 truncate">Starter</span>
                  </div>
                  <span className="text-slate-500 font-mono text-[10px] whitespace-nowrap">
                    0 (0%)
                  </span>
                </div>
                <div className="flex items-center justify-between gap-1">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span className="w-2 h-2 rounded-full bg-amber-500 shrink-0" />
                    <span className="text-slate-300 truncate">Enterprise</span>
                  </div>
                  <span className="text-slate-500 font-mono text-[10px] whitespace-nowrap">
                    0 (0%)
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Bottom Card */}
          <Link
            href="/tenants"
            className="mt-4 bg-[#0e1628] hover:bg-[#121c32] border border-slate-800/80 hover:border-slate-700 rounded-xl p-3 flex items-center gap-3 transition-colors block"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-slate-800/80 text-slate-400 shrink-0">
                <Building2 className="w-4 h-4" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-slate-300 truncate">No tenants yet</p>
                <p className="text-[10px] text-slate-500 truncate">
                  Click to inspect or create tenants.
                </p>
              </div>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
}
