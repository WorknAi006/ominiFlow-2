import { ResetPasswordForm } from "@/components/auth/reset-password-form";
import Link from "next/link";

interface ResetPasswordPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export const metadata = { referrer: "no-referrer" };

export default async function ResetPasswordPage({ searchParams }: ResetPasswordPageProps) {
  const params = await searchParams;
  const token = typeof params.token === "string" ? params.token : "";
  return (
    <div className="auth-card">
      <div className="auth-heading">
        <span className="auth-icon" aria-hidden="true">↻</span>
        <p className="eyebrow mt-6">ACCOUNT RECOVERY</p>
        <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">Choose a new password</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">Reset links can only be used once and expire after one hour.</p>
      </div>
      {token.length >= 32 && token.length <= 256
        ? <ResetPasswordForm token={token} />
        : <div className="mt-7">
            <p role="alert" className="status-message">This password reset link is missing or invalid.</p>
            <Link href="/forgot-password" className="mt-4 block text-center text-sm font-semibold text-[#176b59] hover:underline">Request a new reset link</Link>
          </div>}
    </div>
  );
}
