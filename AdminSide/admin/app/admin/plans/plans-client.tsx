"use client";

import React, { useEffect, useState } from "react";
import { adminApi } from "../../../lib/api/admin-client";

interface PlanItem {
  id: string;
  name: string;
  price: string;
  limits: Record<string, number>;
  active_tenants: number;
  features: string[];
}

interface PlansClientProps {
  initialPlans: PlanItem[] | null;
}

export function PlansClient({ initialPlans }: PlansClientProps) {
  const [plans, setPlans] = useState<PlanItem[]>(initialPlans || []);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialPlans) return;
    async function load() {
      try {
        setLoading(true);
        const res = await adminApi.getPlans();
        setPlans(res.items);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load plans.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [initialPlans]);

  return (
    <div className="space-y-6">
      <div className="pb-4 border-b border-slate-800">
        <h2 className="text-xl font-bold tracking-tight text-white">Platform Subscription Tiers</h2>
        <p className="text-xs text-slate-400 mt-1">
          Defined quota tiers, resource ceilings and active organization subscriptions.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
          {error}
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-pulse">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-64 bg-[#0f172a] rounded-xl border border-slate-800" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {plans.map((p) => (
            <div key={p.id} className="admin-card p-6 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-base font-bold text-white">{p.name}</h3>
                  <span className="text-xs font-mono font-bold text-sky-400">{p.price}</span>
                </div>
                <div className="text-xs text-slate-400 mb-4">
                  Active Organizations: <span className="font-semibold text-white">{p.active_tenants}</span>
                </div>

                <div className="space-y-2 mb-6 text-xs text-slate-300">
                  <div className="flex justify-between py-1 border-b border-slate-800/60">
                    <span className="text-slate-400">Max Channels</span>
                    <span className="font-semibold text-white">{p.limits.channels}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800/60">
                    <span className="text-slate-400">Monthly Messages</span>
                    <span className="font-semibold text-white">{p.limits.messages.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800/60">
                    <span className="text-slate-400">Team Seats</span>
                    <span className="font-semibold text-white">{p.limits.members}</span>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">Features Included</span>
                  {p.features.map((f, idx) => (
                    <div key={idx} className="flex items-center gap-2 text-xs text-slate-300">
                      <span className="text-emerald-400 text-xs">✓</span>
                      <span>{f}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  className="w-full py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700"
                >
                  Configure Tier Quotas
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
