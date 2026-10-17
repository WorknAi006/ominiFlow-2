"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { adminApi } from "../../../lib/api/admin-client";
import { AdminUserItem, AdminTenantItem } from "../../../lib/types/admin";
import { StatusBadge } from "../../../components/badges/status-badge";
import { SkeletonTable } from "../../../components/loading/skeleton-table";
import { ConfirmDialog } from "../../../components/dialogs/confirm-dialog";

export default function UsersPage() {
  const [users, setUsers] = useState<AdminUserItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Available tenants for user creation
  const [tenants, setTenants] = useState<AdminTenantItem[]>([]);

  // Dialog state for actions (suspend, activate, delete)
  const [actionTarget, setActionTarget] = useState<AdminUserItem | null>(null);
  const [actionType, setActionType] = useState<"suspend" | "activate" | "delete" | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Create User Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newFirstName, setNewFirstName] = useState("");
  const [newLastName, setNewLastName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("Omniflow2026!");
  const [newIsSuperAdmin, setNewIsSuperAdmin] = useState(false);
  const [newTenantId, setNewTenantId] = useState("");
  const [newRole, setNewRole] = useState("AGENT");
  const [createError, setCreateError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await adminApi.getUsers({
        page,
        page_size: pageSize,
        search: search || undefined,
        status: statusFilter || undefined,
      });
      setUsers(res.items);
      setTotal(res.total);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load users.");
    } finally {
      setLoading(false);
    }
  };

  const fetchTenants = async () => {
    try {
      const res = await adminApi.getTenants({ page: 1, page_size: 100 });
      setTenants(res.items);
      if (res.items.length > 0 && !newTenantId) {
        setNewTenantId(res.items[0].id);
      }
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    fetchUsers();
    fetchTenants();
  }, [page, statusFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchUsers();
  };

  const handleConfirmAction = async () => {
    if (!actionTarget || !actionType) return;
    setIsSubmitting(true);
    try {
      if (actionType === "delete") {
        await adminApi.deleteUser(actionTarget.id);
      } else {
        await adminApi.updateUserStatus(actionTarget.id, actionType === "activate");
      }
      setActionTarget(null);
      setActionType(null);
      await fetchUsers();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Action failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError(null);

    if (!newFirstName.trim()) {
      setCreateError("First name is required.");
      return;
    }
    if (!newEmail.trim()) {
      setCreateError("Email is required.");
      return;
    }
    if (!newPassword || newPassword.length < 6) {
      setCreateError("Password must be at least 6 characters.");
      return;
    }

    try {
      setIsCreating(true);
      await adminApi.createUser({
        first_name: newFirstName.trim(),
        last_name: newLastName.trim() || undefined,
        email: newEmail.trim().toLowerCase(),
        password: newPassword,
        is_platform_admin: newIsSuperAdmin,
        tenant_id: !newIsSuperAdmin && newTenantId ? newTenantId : undefined,
        role_name: !newIsSuperAdmin ? newRole : undefined,
      });

      // Reset form
      setNewFirstName("");
      setNewLastName("");
      setNewEmail("");
      setNewPassword("Omniflow2026!");
      setNewIsSuperAdmin(false);
      setIsCreateOpen(false);

      // Refresh list
      await fetchUsers();
    } catch (err: unknown) {
      setCreateError(err instanceof Error ? err.message : "Failed to create user.");
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold tracking-tight text-white">Global User Accounts</h2>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-950 text-sky-400 border border-sky-800/60">
              {total} Total Users
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real registered identities, permissions, and workspace memberships across Omniflow.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              setCreateError(null);
              setIsCreateOpen(true);
            }}
            className="admin-btn admin-btn-primary text-xs font-medium px-3.5 py-2 flex items-center gap-1.5 shadow-sm"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Real User
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between bg-[#0b1325] p-3 rounded-lg border border-slate-800">
        <form onSubmit={handleSearchSubmit} className="flex-1 w-full sm:w-auto flex gap-2">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name or email address..."
            className="admin-input flex-1 w-full text-xs"
          />
          <button type="submit" className="admin-btn admin-btn-secondary text-xs">
            Search
          </button>
          {search && (
            <button
              type="button"
              onClick={() => {
                setSearch("");
                setPage(1);
                fetchUsers();
              }}
              className="px-2 py-1 text-xs text-slate-400 hover:text-white"
            >
              Clear
            </button>
          )}
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
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => fetchUsers()} className="underline ml-4 text-xs">
            Retry
          </button>
        </div>
      )}

      {/* Table Section */}
      {loading ? (
        <SkeletonTable rows={6} cols={6} />
      ) : users.length === 0 ? (
        <div className="admin-card p-12 text-center text-slate-400">
          <p className="text-sm font-medium text-slate-300">No users found</p>
          <p className="text-xs text-slate-500 mt-1">No matching user records.</p>
        </div>
      ) : (
        <div className="admin-table-container">
          <table className="admin-table">
            <thead>
              <tr>
                <th className="w-[30%]">User Details</th>
                <th className="w-[18%]">Privilege Level</th>
                <th className="w-[22%]">Tenant Workspaces</th>
                <th className="w-[10%]">Status</th>
                <th className="w-[10%]">Created</th>
                <th className="w-[10%] text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-xs text-sky-400 shrink-0">
                        {u.first_name?.[0]?.toUpperCase() || "U"}
                      </div>
                      <div className="min-w-0">
                        <span className="font-semibold text-white block text-xs truncate">
                          {u.first_name} {u.last_name || ""}
                        </span>
                        <span className="text-[11px] text-slate-400 block font-mono truncate">
                          {u.email}
                        </span>
                      </div>
                    </div>
                  </td>
                  <td>
                    {u.is_platform_admin ? (
                      <span className="admin-badge admin-badge-info">
                        ⭐ Super Admin
                      </span>
                    ) : (
                      <span className="admin-badge admin-badge-neutral">
                        👤 Workspace Member
                      </span>
                    )}
                  </td>
                  <td>
                    <div className="flex flex-wrap gap-1.5 max-w-sm">
                      {u.tenants && u.tenants.length > 0 ? (
                        u.tenants.map((tName, idx) => (
                          <span
                            key={idx}
                            className="text-[11px] bg-slate-800/90 text-sky-300 px-2 py-0.5 rounded border border-slate-700 font-medium"
                          >
                            {tName}
                          </span>
                        ))
                      ) : (
                        <span className="text-[11px] text-slate-500 italic">No workspace</span>
                      )}
                    </div>
                  </td>
                  <td>
                    <StatusBadge status={u.is_active ? "active" : "suspended"} />
                  </td>
                  <td className="text-slate-400 text-xs whitespace-nowrap">
                    {new Date(u.created_at).toLocaleDateString(undefined, {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                    })}
                  </td>
                  <td className="text-right whitespace-nowrap">
                    <div className="flex items-center justify-end gap-1.5">
                      <Link
                        href={`/users/${u.id}`}
                        className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition-colors"
                      >
                        View
                      </Link>
                      {u.is_active ? (
                        <button
                          onClick={() => {
                            setActionTarget(u);
                            setActionType("suspend");
                          }}
                          className="px-2.5 py-1 rounded bg-amber-950/40 hover:bg-amber-900/60 text-amber-300 text-xs font-medium border border-amber-800/50 transition-colors"
                        >
                          Suspend
                        </button>
                      ) : (
                        <button
                          onClick={() => {
                            setActionTarget(u);
                            setActionType("activate");
                          }}
                          className="px-2.5 py-1 rounded bg-emerald-950/40 hover:bg-emerald-900/60 text-emerald-300 text-xs font-medium border border-emerald-800/50 transition-colors"
                        >
                          Activate
                        </button>
                      )}
                      <button
                        onClick={() => {
                          setActionTarget(u);
                          setActionType("delete");
                        }}
                        className="px-2.5 py-1 rounded bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 text-xs font-medium border border-rose-800/50 transition-colors flex items-center gap-1"
                        title="Delete user account"
                      >
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                          />
                        </svg>
                        Delete
                      </button>
                    </div>
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
              className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-white border border-slate-700 transition-colors"
            >
              Previous
            </button>
            <button
              disabled={page * pageSize >= total}
              onClick={() => setPage(page + 1)}
              className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-white border border-slate-700 transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Create User Modal */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="bg-[#0b1325] border border-slate-700 rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold text-white">Add Real Working User</h3>
              <button
                onClick={() => setIsCreateOpen(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            {createError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
                {createError}
              </div>
            )}

            <form onSubmit={handleCreateUser} className="space-y-3.5 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">First Name *</label>
                  <input
                    type="text"
                    required
                    value={newFirstName}
                    onChange={(e) => setNewFirstName(e.target.value)}
                    placeholder="e.g. Jordan"
                    className="admin-input w-full"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Last Name</label>
                  <input
                    type="text"
                    value={newLastName}
                    onChange={(e) => setNewLastName(e.target.value)}
                    placeholder="e.g. Lee"
                    className="admin-input w-full"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Email Address *</label>
                <input
                  type="email"
                  required
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  placeholder="jordan.lee@company.com"
                  className="admin-input w-full"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Account Password *</label>
                <input
                  type="text"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Min 6 characters"
                  className="admin-input w-full font-mono text-xs"
                />
                <span className="text-[10px] text-slate-500 mt-0.5 block">
                  Password is securely hashed and immediately active for login.
                </span>
              </div>

              <div className="pt-2 border-t border-slate-800/80">
                <label className="flex items-center gap-2 cursor-pointer mb-2">
                  <input
                    type="checkbox"
                    checked={newIsSuperAdmin}
                    onChange={(e) => setNewIsSuperAdmin(e.target.checked)}
                    className="rounded border-slate-700 text-sky-600 focus:ring-0 bg-slate-800"
                  />
                  <span className="text-slate-200 font-medium">Grant Platform Super Admin</span>
                </label>
              </div>

              {!newIsSuperAdmin && (
                <div className="space-y-3 pt-1">
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">Assign Workspace</label>
                    <select
                      value={newTenantId}
                      onChange={(e) => setNewTenantId(e.target.value)}
                      className="admin-input w-full text-xs"
                    >
                      {tenants.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name} ({t.slug})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-slate-300 font-medium mb-1">Workspace Role</label>
                    <select
                      value={newRole}
                      onChange={(e) => setNewRole(e.target.value)}
                      className="admin-input w-full text-xs"
                    >
                      <option value="OWNER">Owner (Full Workspace Control)</option>
                      <option value="ADMIN">Admin (Workspace Administrator)</option>
                      <option value="MANAGER">Manager (Operations / Team Lead)</option>
                      <option value="AGENT">Agent (Support Representative)</option>
                      <option value="VIEWER">Viewer (Read Only)</option>
                    </select>
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-2.5 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="admin-btn admin-btn-secondary text-xs"
                  disabled={isCreating}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreating}
                  className="admin-btn admin-btn-primary text-xs"
                >
                  {isCreating ? "Creating User..." : "Create User Account"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirmation Modal for Actions (Suspend, Activate, Delete) */}
      <ConfirmDialog
        isOpen={!!actionTarget && !!actionType}
        title={
          actionType === "delete"
            ? `Delete User: ${actionTarget?.email}`
            : actionType === "suspend"
            ? `Suspend User: ${actionTarget?.email}`
            : `Activate User: ${actionTarget?.email}`
        }
        description={
          actionType === "delete"
            ? `Are you sure you want to permanently delete this user account? All workspace memberships and records for ${actionTarget?.email} will be permanently removed. This action cannot be undone.`
            : actionType === "suspend"
            ? "Suspending this user account immediately invalidates their active sessions and blocks platform authentication."
            : "Activating this user account restores their ability to sign in to their assigned workspaces."
        }
        confirmLabel={
          actionType === "delete"
            ? "Delete User Account"
            : actionType === "suspend"
            ? "Suspend Account"
            : "Activate Account"
        }
        isDestructive={actionType === "delete" || actionType === "suspend"}
        isLoading={isSubmitting}
        onConfirm={handleConfirmAction}
        onCancel={() => {
          setActionTarget(null);
          setActionType(null);
        }}
      />
    </div>
  );
}
