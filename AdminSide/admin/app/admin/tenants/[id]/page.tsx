"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { adminApi } from "../../../../lib/api/admin-client";
import { AdminTenantDetail } from "../../../../lib/types/admin";
import { StatusBadge } from "../../../../components/badges/status-badge";
import { ConfirmDialog } from "../../../../components/dialogs/confirm-dialog";

export default function TenantDetailPage() {
  const params = useParams();
  const router = useRouter();
  const tenantId = params?.id as string;

  const [tenant, setTenant] = useState<AdminTenantDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dialog state
  const [actionType, setActionType] = useState<"suspend" | "restore" | "delete" | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchTenant = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await adminApi.getTenant(tenantId);
      setTenant(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load tenant details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (tenantId) {
      fetchTenant();
    }
  }, [tenantId]);

  const handleConfirmAction = async () => {
    if (!tenant || !actionType) return;
    setIsSubmitting(true);
    try {
      if (actionType === "suspend") {
        await adminApi.updateTenantStatus(tenant.id, false);
        await fetchTenant();
      } else if (actionType === "restore") {
        await adminApi.updateTenantStatus(tenant.id, true);
        await fetchTenant();
      } else if (actionType === "delete") {
        await adminApi.deleteTenant(tenant.id);
        router.push("/admin/tenants");
      }
      setActionType(null);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Action failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-6 w-32 bg-slate-800 rounded" />
        <div className="h-40 bg-[#0f172a] rounded-xl border border-slate-800" />
      </div>
    );
  }

  if (error || !tenant) {
    return (
      <div className="p-6 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300">
        <h3 className="font-semibold text-sm mb-1">Failed to load organization</h3>
        <p className="text-xs mb-4">{error || "Tenant not found."}</p>
        <Link href="/admin/tenants" className="text-xs underline text-sky-400">
          ← Return to Tenants Directory
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back button */}
      <div>
        <Link
          href="/admin/tenants"
          className="text-xs text-slate-400 hover:text-white flex items-center gap-1 transition-colors"
        >
          <span>←</span> Back to Tenants
        </Link>
      </div>

      {/* Hero Header */}
      <div className="admin-card p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold text-white tracking-tight">{tenant.name}</h2>
            <StatusBadge status={tenant.is_active ? "active" : "suspended"} />
          </div>
          <p className="text-xs text-slate-400 font-mono mt-1">
            ID: {tenant.id} • Slug: <span className="text-sky-300">@{tenant.slug}</span>
          </p>
          {tenant.description && (
            <p className="text-xs text-slate-300 mt-2 max-w-2xl">{tenant.description}</p>
          )}
        </div>

        <div className="flex items-center gap-2">
          {tenant.is_active ? (
            <button
              onClick={() => setActionType("suspend")}
              className="px-3 py-2 rounded-lg bg-amber-950/40 hover:bg-amber-900/60 text-amber-300 text-xs font-medium border border-amber-800/50 transition-colors"
            >
              Suspend Workspace
            </button>
          ) : (
            <button
              onClick={() => setActionType("restore")}
              className="px-3 py-2 rounded-lg bg-emerald-950/40 hover:bg-emerald-900/60 text-emerald-300 text-xs font-medium border border-emerald-800/50 transition-colors"
            >
              Restore Workspace
            </button>
          )}
          <button
            onClick={() => setActionType("delete")}
            className="px-3 py-2 rounded-lg bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 text-xs font-medium border border-rose-800/50 transition-colors"
          >
            Delete Workspace
          </button>
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="admin-card p-4">
          <span className="text-xs text-slate-400 block mb-1">Active Members</span>
          <span className="text-xl font-bold text-white">{tenant.user_count}</span>
        </div>
        <div className="admin-card p-4">
          <span className="text-xs text-slate-400 block mb-1">Live Channels</span>
          <span className="text-xl font-bold text-white">{tenant.channel_count}</span>
        </div>
        <div className="admin-card p-4">
          <span className="text-xs text-slate-400 block mb-1">Total Conversations</span>
          <span className="text-xl font-bold text-white">{tenant.conversation_count}</span>
        </div>
        <div className="admin-card p-4">
          <span className="text-xs text-slate-400 block mb-1">Platform Plan</span>
          <span className="text-xl font-bold text-sky-400">{tenant.plan}</span>
        </div>
      </div>

      {/* Two column: Members & Channels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Members */}
        <div className="admin-card p-5">
          <h3 className="text-sm font-semibold text-white mb-3 flex items-center justify-between">
            <span>Workspace Team Members</span>
            <span className="text-xs text-slate-400 font-normal">{tenant.users.length} registered</span>
          </h3>

          {tenant.users.length === 0 ? (
            <p className="text-xs text-slate-500 py-4">No active members found in this tenant.</p>
          ) : (
            <div className="divide-y divide-slate-800/60">
              {tenant.users.map((u) => (
                <div key={u.id} className="py-2.5 flex items-center justify-between text-xs">
                  <div>
                    <p className="font-medium text-slate-200">{u.name}</p>
                    <p className="text-[11px] text-slate-400">{u.email}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={u.status} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Channels */}
        <div className="admin-card p-5">
          <h3 className="text-sm font-semibold text-white mb-3 flex items-center justify-between">
            <span>Configured Channel Integrations</span>
            <span className="text-xs text-slate-400 font-normal">{tenant.channels.length} connections</span>
          </h3>

          {tenant.channels.length === 0 ? (
            <p className="text-xs text-slate-500 py-4">No channels connected to this tenant yet.</p>
          ) : (
            <div className="divide-y divide-slate-800/60">
              {tenant.channels.map((c) => (
                <div key={c.id} className="py-2.5 flex items-center justify-between text-xs">
                  <div>
                    <p className="font-medium text-slate-200">{c.name}</p>
                    <p className="text-[11px] text-slate-400 uppercase font-mono">{c.type}</p>
                  </div>
                  <div>
                    <StatusBadge status={c.status} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Confirmation Modal */}
      <ConfirmDialog
        isOpen={!!actionType}
        title={
          actionType === "suspend"
            ? `Suspend Workspace: ${tenant.name}`
            : actionType === "restore"
            ? `Restore Workspace: ${tenant.name}`
            : `Delete Workspace: ${tenant.name}`
        }
        description={
          actionType === "suspend"
            ? "Suspending this workspace immediately freezes all member logins and webhooks."
            : actionType === "restore"
            ? "Restoring this workspace immediately reactivates access for team members."
            : "Permanently delete this organization. This cannot be undone."
        }
        confirmLabel={
          actionType === "suspend"
            ? "Suspend Workspace"
            : actionType === "restore"
            ? "Restore Access"
            : "Delete Permanently"
        }
        isDestructive={actionType === "suspend" || actionType === "delete"}
        isLoading={isSubmitting}
        onConfirm={handleConfirmAction}
        onCancel={() => setActionType(null)}
      />
    </div>
  );
}
