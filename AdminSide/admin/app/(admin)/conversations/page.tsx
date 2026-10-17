"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { adminApi } from "../../../lib/api/admin-client";
import { AdminConversationItem } from "../../../lib/types/admin";
import { StatusBadge } from "../../../components/badges/status-badge";
import { SkeletonTable } from "../../../components/loading/skeleton-table";

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<AdminConversationItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchConversations = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await adminApi.getConversations({
        page,
        page_size: pageSize,
        search: search || undefined,
        status: statusFilter || undefined,
      });
      setConversations(res.items);
      setTotal(res.total);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load conversations.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConversations();
  }, [page, statusFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchConversations();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">Conversation Monitor</h2>
          <p className="text-xs text-slate-400 mt-1">
            Platform-wide customer conversation traffic and message ingestion oversight.
          </p>
        </div>
        <div className="text-xs text-slate-400">
          Total Conversations: <span className="font-semibold text-white">{total}</span>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between bg-[#0f172a] p-3 rounded-lg border border-slate-800">
        <form onSubmit={handleSearchSubmit} className="flex-1 w-full sm:w-auto flex gap-2">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by contact name or message preview..."
            className="admin-input flex-1 w-full text-xs"
          />
          <button type="submit" className="admin-btn admin-btn-secondary text-xs">
            Search
          </button>
        </form>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="admin-input text-xs"
          >
            <option value="">All Statuses</option>
            <option value="open">Open</option>
            <option value="pending">Pending</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
          {error}
        </div>
      )}

      {loading ? (
        <SkeletonTable rows={5} cols={6} />
      ) : conversations.length === 0 ? (
        <div className="admin-card p-12 text-center text-slate-400">
          <p className="text-sm font-medium text-slate-300">No conversations recorded</p>
          <p className="text-xs text-slate-500 mt-1">
            Incoming customer messages from WhatsApp or Web Chat will populate this feed.
          </p>
        </div>
      ) : (
        <div className="admin-table-container">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Customer Contact</th>
                <th>Tenant Organization</th>
                <th>Channel</th>
                <th>Last Message Preview</th>
                <th>Status</th>
                <th>Last Activity</th>
              </tr>
            </thead>
            <tbody>
              {conversations.map((c) => (
                <tr key={c.id}>
                  <td>
                    <span className="font-semibold text-white block">
                      {c.contact_name || c.contact_phone || "Anonymous"}
                    </span>
                    {c.contact_phone && (
                      <span className="text-[11px] text-slate-400 font-mono">{c.contact_phone}</span>
                    )}
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
                    <span className="font-mono text-xs uppercase px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">
                      {c.channel_type}
                    </span>
                  </td>
                  <td className="max-w-xs truncate text-xs text-slate-300">
                    {c.last_message_preview || <span className="text-slate-500 italic">No messages</span>}
                  </td>
                  <td>
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="text-slate-400 text-xs">
                    {new Date(c.updated_at).toLocaleString()}
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
