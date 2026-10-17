"use client";

import React, { useEffect, useState } from "react";
import { adminApi } from "../../../lib/api/admin-client";

interface BillingData {
  status: string;
  message: string;
  active_subscriptions: number;
  mrr_usd: number;
  billing_cycles: string[];
}

interface BillingClientProps {
  initialBilling: BillingData | null;
}

export function BillingClient({ initialBilling }: BillingClientProps) {
  const [billing, setBilling] = useState<BillingData | null>(initialBilling);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (initialBilling) return;
    async function load() {
      try {
        setLoading(true);
        const data = await adminApi.getBilling();
        setBilling(data);
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [initialBilling]);

  return (
    <div className="space-y-6">
      <div className="pb-4 border-b border-slate-800">
        <h2 className="text-xl font-bold tracking-tight text-white">Billing & Revenue Operations</h2>
        <p className="text-xs text-slate-400 mt-1">
          Subscription tracking, payment gateway orchestration and recurring revenue reports.
        </p>
      </div>

      {loading ? (
        <div className="h-48 bg-[#0f172a] rounded-xl border border-slate-800 animate-pulse" />
      ) : (
        <>
          {/* Pending Integration Notice */}
          <div className="admin-card p-6 border-amber-500/30 bg-amber-500/5">
            <div className="flex items-start gap-3">
              <span className="text-xl">💳</span>
              <div>
                <h3 className="text-sm font-semibold text-amber-200">
                  Payment Gateway Status: Pending Integration
                </h3>
                <p className="text-xs text-amber-300/80 mt-1">
                  {billing?.message ||
                    "Direct Stripe / Paddle integration is pending. Omniflow currently provisions all tenants under local development tier governance without active card billing."}
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="admin-card p-5">
              <span className="text-xs text-slate-400 block mb-1">Active Subscriptions</span>
              <span className="text-2xl font-bold text-white">{billing?.active_subscriptions || 0}</span>
              <p className="text-[11px] text-slate-500 mt-1">Direct billing accounts</p>
            </div>
            <div className="admin-card p-5">
              <span className="text-xs text-slate-400 block mb-1">Current MRR</span>
              <span className="text-2xl font-bold text-slate-300">${billing?.mrr_usd || 0}.00</span>
              <p className="text-[11px] text-slate-500 mt-1">Monthly Recurring Revenue</p>
            </div>
            <div className="admin-card p-5">
              <span className="text-xs text-slate-400 block mb-1">Supported Cycles</span>
              <span className="text-sm font-mono text-slate-300">Monthly, Annual</span>
              <p className="text-[11px] text-slate-500 mt-1">Recurring frequency</p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
