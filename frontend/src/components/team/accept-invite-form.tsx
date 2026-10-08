"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

interface AcceptApiResponse {
  error?: string;
}

export function AcceptInviteForm({ token }: { token: string }) {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    const form = new FormData(event.currentTarget);
    const password = String(form.get("password") ?? "");
    const confirm = String(form.get("confirm_password") ?? "");
    const firstName = String(form.get("first_name") ?? "").trim();
    const lastName = String(form.get("last_name") ?? "").trim();

    if (password.length < 8) return setError("Your password must be at least 8 characters.");
    if (password !== confirm) return setError("The two passwords do not match.");

    setSubmitting(true);
    try {
      const response = await fetch("/api/auth/accept", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          token,
          password,
          first_name: firstName || undefined,
          last_name: lastName || undefined,
        }),
      });
      const payload = (await response.json().catch(() => ({}))) as AcceptApiResponse;
      if (!response.ok) {
        setError(payload.error ?? "This invitation could not be accepted.");
        return;
      }
      router.replace("/dashboard");
      router.refresh();
    } catch {
      setError("We could not reach the service. Check your connection and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5" noValidate>
      <p className="text-sm leading-6 text-slate-600">
        If you are new to Omniflow, enter your name below. Returning users can leave the name fields blank and use their existing password.
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="First name" name="first_name" autoComplete="given-name" maxLength={100} />
        <Field label="Last name" name="last_name" autoComplete="family-name" maxLength={100} />
      </div>
      <Field label="Password" name="password" type="password" autoComplete="new-password" required minLength={8} maxLength={128} />
      <Field label="Confirm password" name="confirm_password" type="password" autoComplete="new-password" required minLength={8} maxLength={128} />

      {error && (
        <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</p>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-[#176b59] px-5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#125747] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#176b59] disabled:cursor-not-allowed disabled:opacity-60"
      >
        {submitting ? "Please wait…" : "Accept invitation"}
      </button>
    </form>
  );
}

interface FieldProps {
  label: string;
  name: string;
  type?: string;
  autoComplete?: string;
  required?: boolean;
  minLength?: number;
  maxLength?: number;
}

function Field({ label, name, type = "text", ...props }: FieldProps) {
  const id = `accept-${name}`;
  return (
    <div className="space-y-2">
      <label htmlFor={id} className="block text-sm font-medium text-slate-700">{label}</label>
      <input
        id={id}
        name={name}
        type={type}
        className="min-h-12 w-full rounded-xl border border-slate-200 bg-white px-3.5 text-[15px] text-slate-900 outline-none transition placeholder:text-slate-400 hover:border-slate-300 focus:border-[#258672] focus:ring-4 focus:ring-[#258672]/10"
        {...props}
      />
    </div>
  );
}
