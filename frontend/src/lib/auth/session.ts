import "server-only";

import { cookies } from "next/headers";

import { backendApiUrl, isRecord } from "@/lib/auth/backend";
import { readUnverifiedTokenClaims, SESSION_COOKIE_NAME } from "@/lib/auth/session-utils";

export interface AuthenticatedUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string | null;
  role: string;
  is_platform_super_admin: boolean;
}

export interface AuthenticatedTenant {
  id: string;
  name: string;
  slug: string;
}

export interface AuthContext {
  user: AuthenticatedUser;
  tenant: AuthenticatedTenant;
}

export class AuthBackendUnavailableError extends Error {
  constructor() {
    super("The workspace service is temporarily unavailable.");
    this.name = "AuthBackendUnavailableError";
  }
}

export async function getSessionAccessToken(): Promise<string | null> {
  const token = (await cookies()).get(SESSION_COOKIE_NAME)?.value;
  if (!token) return null;

  const claims = readUnverifiedTokenClaims(token);
  if (!claims || !isUuid(claims.sub) || typeof claims.exp !== "number" || claims.exp <= Date.now() / 1000) {
    return null;
  }
  return token;
}

function isUuid(value: unknown): value is string {
  return typeof value === "string" &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
}

async function authenticatedGet(path: string, token: string) {
  try {
    return await fetch(backendApiUrl(path), {
      headers: { Accept: "application/json", Authorization: `Bearer ${token}` },
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
  } catch {
    throw new AuthBackendUnavailableError();
  }
}

export async function getAuthContext(): Promise<AuthContext | null> {
  const token = await getSessionAccessToken();
  if (!token) return null;

  const claims = readUnverifiedTokenClaims(token);
  if (!claims || !isUuid(claims.sub)) {
    return null;
  }

  const [tenantResponse, userResponse, adminResponse] = await Promise.all([
    authenticatedGet("/tenants/current", token),
    authenticatedGet(`/users/${encodeURIComponent(claims.sub)}`, token),
    authenticatedGet("/auth/platform-admin/status", token),
  ]);

  if ([tenantResponse.status, userResponse.status, adminResponse.status].some((status) => status === 401 || status === 403 || status === 404)) {
    return null;
  }
  if (!tenantResponse.ok || !userResponse.ok || !adminResponse.ok) throw new AuthBackendUnavailableError();

  let tenant: unknown;
  let user: unknown;
  let adminStatus: unknown;
  try {
    [tenant, user, adminStatus] = await Promise.all([
      tenantResponse.json(),
      userResponse.json(),
      adminResponse.json(),
    ]);
  } catch {
    throw new AuthBackendUnavailableError();
  }
  if (
    !isRecord(tenant) || typeof tenant.id !== "string" || typeof tenant.name !== "string" ||
    typeof tenant.slug !== "string" || !isRecord(user) || typeof user.id !== "string" ||
    typeof user.email !== "string" || typeof user.first_name !== "string" ||
    !(typeof user.last_name === "string" || user.last_name === null) || typeof user.role !== "string" ||
    !isRecord(adminStatus) || typeof adminStatus.is_platform_super_admin !== "boolean"
  ) {
    throw new AuthBackendUnavailableError();
  }

  return {
    tenant: { id: tenant.id, name: tenant.name, slug: tenant.slug },
    user: {
      id: user.id,
      email: user.email,
      first_name: user.first_name,
      last_name: user.last_name,
      role: user.role,
      is_platform_super_admin: adminStatus.is_platform_super_admin,
    },
  };
}
