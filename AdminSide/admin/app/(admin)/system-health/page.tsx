"use client";

import React, { useEffect, useState } from "react";
import { adminApi } from "../../../lib/api/admin-client";
import { AdminSystemHealth } from "../../../lib/types/admin";
import { StatusBadge } from "../../../components/badges/status-badge";

export default function SystemHealthPage() {
  const [health, setHealth] = useState<AdminSystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await adminApi.getSystemHealth();
      setHealth(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load system health metrics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">Infrastructure & Subsystem Diagnostics</h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time ping probes, database latency and broker responsiveness.
          </p>
        </div>
        <button
          onClick={fetchHealth}
          className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 flex items-center gap-1.5 self-start"
        >
          <span>🔄</span>
          <span>Run Probe Now</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
          {error}
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-pulse">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-32 bg-[#0f172a] rounded-xl border border-slate-800" />
          ))}
        </div>
      ) : health ? (
        <div className="space-y-6">
          {/* Overall Health Status Bar */}
          <div className="admin-card p-5 flex items-center justify-between border-sky-500/30 bg-sky-500/5">
            <div>
              <span className="text-xs text-slate-400 block mb-0.5 uppercase tracking-wider">Overall Status</span>
              <span className="text-lg font-bold text-white capitalize">{health.overall_status}</span>
            </div>
            <div className="text-right">
              <span className="text-[11px] text-slate-400 block">Probe Timestamp</span>
              <span className="text-xs font-mono text-slate-300">
                {new Date(health.timestamp).toLocaleTimeString()}
              </span>
            </div>
          </div>

          {/* Component Status Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {health.components.map((comp, idx) => (
              <div key={idx} className="admin-card p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-white">{comp.name}</h3>
                  <StatusBadge status={comp.status} />
                </div>

                <p className="text-xs text-slate-400">{comp.details || "Component operational"}</p>

                <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-400">
                  <span>Roundtrip Latency:</span>
                  <span className={comp.latency_ms !== null ? "text-emerald-400 font-semibold" : "text-slate-500"}>
                    {comp.latency_ms !== null ? `${comp.latency_ms} ms` : "Not applicable"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
