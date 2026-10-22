"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { adminApi } from "../../../lib/api/admin-client";
import { AdminTenantItem } from "../../../lib/types/admin";
import { StatusBadge } from "../../../components/badges/status-badge";
import { SkeletonTable } from "../../../components/loading/skeleton-table";
import { ConfirmDialog } from "../../../components/dialogs/confirm-dialog";
import { CreateTenantDialog } from "../../../components/dialogs/create-tenant-dialog";

interface TenantsClientProps {
  initialData: {
    items: AdminTenantItem[];
    total: number;
    page: number;
    page_size: number;
  } | null;
}

export function TenantsClient({ initialData }: TenantsClientProps) {
  const [tenants, setTenants] = useState<AdminTenantItem[]>(initialData?.items || []);
  const [total, setTotal] = useState(initialData?.total || 0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(!initialData);
  const [error, setError] = useState<string | null>(null);
  const isInitialMount = useRef(true);

  // Dialog state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [actionTarget, setActionTarget] = useState<AdminTenantItem | null>(null);
  const [actionType, setActionType] = useState<"suspend" | "restore" | "delete" | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchTenants = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await adminApi.getTenants({
        page,
        page_size: pageSize,
        search: search || undefined,
        status: statusFilter || undefined,
      });
      setTenants(res.items);
      setTotal(res.total);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load tenants.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      if (initialData) return; // Data already populated on server
    }
    fetchTenants();
  }, [page, statusFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchTenants();
  };

  const handleConfirmAction = async () => {
    if (!actionTarget || !actionType) return;
    setIsSubmitting(true);
    try {
      if (actionType === "suspend") {
        await adminApi.updateTenantStatus(actionTarget.id, false);
      } else if (actionType === "restore") {
        await adminApi.updateTenantStatus(actionTarget.id, true);
      } else if (actionType === "delete") {
        await adminApi.deleteTenant(actionTarget.id);
      }
      setActionTarget(null);
      setActionType(null);
      await fetchTenants();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Action failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">Tenants Directory</h2>
          <p className="text-xs text-slate-400 mt-1">
            All registered organizations and workspaces on the Omniflow platform.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-xs text-slate-400">
            Total Organizations: <span className="font-semibold text-white">{total}</span>
          </div>
          <button
            onClick={() => setIsCreateOpen(true)}
            className="px-3.5 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-lg shadow-sky-600/30 transition-all flex items-center gap-1.5 cursor-pointer"
          >
            <span>+</span> Provision New Tenant
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between bg-[#0f172a] p-3 rounded-lg border border-slate-800">
        <form onSubmit={handleSearchSubmit} className="flex-1 w-full sm:w-auto flex gap-2">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search tenant by name, slug or email..."
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
            <option value="active">Active Only</option>
            <option value="suspended">Suspended Only</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
          {error}
        </div>
      )}

      {loading ? (
        <SkeletonTable rows={6} cols={6} />
      ) : tenants.length === 0 ? (
        <div className="admin-card p-12 text-center text-slate-400">
          <p className="text-sm font-medium text-slate-300">No tenants found</p>
          <p className="text-xs text-slate-500 mt-1">Try adjusting your search criteria or register a new workspace.</p>
        </div>
      ) : (
        <div className="admin-table-container">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Organization</th>
                <th>Slug</th>
                <th>Status</th>
                <th>Seats / Users</th>
                <th>Channels</th>
                <th>Conversations</th>
                <th>Created</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {tenants.map((t) => (
                <tr key={t.id}>
                  <td>
                    <Link
                      href={`/admin/tenants/${t.id}`}
                      className="font-semibold text-white hover:text-sky-400 transition-colors block"
                    >
                      {t.name}
                    </Link>
                    <span className="text-[10px] text-slate-500 font-mono">{t.id}</span>
                  </td>
                  <td className="font-mono text-xs text-slate-400">{t.slug}</td>
                  <td>
                    <StatusBadge status={t.is_active ? "active" : "suspended"} />
                  </td>
                  <td>
                    <span className="font-semibold text-slate-200">{t.user_count}</span>
                    <span className="text-[10px] text-slate-500 ml-1">members</span>
                  </td>
                  <td>
                    <span className="font-semibold text-slate-200">{t.channel_count}</span>
                    <span className="text-[10px] text-slate-500 ml-1">connected</span>
                  </td>
                  <td>
                    <span className="font-semibold text-slate-200">{t.conversation_count}</span>
                  </td>
                  <td className="text-slate-400 text-xs">
                    {new Date(t.created_at).toLocaleDateString()}
                  </td>
                  <td className="text-right space-x-2">
                    <Link
                      href={`/admin/tenants/${t.id}`}
                      className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 inline-block"
                    >
                      Inspect
                    </Link>
                    {t.is_active ? (
                      <button
                        onClick={() => {
                          setActionTarget(t);
                          setActionType("suspend");
                        }}
                        className="px-2.5 py-1 rounded bg-amber-950/40 hover:bg-amber-900/60 text-amber-300 text-xs font-medium border border-amber-800/50"
                      >
                        Suspend
                      </button>
                    ) : (
                      <button
                        onClick={() => {
                          setActionTarget(t);
                          setActionType("restore");
                        }}
                        className="px-2.5 py-1 rounded bg-emerald-950/40 hover:bg-emerald-900/60 text-emerald-300 text-xs font-medium border border-emerald-800/50"
                      >
                        Restore
                      </button>
                    )}
                    <button
                      onClick={() => {
                        setActionTarget(t);
                        setActionType("delete");
                      }}
                      className="px-2.5 py-1 rounded bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 text-xs font-medium border border-rose-800/50"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination Controls */}
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

      {/* Confirmation Modal */}
      <ConfirmDialog
        isOpen={!!actionTarget && !!actionType}
        title={
          actionType === "suspend"
            ? `Suspend Workspace: ${actionTarget?.name}`
            : actionType === "restore"
            ? `Restore Workspace: ${actionTarget?.name}`
            : `Delete Workspace: ${actionTarget?.name}`
        }
        description={
          actionType === "suspend"
            ? "Suspending this workspace prevents its members from logging in and accessing live channels. Inbound webhooks will be paused."
            : actionType === "restore"
            ? "Restoring this workspace immediately re-enables full access for its members and channels."
            : "Deleting this workspace is a destructive action. The organization will be soft-deleted and all live channels disconnected."
        }
        confirmLabel={
          actionType === "suspend"
            ? "Suspend Workspace"
            : actionType === "restore"
            ? "Restore Access"
            : "Permanently Delete"
        }
        isDestructive={actionType === "suspend" || actionType === "delete"}
        isLoading={isSubmitting}
        onConfirm={handleConfirmAction}
        onCancel={() => {
          setActionTarget(null);
          setActionType(null);
        }}
      />

      <CreateTenantDialog
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onCreated={() => {
          fetchTenants();
        }}
      />
    </div>
  );
}
