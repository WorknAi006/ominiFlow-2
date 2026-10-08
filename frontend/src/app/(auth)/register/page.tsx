import { AuthForm } from "@/components/auth-form";

export default function RegisterPage() {
  return (
    <div className="auth-card auth-card-register">
      <div className="auth-heading">
        <span className="auth-icon" aria-hidden="true">＋</span>
        <p className="eyebrow mt-6">A BETTER WAY TO CONNECT</p>
        <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">Create your workspace</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">Start with your team and the workspace you&apos;ll share.</p>
      </div>
      <div className="mt-7"><AuthForm mode="register" /></div>
      <p className="mt-6 text-center text-xs text-slate-500">You&apos;ll sign in after creating your workspace.</p>
    </div>
  );
}
