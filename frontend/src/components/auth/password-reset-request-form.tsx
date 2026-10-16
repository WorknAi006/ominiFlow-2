"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

export function PasswordResetRequestForm() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      const response = await fetch("/api/auth/password-reset-request", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ email: String(form.get("email") ?? "").trim() }),
      });
      const payload: unknown = await response.json().catch(() => null);
      if (!response.ok) {
        setError(payload && typeof payload === "object" && "error" in payload && typeof payload.error === "string"
          ? payload.error : "Could not submit your request. Please try again.");
        return;
      }
      setSubmitted(true);
    } catch {
      setError("Could not reach the service. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-7">
      {submitted ? (
        <p role="status" className="status-message">
          If an active account matches that email, a platform administrator will review the password reset request.
        </p>
      ) : (
        <form onSubmit={submit} className="space-y-5">
          <label htmlFor="reset-request-email" className="block text-sm font-medium text-slate-700">Work email</label>
          <input
            id="reset-request-email"
            name="email"
            type="email"
            autoComplete="email"
            required
            maxLength={320}
            className="min-h-12 w-full rounded-xl border border-slate-200 px-3.5 text-[15px] text-slate-900 outline-none focus:border-[#258672] focus:ring-4 focus:ring-[#258672]/10"
          />
          {error && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</p>}
          <button
            type="submit"
            disabled={busy}
            className="inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-[#176b59] px-5 text-sm font-semibold text-white disabled:opacity-60"
          >
            {busy ? "Submitting…" : "Request password reset"}
          </button>
        </form>
      )}
      <p className="mt-6 text-center text-sm text-slate-600">
        <Link className="font-semibold text-[#176b59] hover:underline" href="/login">Back to sign in</Link>
      </p>
    </div>
  );
}
