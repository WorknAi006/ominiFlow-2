"use client";

import React, { useState } from "react";
import { adminApi } from "../../lib/api/admin-client";

interface CreateTenantDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export function CreateTenantDialog({
  isOpen,
  onClose,
  onCreated,
}: CreateTenantDialogProps) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [description, setDescription] = useState("");
  const [ownerEmail, setOwnerEmail] = useState("");
  const [ownerFirstName, setOwnerFirstName] = useState("");
  const [ownerLastName, setOwnerLastName] = useState("");
  const [ownerPassword, setOwnerPassword] = useState("");
  const [ownerPhone, setOwnerPhone] = useState("");
  const [plan, setPlan] = useState("Standard");
  const [initialCredits, setInitialCredits] = useState(500);
  const [isActive, setIsActive] = useState(true);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successData, setSuccessData] = useState<{
    tenantName: string;
    ownerEmail: string;
    temporaryPassword: string | null;
  } | null>(null);
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const resetForm = () => {
    setName("");
    setSlug("");
    setEmail("");
    setPhone("");
    setDescription("");
    setOwnerEmail("");
    setOwnerFirstName("");
    setOwnerLastName("");
    setOwnerPassword("");
    setOwnerPhone("");
    setPlan("Standard");
    setInitialCredits(500);
    setIsActive(true);
    setError(null);
    setSuccessData(null);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError("Tenant / Organization name is required.");
      return;
    }
    if (!ownerEmail.trim()) {
      setError("Owner email address is required.");
      return;
    }
    if (!ownerFirstName.trim()) {
      setError("Owner first name is required.");
      return;
    }

    setIsLoading(true);
    try {
      const res = await adminApi.createTenant({
        name: name.trim(),
        slug: slug.trim() || undefined,
        email: email.trim() || undefined,
        phone: phone.trim() || undefined,
        description: description.trim() || undefined,
        owner_email: ownerEmail.trim(),
        owner_first_name: ownerFirstName.trim(),
        owner_last_name: ownerLastName.trim() || undefined,
        owner_password: ownerPassword.trim() || undefined,
        owner_phone: ownerPhone.trim() || undefined,
        plan,
        initial_credits: Number(initialCredits) || 500,
        is_active: isActive,
      });

      setSuccessData({
        tenantName: res.tenant.name,
        ownerEmail: res.owner_user.email,
        temporaryPassword: res.temporary_password,
      });
      onCreated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create organization.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in overflow-y-auto">
      <div className="w-full max-w-2xl bg-[#0f172a] border border-slate-800 rounded-xl p-6 shadow-2xl my-8">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
          <div>
            <h3 className="text-base font-semibold text-white">Create & Activate New Organization</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Provision a new isolated tenant workspace and assign its primary owner account.
            </p>
          </div>
          <button
            onClick={handleClose}
            className="text-slate-400 hover:text-white text-lg px-2 py-1 rounded"
          >
            ✕
          </button>
        </div>

        {/* Success Banner */}
        {successData ? (
          <div className="space-y-4 py-2">
            <div className="p-4 rounded-lg bg-emerald-950/50 border border-emerald-500/40 text-emerald-300 space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-lg">🎉</span>
                <h4 className="font-semibold text-sm">Tenant Created Successfully!</h4>
              </div>
              <p className="text-xs leading-relaxed text-slate-200">
                Workspace <strong className="text-emerald-200">{successData.tenantName}</strong> has been provisioned. Primary owner account <strong className="text-emerald-200">{successData.ownerEmail}</strong> is configured with full OWNER permissions.
              </p>
              {successData.temporaryPassword && (
                <div className="mt-3 p-3 bg-black/40 rounded-lg border border-emerald-500/30 flex items-center justify-between">
                  <div>
                    <span className="text-[11px] text-slate-400 uppercase tracking-wider block">Generated Temporary Password</span>
                    <span className="text-sm font-mono text-emerald-300 font-bold">{successData.temporaryPassword}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleCopy(successData.temporaryPassword!)}
                    className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition-colors"
                  >
                    {copied ? "Copied!" : "Copy Password"}
                  </button>
                </div>
              )}
            </div>
            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={handleClose}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium"
              >
                Done
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
                {error}
              </div>
            )}

            {/* Section 1: Organization Details */}
            <div>
              <h4 className="text-xs font-semibold text-sky-400 uppercase tracking-wider mb-2">
                1. Organization Details
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-medium text-slate-300 block mb-1">
                    Organization / Company Name <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Acme Health Solutions"
                    className="admin-input w-full text-xs"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-300 block mb-1">
                    Workspace Slug (Optional)
                  </label>
                  <input
                    type="text"
                    value={slug}
                    onChange={(e) => setSlug(e.target.value)}
                    placeholder="e.g. acme-health"
                    className="admin-input w-full text-xs"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-300 block mb-1">
                    Business Email (Optional)
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="contact@acme.com"
                    className="admin-input w-full text-xs"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-300 block mb-1">
                    Business Phone (Optional)
                  </label>
                  <input
                    type="text"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+919876543210"
                    className="admin-input w-full text-xs"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="text-[11px] font-medium text-slate-300 block mb-1">
                    Description / Notes
                  </label>
                  <input
                    type="text"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Brief description of the organization or customer industry..."
                    className="admin-input w-full text-xs"
                  />
                </div>
              </div>
            </div>

            {/* Section 2: Primary Owner Account */}
            <div className="pt-2 border-t border-slate-800">
              <h4 className="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-2">
                2. Tenant Primary Owner Account
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-medium text-slate-300 block mb-1">
                    Owner Email <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="email"
                    required
                    value={ownerEmail}
                    onChange={(e) => setOwnerEmail(e.target.value)}
                    placeholder="owner@acme.com"
                    className="admin-input w-full text-xs"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-300 block mb-1">
                    Owner Phone (Optional)
                  </label>
                  <input
                    type="text"
                    value={ownerPhone}
                    onChange={(e) => setOwnerPhone(e.target.value)}
                    placeholder="+919876543210"
                    className="admin-input w-full text-xs"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-300 block mb-1">
                    Owner First Name <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={ownerFirstName}
                    onChange={(e) => setOwnerFirstName(e.target.value)}
                    placeholder="John"
                    className="admin-input w-full text-xs"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-300 block mb-1">
                    Owner Last Name
                  </label>
                  <input
                    type="text"
                    value={ownerLastName}
                    onChange={(e) => setOwnerLastName(e.target.value)}
                    placeholder="Doe"
                    className="admin-input w-full text-xs"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="text-[11px] font-medium text-slate-300 block mb-1">
                    Owner Password (Optional, leave blank to auto-generate)
                  </label>
                  <input
                    type="password"
                    value={ownerPassword}
                    onChange={(e) => setOwnerPassword(e.target.value)}
                    placeholder="Leave blank for secure auto-generated password"
                    className="admin-input w-full text-xs"
                  />
                </div>
              </div>
            </div>

            {/* Section 3: Plan & Credits */}
            <div className="pt-2 border-t border-slate-800">
              <h4 className="text-xs font-semibold text-purple-400 uppercase tracking-wider mb-2">
                3. Plan & Initial Allocation
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="text-[11px] font-medium text-slate-300 block mb-1">
                    Subscription Plan
                  </label>
                  <select
                    value={plan}
                    onChange={(e) => setPlan(e.target.value)}
                    className="admin-input w-full text-xs"
                  >
                    <option value="Standard">Standard / Starter</option>
                    <option value="Professional">Professional</option>
                    <option value="Enterprise">Enterprise Control</option>
                  </select>
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-300 block mb-1">
                    Initial AI Credits
                  </label>
                  <input
                    type="number"
                    min={0}
                    step={50}
                    value={initialCredits}
                    onChange={(e) => setInitialCredits(Number(e.target.value))}
                    className="admin-input w-full text-xs"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-300 block mb-1">
                    Initial Status
                  </label>
                  <select
                    value={isActive ? "active" : "suspended"}
                    onChange={(e) => setIsActive(e.target.value === "active")}
                    className="admin-input w-full text-xs"
                  >
                    <option value="active">Active & Operational</option>
                    <option value="suspended">Suspended / Inactive</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
              <button
                type="button"
                disabled={isLoading}
                onClick={handleClose}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="px-5 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-lg shadow-sky-600/30 transition-all flex items-center gap-2"
              >
                {isLoading ? "Provisioning..." : "Provision & Activate Tenant"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
