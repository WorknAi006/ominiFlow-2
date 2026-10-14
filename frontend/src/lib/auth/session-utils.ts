export const SESSION_COOKIE_NAME = "omniflow_session";

export interface TokenClaims {
  sub?: unknown;
  exp?: unknown;
}

export function readUnverifiedTokenClaims(token: string): TokenClaims | null {
  const payload = token.split(".")[1];
  if (!payload) return null;

  try {
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const decoded = atob(normalized);
    const bytes = Uint8Array.from(decoded, (character) => character.charCodeAt(0));
    const value: unknown = JSON.parse(new TextDecoder().decode(bytes));
    return value && typeof value === "object" ? (value as TokenClaims) : null;
  } catch {
    return null;
  }
}

export function tokenMaxAgeSeconds(token: string, nowSeconds = Date.now() / 1000) {
  const claims = readUnverifiedTokenClaims(token);
  if (typeof claims?.exp !== "number" || !Number.isFinite(claims.exp)) return null;
  const remaining = Math.floor(claims.exp - nowSeconds);
  return remaining > 0 ? remaining : null;
}

export function sessionCookieOptions(secure: boolean, maxAge: number) {
  return {
    httpOnly: true,
    secure,
    sameSite: "lax" as const,
    path: "/",
    maxAge,
  };
}

export function safeInternalPath(path: string | null | undefined) {
  if (!path || !path.startsWith("/") || path.startsWith("//") || path.includes("\\")) {
    return "/dashboard";
  }
  return path;
}
