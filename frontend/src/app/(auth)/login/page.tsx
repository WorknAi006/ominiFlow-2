import { AuthForm } from "@/components/auth-form";
import { safeInternalPath } from "@/lib/auth/session-utils";
import { redirect } from "next/navigation";

interface LoginPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export const metadata = { referrer: "no-referrer" };

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const params = await searchParams;
  const hasCredentialQuery = Object.keys(params).some((key) =>
    /(email|password|passwd|token|secret|authorization|credential|api[_-]?key)/i.test(key),
  );
  if (hasCredentialQuery) redirect("/login");

  const destination = safeInternalPath(typeof params.next === "string" ? params.next : undefined);

  return (
    <div className="auth-card">
      <div className="auth-heading">
        <span className="auth-icon" aria-hidden="true">↗</span>
        <p className="eyebrow mt-6">WELCOME BACK</p>
        <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">Sign in to your workspace</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">Pick up where your team left off.</p>
      </div>

      {params.registered === "1" && (
        <p role="status" className="status-message mt-6">Your workspace is ready. Sign in with the account you just created.</p>
      )}
      {params.reason === "session-expired" && (
        <p role="status" className="status-message status-message-neutral mt-6">Your session has expired. Sign in again to continue.</p>
      )}

      <div className="mt-7"><AuthForm mode="login" destination={destination} /></div>
      <p className="mt-6 text-center text-xs text-slate-500">Secure access for your Omniflow workspace</p>
    </div>
  );
}
