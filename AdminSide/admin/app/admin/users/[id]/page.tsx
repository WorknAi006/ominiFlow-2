"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { adminApi } from "../../../../lib/api/admin-client";
import { AdminUserItem } from "../../../../lib/types/admin";
import { StatusBadge } from "../../../../components/badges/status-badge";
import { ConfirmDialog } from "../../../../components/dialogs/confirm-dialog";

export default function UserDetailPage() {
  const params = useParams();
  const userId = params?.id as string;

  const [user, setUser] = useState<AdminUserItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dialog state
  const [actionType, setActionType] = useState<"suspend" | "activate" | "delete" | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchUser = async () => {
    try {
      setLoading(true);
      setError(null);
      // Fetch users and find by id
      const res = await adminApi.getUsers({ page: 1, page_size: 100 });
      const found = res.items.find((u) => u.id === userId);
      if (found) {
        setUser(found);
      } else {
        setError("User account not found.");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load user details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (userId) {
      fetchUser();
    }
  }, [userId]);

  const handleConfirmAction = async () => {
    if (!user || !actionType) return;
    setIsSubmitting(true);
    try {
      if (actionType === "delete") {
        await adminApi.deleteUser(user.id);
        window.location.href = "/admin/users";
        return;
      }
      await adminApi.updateUserStatus(user.id, actionType === "activate");
      await fetchUser();
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

  if (error || !user) {
    return (
      <div className="p-6 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300">
        <h3 className="font-semibold text-sm mb-1">Error</h3>
        <p className="text-xs mb-4">{error || "User not found."}</p>
        <Link href="/admin/users" className="text-xs underline text-sky-400">
          ← Return to Users Directory
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <Link
          href="/admin/users"
          className="text-xs text-slate-400 hover:text-white flex items-center gap-1 transition-colors"
        >
          <span>←</span> Back to Users
        </Link>
      </div>

      <div className="admin-card p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-lg text-sky-400 shrink-0">
            {user.first_name[0]}
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold text-white tracking-tight">
                {user.first_name} {user.last_name || ""}
              </h2>
              <StatusBadge status={user.is_active ? "active" : "suspended"} />
              {user.is_platform_admin && (
                <span className="admin-badge admin-badge-info">⭐ Super Admin</span>
              )}
            </div>
            <p className="text-xs text-slate-400 font-mono mt-1">
              ID: {user.id} • Email: <span className="text-sky-300">{user.email}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {user.is_active ? (
            <button
              onClick={() => setActionType("suspend")}
              className="px-3 py-2 rounded-lg bg-amber-950/40 hover:bg-amber-900/60 text-amber-300 text-xs font-medium border border-amber-800/50 transition-colors"
            >
              Suspend Account
            </button>
          ) : (
            <button
              onClick={() => setActionType("activate")}
              className="px-3 py-2 rounded-lg bg-emerald-950/40 hover:bg-emerald-900/60 text-emerald-300 text-xs font-medium border border-emerald-800/50 transition-colors"
            >
              Activate Account
            </button>
          )}
          <button
            onClick={() => setActionType("delete")}
            className="px-3 py-2 rounded-lg bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 text-xs font-medium border border-rose-800/50 transition-colors flex items-center gap-1.5"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Delete Account
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="admin-card p-5 space-y-4">
          <h3 className="text-sm font-semibold text-white border-b border-slate-800 pb-2">
            Identity Attributes
          </h3>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Email Address</span>
              <span className="font-mono text-slate-200">{user.email}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Email Verified</span>
              <span className="text-slate-200">{user.is_verified ? "Yes" : "No"}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Created Date</span>
              <span className="text-slate-200">{new Date(user.created_at).toLocaleString()}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Super Admin Status</span>
              <span className="text-slate-200">{user.is_platform_admin ? "Granted" : "None"}</span>
            </div>
          </div>
        </div>

        <div className="admin-card p-5 space-y-4">
          <h3 className="text-sm font-semibold text-white border-b border-slate-800 pb-2">
            Workspace Memberships
          </h3>
          {user.tenants.length === 0 ? (
            <p className="text-xs text-slate-500 py-3">User is not assigned to any customer workspaces.</p>
          ) : (
            <div className="space-y-2 text-xs">
              {user.tenants.map((tName, i) => (
                <div key={i} className="flex justify-between py-1.5 border-b border-slate-800/60">
                  <span className="font-medium text-slate-200">{tName}</span>
                  <span className="text-sky-400 text-[11px]">Member</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <ConfirmDialog
        isOpen={!!actionType}
        title={
          actionType === "delete"
            ? `Delete User: ${user.email}`
            : actionType === "suspend"
            ? `Suspend User: ${user.email}`
            : `Activate User: ${user.email}`
        }
        description={
          actionType === "delete"
            ? "Permanently delete this user account? All workspace memberships and records for this user will be removed. This action cannot be undone."
            : actionType === "suspend"
            ? "Suspending this user blocks access across all assigned workspaces."
            : "Activating this user restores workspace sign-in capability."
        }
        confirmLabel={
          actionType === "delete"
            ? "Delete Account"
            : actionType === "suspend"
            ? "Suspend Account"
            : "Activate Account"
        }
        isDestructive={actionType === "delete" || actionType === "suspend"}
        isLoading={isSubmitting}
        onConfirm={handleConfirmAction}
        onCancel={() => setActionType(null)}
      />
    </div>
  );
}
