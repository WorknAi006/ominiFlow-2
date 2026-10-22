import type { NextConfig } from "next";

const backendUrl = (
  process.env.OMNIFLOW_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: false,
  devIndicators: false,
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ];
  },
  async redirects() {
    return [
      {
        source: "/dashboard",
        destination: "/admin/dashboard",
        permanent: false,
      },
      {
        source: "/tenants",
        destination: "/admin/tenants",
        permanent: false,
      },
      {
        source: "/tenants/:id",
        destination: "/admin/tenants/:id",
        permanent: false,
      },
      {
        source: "/users",
        destination: "/admin/users",
        permanent: false,
      },
      {
        source: "/users/:id",
        destination: "/admin/users/:id",
        permanent: false,
      },
      {
        source: "/channels",
        destination: "/admin/channels",
        permanent: false,
      },
      {
        source: "/conversations",
        destination: "/admin/conversations",
        permanent: false,
      },
      {
        source: "/system-health",
        destination: "/admin/system-health",
        permanent: false,
      },
      {
        source: "/security",
        destination: "/admin/security",
        permanent: false,
      },
      {
        source: "/audit-logs",
        destination: "/admin/audit-logs",
        permanent: false,
      },
      {
        source: "/api-usage",
        destination: "/admin/api-usage",
        permanent: false,
      },
      {
        source: "/plans",
        destination: "/admin/plans",
        permanent: false,
      },
      {
        source: "/billing",
        destination: "/admin/billing",
        permanent: false,
      },
      {
        source: "/settings",
        destination: "/admin/settings",
        permanent: false,
      },
      {
        source: "/webhooks",
        destination: "/admin/webhooks",
        permanent: false,
      },
      {
        source: "/maintenance",
        destination: "/admin/maintenance",
        permanent: false,
      },
      {
        source: "/admin",
        destination: "/admin/dashboard",
        permanent: false,
      },
      {
        source: "/login",
        destination: "/admin/login",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
