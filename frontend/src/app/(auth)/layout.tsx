import type { ReactNode } from "react";
import Link from "next/link";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <main className="auth-page">
      <section className="auth-story" aria-label="About Omniflow">
        <Link className="brand-lockup brand-lockup-light" href="/login">
          <span className="brand-mark brand-mark-light" aria-hidden="true">o</span>
          <span>omniflow</span>
        </Link>
        <div className="auth-story-content">
          <span className="story-kicker"><span className="story-kicker-dot" /> CUSTOMER CONVERSATIONS, IN SYNC</span>
          <h1>Every conversation.<br />One thoughtful<br /><span>workspace.</span></h1>
          <p>Give your team a clearer way to connect with customers across the channels they already use.</p>
          <div className="story-ornament" aria-hidden="true">
            <span className="story-orbit story-orbit-a" /><span className="story-orbit story-orbit-b" />
            <span className="story-center">o</span><span className="story-dot story-dot-a" /><span className="story-dot story-dot-b" />
          </div>
        </div>
        <p className="auth-story-footer">Built for the teams behind every great customer experience.</p>
      </section>

      <section className="auth-panel">
        <div className="auth-panel-top"><span>OMNIFLOW</span><span>WORKSPACE ACCESS</span></div>
        {children}
        <p className="auth-legal">By continuing, you agree to use Omniflow in accordance with your organization&apos;s policies.</p>
      </section>
    </main>
  );
}
