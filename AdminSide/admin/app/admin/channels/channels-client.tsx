"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { adminApi } from "../../../lib/api/admin-client";
import { AdminChannelItem } from "../../../lib/types/admin";
import { StatusBadge } from "../../../components/badges/status-badge";
import { SkeletonTable } from "../../../components/loading/skeleton-table";

interface ChannelsClientProps {
  initialData: { items: AdminChannelItem[]; total: number; page: number; page_size: number } | null;
}

export function ChannelsClient({ initialData }: ChannelsClientProps) {
  const [channels, setChannels] = useState<AdminChannelItem[]>(initialData?.items || []);
  const [total, setTotal] = useState(initialData?.total || 0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(!initialData);
  const [error, setError] = useState<string | null>(null);
  const isInitialMount = useRef(true);

  const fetchChannels = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await adminApi.getChannels({
        page,
        page_size: pageSize,
        search: search || undefined,
        channel_type: typeFilter || undefined,
        status: statusFilter || undefined,
      });
      setChannels(res.items);
      setTotal(res.total);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load channels.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      if (initialData) return;
    }
    fetchChannels();
  }, [page, typeFilter, statusFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchChannels();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">Channel Integrations</h2>
          <p className="text-xs text-slate-400 mt-1">
            Global monitoring of customer WhatsApp, Web Chat and Social connections.
          </p>
        </div>
        <div className="text-xs text-slate-400">
          Total Channels: <span className="font-semibold text-white">{total}</span>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between bg-[#0f172a] p-3 rounded-lg border border-slate-800">
        <form onSubmit={handleSearchSubmit} className="flex-1 w-full sm:w-auto flex gap-2">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search channel name or external account ID..."
            className="admin-input flex-1 w-full text-xs"
          />
          <button type="submit" className="admin-btn admin-btn-secondary text-xs">
            Search
          </button>
        </form>

        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
          <select
            value={typeFilter}
            onChange={(e) => {
              setTypeFilter(e.target.value);
              setPage(1);
            }}
            className="admin-input text-xs"
          >
            <option value="">All Channel Types</option>
            <option value="whatsapp">WhatsApp Cloud API</option>
            <option value="web_chat">Web Chat Widget</option>
            <option value="instagram">Instagram Direct</option>
            <option value="facebook">Facebook Messenger</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="admin-input text-xs"
          >
            <option value="">All Statuses</option>
            <option value="connected">Connected</option>
            <option value="pending">Pending</option>
            <option value="disconnected">Disconnected</option>
            <option value="error">Error</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
          {error}
        </div>
      )}

      {loading ? (
        <SkeletonTable rows={5} cols={5} />
      ) : channels.length === 0 ? (
        <div className="admin-card p-12 text-center text-slate-400">
          <p className="text-sm font-medium text-slate-300">No channels configured</p>
          <p className="text-xs text-slate-500 mt-1">Tenants have not connected communication channels yet.</p>
        </div>
      ) : (
        <div className="admin-table-container">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Channel Name</th>
                <th>Tenant Organization</th>
                <th>Provider Type</th>
                <th>Account ID</th>
                <th>Status</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {channels.map((c) => (
                <tr key={c.id}>
                  <td>
                    <span className="font-semibold text-white block">{c.name}</span>
                    <span className="text-[10px] text-slate-500 font-mono">{c.id}</span>
                  </td>
                  <td>
                    <Link
                      href={`/tenants/${c.tenant_id}`}
                      className="text-sky-400 hover:underline font-medium text-xs"
                    >
                      {c.tenant_name}
                    </Link>
                  </td>
                  <td>
                    <span className="font-mono text-xs text-slate-300 uppercase px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                      {c.channel_type}
                    </span>
                  </td>
                  <td className="font-mono text-xs text-slate-400">
                    {c.external_account_id || "—"}
                  </td>
                  <td>
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="text-slate-400 text-xs">
                    {new Date(c.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {total > pageSize && (
        <div className="flex items-center justify-between pt-2 text-xs text-slate-400">
          <span>
            Showing {(page - 1) * pageSize + 1} to {Math.min(total, page * pageSize)} of {total} results
          </span>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
              className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-white border border-slate-700"
            >
              Previous
            </button>
            <button
              disabled={page * pageSize >= total}
              onClick={() => setPage(page + 1)}
              className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-white border border-slate-700"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
