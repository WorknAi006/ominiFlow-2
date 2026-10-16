"use client";

import { useCallback, useEffect, useState } from "react";

interface ResetRequest {
  id: string;
  email: string;
  status: string;
  requested_at: string;
}

export function PasswordResetAdmin() {
  const [requests, setRequests] = useState<ResetRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const fetchRequests = useCallback(async () => {
    const response = await fetch("/api/auth/platform-admin/password-reset-requests", { cache: "no-store" });
    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(payload && typeof payload === "object" && "error" in payload && typeof payload.error === "string"
        ? payload.error : "Could not load reset requests.");
    }
    if (!Array.isArray(payload)) return [];
    return payload.flatMap((item): ResetRequest[] =>
      item && typeof item === "object" &&
      "id" in item && typeof item.id === "string" &&
      "email" in item && typeof item.email === "string" &&
      "status" in item && typeof item.status === "string" &&
      "requested_at" in item && typeof item.requested_at === "string"
        ? [{ id: item.id, email: item.email, status: item.status, requested_at: item.requested_at }]
        : []);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setRequests(await fetchRequests());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not load reset requests.");
    } finally {
      setLoading(false);
    }
  }, [fetchRequests]);

  useEffect(() => {
    let active = true;
    void fetchRequests()
      .then((items) => { if (active) setRequests(items); })
      .catch((cause: unknown) => { if (active) setError(cause instanceof Error ? cause.message : "Could not load reset requests."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [fetchRequests]);

  async function approve(request: ResetRequest) {
    setBusyId(request.id);
    setError("");
    setNotice("");
    try {
      const response = await fetch(`/api/auth/platform-admin/password-reset-requests/${encodeURIComponent(request.id)}/approve`, {
        method: "POST",
      });
      const payload: unknown = response.status === 204 ? null : await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(payload && typeof payload === "object" && "error" in payload && typeof payload.error === "string"
          ? payload.error : "Could not approve this reset request.");
      }
      setRequests((current) => current.filter((item) => item.id !== request.id));
      setNotice(`A one-time reset link was emailed to ${request.email}.`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not approve this reset request.");
    } finally {
      setBusyId("");
    }
  }

  return (
    <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Pending requests</h2>
          <p className="mt-1 text-sm text-slate-600">Approving sends a single-use reset link to that account&apos;s email.</p>
        </div>
        <button type="button" onClick={() => void load()} disabled={loading} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium disabled:opacity-50">
          Refresh
        </button>
      </div>
      {error && <p role="alert" className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
      {notice && <p role="status" className="mt-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</p>}
      {loading ? <p className="py-6 text-sm text-slate-500">Loading requests…</p> : requests.length === 0 ? (
        <p className="py-6 text-sm text-slate-500">No pending password reset requests.</p>
      ) : (
        <ul className="mt-4 divide-y divide-slate-100">
          {requests.map((request) => (
            <li key={request.id} className="flex flex-wrap items-center justify-between gap-4 py-4">
              <div>
                <p className="font-medium text-slate-900">{request.email}</p>
                <p className="mt-1 text-xs text-slate-500">Requested {new Date(request.requested_at).toLocaleString()}</p>
              </div>
              <button
                type="button"
                disabled={Boolean(busyId)}
                onClick={() => void approve(request)}
                className="rounded-lg bg-[#176b59] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
              >
                {busyId === request.id ? "Sending…" : "Approve and email link"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
