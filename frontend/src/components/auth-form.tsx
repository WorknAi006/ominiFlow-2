"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { validateLogin, validateRegistration } from "@/lib/auth/validation";

interface AuthFormProps {
  mode: "login" | "register";
  destination?: string;
}

interface AuthApiResponse {
  error?: string;
}

export function AuthForm({ mode, destination = "/dashboard" }: AuthFormProps) {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const isRegister = mode === "register";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "");
    const password = String(form.get("password") ?? "");
    const validationError = isRegister
      ? validateRegistration({
          email,
          password,
          confirmPassword: String(form.get("confirm_password") ?? ""),
          firstName: String(form.get("first_name") ?? ""),
          lastName: String(form.get("last_name") ?? ""),
          tenantName: String(form.get("tenant_name") ?? ""),
        })
      : validateLogin(email, password);

    if (validationError) {
      setError(validationError);
      return;
    }

    setIsSubmitting(true);
    try {
      const endpoint = isRegister ? "/api/auth/register" : "/api/auth/login";
      const body = isRegister
        ? {
            email,
            password,
            first_name: String(form.get("first_name") ?? "").trim(),
            last_name: String(form.get("last_name") ?? "").trim() || null,
            tenant_name: String(form.get("tenant_name") ?? "").trim(),
          }
        : { email, password };

      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(body),
      });
      const payload = (await response.json().catch(() => ({}))) as AuthApiResponse;

      if (!response.ok) {
        setError(payload.error ?? "Something went wrong. Please try again.");
        return;
      }

      if (isRegister) {
        router.replace("/login?registered=1");
      } else {
        router.replace(destination);
        router.refresh();
      }
    } catch {
      setError("We could not reach the service. Check your connection and try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5" noValidate>
      {isRegister && (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="First name" name="first_name" autoComplete="given-name" required maxLength={100} />
            <Field label="Last name" name="last_name" autoComplete="family-name" maxLength={100} />
          </div>
          <Field label="Workspace name" name="tenant_name" autoComplete="organization" required minLength={2} maxLength={150} />
        </>
      )}
      <Field label="Work email" name="email" type="email" autoComplete="email" required maxLength={320} />
      <Field
        label="Password"
        name="password"
        type="password"
        autoComplete={isRegister ? "new-password" : "current-password"}
        required
        minLength={isRegister ? 8 : 1}
        maxLength={128}
      />
      {isRegister && (
        <Field label="Confirm password" name="confirm_password" type="password" autoComplete="new-password" required minLength={8} maxLength={128} />
      )}

      {error && (
        <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={isSubmitting}
        className="inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-[#176b59] px-5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#125747] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#176b59] disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isSubmitting ? "Please wait…" : isRegister ? "Create workspace" : "Sign in"}
      </button>

      <p className="text-center text-sm text-slate-600">
        {isRegister ? "Already have an account? " : "New to Omniflow? "}
        <Link className="font-semibold text-[#176b59] underline-offset-4 hover:underline" href={isRegister ? "/login" : "/register"}>
          {isRegister ? "Sign in" : "Create an account"}
        </Link>
      </p>
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
  const id = `auth-${name}`;
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
