"use client";

import React, { useEffect, useState } from "react";
import { adminApi } from "../../../lib/api/admin-client";
import { AdminMaintenance } from "../../../lib/types/admin";
import { StatusBadge } from "../../../components/badges/status-badge";

interface MaintenanceClientProps {
  initialMaint: AdminMaintenance | null;
}

export function MaintenanceClient({ initialMaint }: MaintenanceClientProps) {
  const [maint, setMaint] = useState<AdminMaintenance | null>(initialMaint);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (initialMaint) return;
    async function load() {
      try {
        setLoading(true);
        const data = await adminApi.getMaintenance();
        setMaint(data);
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [initialMaint]);

  return (
    <div className="space-y-6">
      <div className="pb-4 border-b border-slate-800">
        <h2 className="text-xl font-bold tracking-tight text-white">Platform Maintenance & Incident Oversight</h2>
        <p className="text-xs text-slate-400 mt-1">
          Service availability status, planned downtime schedules and incident logs.
        </p>
      </div>

      {loading ? (
        <div className="h-48 bg-[#0f172a] rounded-xl border border-slate-800 animate-pulse" />
      ) : maint ? (
        <div className="space-y-6">
          <div className="admin-card p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <span className="text-xs text-slate-400 block mb-1 uppercase font-semibold">Maintenance Mode</span>
              <div className="flex items-center gap-3">
                <StatusBadge status={maint.maintenance_mode ? "warning" : "active"} />
                <span className="text-sm font-semibold text-white">
                  {maint.maintenance_mode ? "Maintenance Mode Active" : "All Systems Operational"}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-2">{maint.message || "No ongoing system disruptions."}</p>
            </div>

            <div>
              <button
                type="button"
                onClick={() => alert("Maintenance mode toggle requires backend master key confirmation.")}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium"
              >
                Schedule Maintenance Window
              </button>
            </div>
          </div>

          <div className="admin-card p-6">
            <h3 className="text-sm font-semibold text-white mb-2">Active Incidents</h3>
            <p className="text-xs text-slate-400 mb-4">
              Real-time infrastructure notices and unhandled service disruptions.
            </p>

            {maint.active_incidents.length === 0 ? (
              <div className="p-8 text-center border border-dashed border-slate-800 rounded-lg">
                <span className="text-2xl block mb-2">🎉</span>
                <p className="text-xs font-medium text-slate-300">Zero Active Platform Incidents</p>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  All microservices and database engines are operating within nominal thresholds.
                </p>
              </div>
            ) : (
              <div className="space-y-2 text-xs">
                {maint.active_incidents.map((inc, i) => (
                  <div key={i} className="p-3 rounded bg-rose-500/10 border border-rose-500/30 text-rose-300">
                    {JSON.stringify(inc)}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
