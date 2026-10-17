import { AcceptInviteForm } from "@/components/team/accept-invite-form";

interface AcceptPageProps {
  searchParams: Promise<{ token?: string | string[] }>;
}

// Referrer is suppressed so the invitation token in the URL is never leaked
// to third parties via the Referer header.
export const metadata = { referrer: "no-referrer" as const };

export default async function AcceptInvitePage({ searchParams }: AcceptPageProps) {
  const params = await searchParams;
  const token = typeof params.token === "string" ? params.token : "";

  return (
    <div className="auth-card">
      <div className="auth-heading">
        <span className="auth-icon" aria-hidden="true">↗</span>
        <p className="eyebrow mt-6">JOIN THE WORKSPACE</p>
        <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">Accept your invitation</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">Set a password to join your team on Omniflow.</p>
      </div>

      {token ? (
        <div className="mt-7"><AcceptInviteForm token={token} /></div>
      ) : (
        <p role="alert" className="status-message status-message-neutral mt-6">
          This invitation link is missing its token. Please use the link from your invitation email.
        </p>
      )}
    </div>
  );
}
