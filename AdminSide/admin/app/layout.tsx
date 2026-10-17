import type { Metadata } from "next";
import { AdminAuthProvider } from "../lib/auth/context";
import { ThemeProvider } from "../lib/theme/context";
import "./globals.css";

export const metadata: Metadata = {
  title: "Omniflow Super Admin — Platform Control Plane",
  description: "Enterprise SaaS Platform Management for Omniflow",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                var t = localStorage.getItem('omniflow_admin_token');
                if (t && document.cookie.indexOf('omniflow_admin_token=') === -1) {
                  document.cookie = 'omniflow_admin_token=' + encodeURIComponent(t) + '; path=/; max-age=28800; SameSite=Lax';
                }
              } catch (e) {}
            `,
          }}
        />
      </head>
      <body className="antialiased bg-[#090d16] text-[#f8fafc]" suppressHydrationWarning>
        <ThemeProvider>
          <AdminAuthProvider>{children}</AdminAuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
