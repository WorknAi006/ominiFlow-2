"use client";

import React, { useEffect, useState } from "react";
import { adminApi } from "../../../lib/api/admin-client";
import { StatusBadge } from "../../../components/badges/status-badge";

interface WebhookEndpoint {
  provider: string;
  path: string;
  status: string;
  subscribed_events: string[];
  total_received: number;
  processed: number;
  failed: number;
}

export default function WebhooksPage() {
  const [endpoints, setEndpoints] = useState<WebhookEndpoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const res = await adminApi.getWebhooks();
        setEndpoints(res.endpoints);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load webhook monitors.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="space-y-6">
      <div className="pb-4 border-b border-slate-800">
        <h2 className="text-xl font-bold tracking-tight text-white">Webhook Ingestion Hub</h2>
        <p className="text-xs text-slate-400 mt-1">
          Inbound provider webhook health, payload signature verification and event delivery metrics.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
          {error}
        </div>
      )}

      {loading ? (
        <div className="h-48 bg-[#0f172a] rounded-xl border border-slate-800 animate-pulse" />
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {endpoints.map((ep, i) => (
              <div key={i} className="admin-card p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-white">{ep.provider}</h3>
                  <StatusBadge status={ep.status} />
                </div>

                <div className="space-y-2 text-xs">
                  <div className="flex justify-between py-1 border-b border-slate-800/60">
                    <span className="text-slate-400">Callback Endpoint Path</span>
                    <span className="font-mono text-sky-400 font-semibold">{ep.path}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800/60">
                    <span className="text-slate-400">Total Ingested Events</span>
                    <span className="font-mono text-slate-200">{ep.total_received}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800/60">
                    <span className="text-slate-400">Successfully Processed</span>
                    <span className="font-mono text-emerald-400 font-semibold">{ep.processed}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800/60">
                    <span className="text-slate-400">Failed / Retried Events</span>
                    <span className="font-mono text-rose-400 font-semibold">{ep.failed}</span>
                  </div>
                </div>

                <div className="pt-2">
                  <span className="text-[10px] uppercase font-bold text-slate-500 block mb-1">
                    Subscribed Webhook Fields
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {ep.subscribed_events.map((evt, idx) => (
                      <span
                        key={idx}
                        className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300"
                      >
                        {evt}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="admin-card p-6">
            <h3 className="text-sm font-semibold text-white mb-2">Meta Signature Security Protocol</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Every incoming POST request to WhatsApp webhooks is required to carry the{" "}
              <code className="text-sky-400 font-mono">X-Hub-Signature-256</code> header. Omniflow validates
              the HMAC-SHA256 signature in constant time using your configured Meta App Secret before parsing the
              payload body. Payloads exceeding 1MB or with invalid signatures are rejected with HTTP 403.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
