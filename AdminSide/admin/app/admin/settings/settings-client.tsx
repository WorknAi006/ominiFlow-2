"use client";

import React, { useEffect, useState } from "react";
import { adminApi } from "../../../lib/api/admin-client";
import { AdminSettings } from "../../../lib/types/admin";

interface SettingsClientProps {
  initialSettings: AdminSettings | null;
}

export function SettingsClient({ initialSettings }: SettingsClientProps) {
  const [settings, setSettings] = useState<AdminSettings | null>(initialSettings);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialSettings) return;
    async function load() {
      try {
        setLoading(true);
        const data = await adminApi.getSettings();
        setSettings(data);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load platform settings.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [initialSettings]);

  return (
    <div className="space-y-6">
      <div className="pb-4 border-b border-slate-800">
        <h2 className="text-xl font-bold tracking-tight text-white">Platform Settings & Configurations</h2>
        <p className="text-xs text-slate-400 mt-1">
          Global backend environment settings, cryptographic session controls and integration parameters.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
          {error}
        </div>
      )}

      {loading ? (
        <div className="h-64 bg-[#0f172a] rounded-xl border border-slate-800 animate-pulse" />
      ) : settings ? (
        <div className="space-y-6">
          {/* General Platform Config */}
          <div className="admin-card p-6 space-y-4">
            <h3 className="text-sm font-semibold text-white border-b border-slate-800 pb-2">
              Platform Environment
            </h3>
            <div className="space-y-3 text-xs">
              <div className="flex justify-between items-center py-1">
                <div>
                  <p className="font-medium text-slate-200">Application Name</p>
                  <p className="text-[11px] text-slate-400">Core SaaS instance identifier</p>
                </div>
                <span className="font-mono text-slate-300 bg-slate-800 px-2.5 py-1 rounded border border-slate-700">
                  {settings.app_name}
                </span>
              </div>

              <div className="flex justify-between items-center py-1 border-t border-slate-800/60">
                <div>
                  <p className="font-medium text-slate-200">Environment Mode</p>
                  <p className="text-[11px] text-slate-400">Current deployment lifecycle stage</p>
                </div>
                <span className="font-mono text-emerald-400 bg-emerald-950/40 border border-emerald-800/50 px-2.5 py-1 rounded uppercase">
                  {settings.app_env}
                </span>
              </div>

              <div className="flex justify-between items-center py-1 border-t border-slate-800/60">
                <div>
                  <p className="font-medium text-slate-200">Storage Backend</p>
                  <p className="text-[11px] text-slate-400">Inbound media file storage provider</p>
                </div>
                <span className="font-mono text-slate-300 bg-slate-800 px-2.5 py-1 rounded border border-slate-700">
                  {settings.media_storage_backend}
                </span>
              </div>
            </div>
          </div>

          {/* Authentication & Security Settings */}
          <div className="admin-card p-6 space-y-4">
            <h3 className="text-sm font-semibold text-white border-b border-slate-800 pb-2">
              Security & Tokens
            </h3>
            <div className="space-y-3 text-xs">
              <div className="flex justify-between items-center py-1">
                <div>
                  <p className="font-medium text-slate-200">JWT Token Expiration</p>
                  <p className="text-[11px] text-slate-400">Access token TTL before re-authentication</p>
                </div>
                <span className="font-mono text-slate-300 bg-slate-800 px-2.5 py-1 rounded border border-slate-700">
                  {settings.jwt_expire_minutes} minutes
                </span>
              </div>

              <div className="flex justify-between items-center py-1 border-t border-slate-800/60">
                <div>
                  <p className="font-medium text-slate-200">Max Automation Nodes</p>
                  <p className="text-[11px] text-slate-400">Execution graph complexity boundary</p>
                </div>
                <span className="font-mono text-slate-300 bg-slate-800 px-2.5 py-1 rounded border border-slate-700">
                  {settings.max_automation_nodes} nodes
                </span>
              </div>

              <div className="flex justify-between items-center py-1 border-t border-slate-800/60">
                <div>
                  <p className="font-medium text-slate-200">Meta Graph API Version</p>
                  <p className="text-[11px] text-slate-400">WhatsApp Cloud API protocol version</p>
                </div>
                <span className="font-mono text-sky-400 bg-slate-800 px-2.5 py-1 rounded border border-slate-700">
                  {settings.meta_graph_version}
                </span>
              </div>
            </div>
          </div>

          {/* Allowed CORS Origins */}
          <div className="admin-card p-6 space-y-3">
            <h3 className="text-sm font-semibold text-white">Configured Browser Origins (CORS)</h3>
            <p className="text-xs text-slate-400">
              Only requests from these origins are permitted to access authenticated APIs:
            </p>
            <div className="flex flex-wrap gap-2">
              {settings.allowed_origins.map((origin, idx) => (
                <span
                  key={idx}
                  className="font-mono text-xs px-2.5 py-1 rounded bg-slate-800 text-sky-300 border border-slate-700"
                >
                  {origin}
                </span>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
