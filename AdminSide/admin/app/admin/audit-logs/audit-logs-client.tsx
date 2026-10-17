"use client";

import React, { useEffect, useState } from "react";
import { adminApi } from "../../../lib/api/admin-client";
import { AdminAuditLogItem } from "../../../lib/types/admin";
import { StatusBadge } from "../../../components/badges/status-badge";
import { SkeletonTable } from "../../../components/loading/skeleton-table";

interface AuditLogsClientProps {
  initialLogs: AdminAuditLogItem[] | null;
}

export function AuditLogsClient({ initialLogs }: AuditLogsClientProps) {
  const [logs, setLogs] = useState<AdminAuditLogItem[]>(initialLogs || []);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialLogs) return;
    async function load() {
      try {
        setLoading(true);
        const data = await adminApi.getAuditLogs();
        setLogs(data.items);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load audit logs.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [initialLogs]);

  return (
    <div className="space-y-6">
      <div className="pb-4 border-b border-slate-800">
        <h2 className="text-xl font-bold tracking-tight text-white">Platform Audit Trail</h2>
        <p className="text-xs text-slate-400 mt-1">
          Immutable historical record of tenant creation, role modifications and system events.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
          {error}
        </div>
      )}

      {loading ? (
        <SkeletonTable rows={6} cols={6} />
      ) : logs.length === 0 ? (
        <div className="admin-card p-12 text-center text-slate-400">
          <p className="text-sm font-medium text-slate-300">No audit logs recorded yet</p>
          <p className="text-xs text-slate-500 mt-1">Administrative events will be logged here.</p>
        </div>
      ) : (
        <div className="admin-table-container">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Actor</th>
                <th>Action Event</th>
                <th>Target Resource</th>
                <th>Organization</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((item) => (
                <tr key={item.id}>
                  <td className="font-mono text-xs text-slate-400">
                    {new Date(item.timestamp).toLocaleString()}
                  </td>
                  <td className="text-xs font-medium text-slate-300">{item.actor}</td>
                  <td>
                    <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-sky-300">
                      {item.action}
                    </span>
                  </td>
                  <td className="text-xs text-slate-200">{item.target}</td>
                  <td className="text-xs text-slate-400">{item.tenant || "System"}</td>
                  <td>
                    <StatusBadge status={item.result} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
