"use client";

import React, { useEffect, useState } from "react";
import { adminApi } from "../../../lib/api/admin-client";
import { AdminApiUsage } from "../../../lib/types/admin";

interface ApiUsageClientProps {
  initialUsage: AdminApiUsage | null;
}

export function ApiUsageClient({ initialUsage }: ApiUsageClientProps) {
  const [usage, setUsage] = useState<AdminApiUsage | null>(initialUsage);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchUsage = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await adminApi.getApiUsage();
      setUsage(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load API usage statistics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!initialUsage) {
      fetchUsage();
    }
  }, [initialUsage]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">Platform Throughput & API Quotas</h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time telemetry of message ingestion, webhook payloads, and tenant consumption.
          </p>
        </div>
        <button
          onClick={fetchUsage}
          className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 self-start"
        >
          🔄 Refresh Metrics
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
          {error}
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 animate-pulse">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-28 bg-[#0f172a] rounded-xl border border-slate-800" />
          ))}
        </div>
      ) : usage ? (
        <>
          {/* Key Metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="admin-card p-5">
              <span className="text-xs text-slate-400 block mb-1 uppercase font-semibold">Total API Invocations</span>
              <span className="text-2xl font-bold text-white">{usage.total_api_requests}</span>
              <p className="text-[11px] text-slate-500 mt-1">Platform endpoints called</p>
            </div>
            <div className="admin-card p-5">
              <span className="text-xs text-slate-400 block mb-1 uppercase font-semibold">Messages Processed</span>
              <span className="text-2xl font-bold text-sky-400">{usage.total_messages_processed}</span>
              <p className="text-[11px] text-slate-500 mt-1">Inbound & outbound flow</p>
            </div>
            <div className="admin-card p-5">
              <span className="text-xs text-slate-400 block mb-1 uppercase font-semibold">Webhooks Ingested</span>
              <span className="text-2xl font-bold text-emerald-400">{usage.total_webhooks_received}</span>
              <p className="text-[11px] text-slate-500 mt-1">Meta Cloud events verified</p>
            </div>
            <div className="admin-card p-5">
              <span className="text-xs text-slate-400 block mb-1 uppercase font-semibold">Rate Limit Breaches</span>
              <span className="text-2xl font-bold text-amber-400">{usage.rate_limit_events}</span>
              <p className="text-[11px] text-slate-500 mt-1">429 throttle interventions</p>
            </div>
          </div>

          {/* Usage by Tenant Table */}
          <div className="admin-card p-6">
            <h3 className="text-sm font-semibold text-white mb-2">Tenant Quota Consumption</h3>
            <p className="text-xs text-slate-400 mb-4">
              Real-time consumption breakdown against monthly tiered allowance.
            </p>

            {usage.tenant_usage.length === 0 ? (
              <p className="text-xs text-slate-500 py-6 text-center">No tenant usage records registered yet.</p>
            ) : (
              <div className="admin-table-container">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Tenant Workspace</th>
                      <th>Messages Ingested</th>
                      <th>Webhooks Handled</th>
                      <th>Monthly Quota Limit</th>
                      <th>Capacity Consumed</th>
                    </tr>
                  </thead>
                  <tbody>
                    {usage.tenant_usage.map((t) => (
                      <tr key={t.tenant_id}>
                        <td>
                          <span className="font-semibold text-white">{t.tenant_name}</span>
                          <span className="text-[10px] text-slate-500 block font-mono">{t.tenant_id}</span>
                        </td>
                        <td className="font-mono text-xs text-slate-200">{t.messages}</td>
                        <td className="font-mono text-xs text-slate-200">{t.webhooks}</td>
                        <td className="font-mono text-xs text-slate-400">{t.quota_limit.toLocaleString()} msgs</td>
                        <td className="w-48">
                          <div className="flex items-center gap-2">
                            <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full ${
                                  t.usage_percentage > 85
                                    ? "bg-rose-500"
                                    : t.usage_percentage > 60
                                    ? "bg-amber-500"
                                    : "bg-sky-500"
                                }`}
                                style={{ width: `${Math.max(2, t.usage_percentage)}%` }}
                              />
                            </div>
                            <span className="text-[11px] font-mono text-slate-400 w-10 text-right">
                              {t.usage_percentage}%
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      ) : null}
    </div>
  );
}
