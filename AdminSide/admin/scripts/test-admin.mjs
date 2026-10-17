import assert from "node:assert/strict";
import { describe, it } from "node:test";

const API_BASE = "http://127.0.0.1:8000/api/v1";

describe("Omniflow Super Admin API & Authorization", () => {
  let adminToken = "";

  it("rejects login with invalid credentials with 401 Unauthorized", async () => {
    const res = await fetch(`${API_BASE}/admin/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: "invalid@omniflow.io", password: "wrong-password" }),
    });
    assert.equal(res.status, 401);
  });

  it("authenticates valid platform super admin and returns JWT with is_platform_admin", async () => {
    const res = await fetch(`${API_BASE}/admin/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: "admin@omniflow.io", password: "OmniflowAdmin2026!" }),
    });
    assert.equal(res.status, 200);
    const data = await res.json();
    assert.ok(data.access_token);
    assert.equal(data.user.email, "admin@omniflow.io");
    assert.equal(data.user.is_platform_admin, true);
    adminToken = data.access_token;
  });

  it("unauthenticated requests to /admin/dashboard are rejected with 401", async () => {
    const res = await fetch(`${API_BASE}/admin/dashboard`);
    assert.equal(res.status, 401);
  });

  it("authenticated super admin accesses /admin/dashboard with real statistics", async () => {
    const res = await fetch(`${API_BASE}/admin/dashboard`, {
      headers: { Authorization: `Bearer ${adminToken}` },
    });
    assert.equal(res.status, 200);
    const data = await res.json();
    assert.equal(typeof data.total_tenants, "number");
    assert.equal(typeof data.total_users, "number");
    assert.equal(data.database_status, "healthy");
    assert.equal(data.redis_status, "healthy");
  });

  it("authenticated super admin can list tenants", async () => {
    const res = await fetch(`${API_BASE}/admin/tenants`, {
      headers: { Authorization: `Bearer ${adminToken}` },
    });
    assert.equal(res.status, 200);
    const data = await res.json();
    assert.ok(Array.isArray(data.items));
    assert.equal(typeof data.total, "number");
  });

  it("authenticated super admin can list users", async () => {
    const res = await fetch(`${API_BASE}/admin/users`, {
      headers: { Authorization: `Bearer ${adminToken}` },
    });
    assert.equal(res.status, 200);
    const data = await res.json();
    assert.ok(Array.isArray(data.items));
    assert.ok(data.items.length >= 1);
  });

  it("authenticated super admin can inspect system health", async () => {
    const res = await fetch(`${API_BASE}/admin/system-health`, {
      headers: { Authorization: `Bearer ${adminToken}` },
    });
    assert.equal(res.status, 200);
    const data = await res.json();
    assert.ok(["healthy", "warning", "degraded"].includes(data.overall_status));
    assert.ok(data.components.length >= 3);
  });

  it("authenticated super admin can inspect webhooks and audit logs", async () => {
    const [webhooksRes, auditRes] = await Promise.all([
      fetch(`${API_BASE}/admin/webhooks`, { headers: { Authorization: `Bearer ${adminToken}` } }),
      fetch(`${API_BASE}/admin/audit-logs`, { headers: { Authorization: `Bearer ${adminToken}` } }),
    ]);
    assert.equal(webhooksRes.status, 200);
    assert.equal(auditRes.status, 200);
  });
});
