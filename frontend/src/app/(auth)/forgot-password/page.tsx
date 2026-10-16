import { PasswordResetRequestForm } from "@/components/auth/password-reset-request-form";

export const metadata = { referrer: "no-referrer" };

export default function ForgotPasswordPage() {
  return (
    <div className="auth-card">
      <div className="auth-heading">
        <span className="auth-icon" aria-hidden="true">?</span>
        <p className="eyebrow mt-6">ACCOUNT RECOVERY</p>
        <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">Request a password reset</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          A platform administrator will review your request. If approved, you will receive a secure reset link by email.
        </p>
      </div>
      <PasswordResetRequestForm />
    </div>
  );
}
