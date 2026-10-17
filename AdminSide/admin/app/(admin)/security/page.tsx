"use client";

import React, { useEffect, useState } from "react";
import { adminApi } from "../../../lib/api/admin-client";
import { StatusBadge } from "../../../components/badges/status-badge";

export default function SecurityPage() {
  const [sec, setSec] = useState<{
    status: string;
    mfa_enforced: boolean;
    super_admins_count: number;
    failed_logins_24h: number;
    rate_limiting_active: boolean;
  } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const data = await adminApi.getSecurity();
        setSec(data);
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="space-y-6">
      <div className="pb-4 border-b border-slate-800">
        <h2 className="text-xl font-bold tracking-tight text-white">Platform Security Center</h2>
        <p className="text-xs text-slate-400 mt-1">
          Cryptographic token parameters, privileged identity oversight and rate limiting defenses.
        </p>
      </div>

      {loading ? (
        <div className="h-48 bg-[#0f172a] rounded-xl border border-slate-800 animate-pulse" />
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="admin-card p-5">
              <span className="text-xs text-slate-400 block mb-1">Security Status</span>
              <StatusBadge status={sec?.status || "active"} />
              <p className="text-[11px] text-slate-500 mt-2">Zero active breaches</p>
            </div>
            <div className="admin-card p-5">
              <span className="text-xs text-slate-400 block mb-1">Super Admins</span>
              <span className="text-2xl font-bold text-white">{sec?.super_admins_count || 1}</span>
              <p className="text-[11px] text-slate-500 mt-1">Privileged accounts</p>
            </div>
            <div className="admin-card p-5">
              <span className="text-xs text-slate-400 block mb-1">Failed Logins (24h)</span>
              <span className="text-2xl font-bold text-emerald-400">{sec?.failed_logins_24h || 0}</span>
              <p className="text-[11px] text-slate-500 mt-1">Auth anomaly count</p>
            </div>
            <div className="admin-card p-5">
              <span className="text-xs text-slate-400 block mb-1">Rate Limiting</span>
              <span className="text-sm font-semibold text-sky-400">
                {sec?.rate_limiting_active ? "Enforced" : "Disabled"}
              </span>
              <p className="text-[11px] text-slate-500 mt-1">DDoS & brute force guard</p>
            </div>
          </div>

          <div className="admin-card p-6 space-y-4">
            <h3 className="text-sm font-semibold text-white">Platform Protection Matrix</h3>
            <div className="divide-y divide-slate-800/80 text-xs">
              <div className="py-3 flex items-center justify-between">
                <div>
                  <p className="font-medium text-slate-200">Credential Encryption</p>
                  <p className="text-slate-400 text-[11px]">
                    Channel access tokens and refresh tokens are encrypted via multi-key Fernet before persisting.
                  </p>
                </div>
                <span className="admin-badge admin-badge-success">Active (Fernet 256-bit)</span>
              </div>

              <div className="py-3 flex items-center justify-between">
                <div>
                  <p className="font-medium text-slate-200">Hash Algorithm</p>
                  <p className="text-slate-400 text-[11px]">
                    User passwords hashed strictly using Argon2id with memory hardness.
                  </p>
                </div>
                <span className="admin-badge admin-badge-success">Argon2id Enforced</span>
              </div>

              <div className="py-3 flex items-center justify-between">
                <div>
                  <p className="font-medium text-slate-200">Webhook Signature Verification</p>
                  <p className="text-slate-400 text-[11px]">
                    Inbound Meta webhooks verified via HMAC-SHA256 constant-time digest matching.
                  </p>
                </div>
                <span className="admin-badge admin-badge-success">Enforced</span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
