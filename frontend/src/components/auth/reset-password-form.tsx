"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

export function ResetPasswordForm({ token }: { token: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [complete, setComplete] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      const response = await fetch("/api/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          token,
          password: String(form.get("password") ?? ""),
          confirm_password: String(form.get("confirm_password") ?? ""),
        }),
      });
      const payload: unknown = await response.json().catch(() => null);
      if (!response.ok) {
        setError(payload && typeof payload === "object" && "error" in payload && typeof payload.error === "string"
          ? payload.error : "Could not reset your password.");
        return;
      }
      setComplete(true);
      router.replace("/login?reset=1");
    } catch {
      setError("Could not reach the service. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  if (complete) {
    return <p role="status" className="status-message mt-7">Password reset. Sign in with your new password.</p>;
  }

  return (
    <form onSubmit={submit} className="mt-7 space-y-5">
      <label className="block text-sm font-medium text-slate-700" htmlFor="new-password">New password</label>
      <input
        id="new-password"
        name="password"
        type="password"
        autoComplete="new-password"
        required
        minLength={8}
        maxLength={128}
        className="min-h-12 w-full rounded-xl border border-slate-200 px-3.5 text-[15px] text-slate-900 outline-none focus:border-[#258672] focus:ring-4 focus:ring-[#258672]/10"
      />
      <label className="block text-sm font-medium text-slate-700" htmlFor="confirm-password">Confirm new password</label>
      <input
        id="confirm-password"
        name="confirm_password"
        type="password"
        autoComplete="new-password"
        required
        minLength={8}
        maxLength={128}
        className="min-h-12 w-full rounded-xl border border-slate-200 px-3.5 text-[15px] text-slate-900 outline-none focus:border-[#258672] focus:ring-4 focus:ring-[#258672]/10"
      />
      {error && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</p>}
      <button type="submit" disabled={busy} className="inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-[#176b59] px-5 text-sm font-semibold text-white disabled:opacity-60">
        {busy ? "Updating…" : "Set new password"}
      </button>
      <p className="text-center text-sm text-slate-600">
        <Link className="font-semibold text-[#176b59] hover:underline" href="/login">Back to sign in</Link>
      </p>
    </form>
  );
}
