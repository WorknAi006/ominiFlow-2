// Server-side allowlist for the Channel Management proxy. Mirrors the
// inbox proxy: only enumerated backend paths, methods, filters and request
// shapes are forwarded. Secrets (access tokens) are forwarded but never
// logged by the route handler. Kept free of framework imports so it can be
// unit-tested in isolation.

export const CHANNEL_TYPES = ["whatsapp", "instagram", "facebook", "web_chat"] as const;
export const CHANNEL_STATUSES = [
  "pending",
  "connected",
  "disconnected",
  "error",
  "revoked",
] as const;

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const EXTERNAL_ID_PATTERN = /^[A-Za-z0-9._:@+-]{1,255}$/;
const META_ID_PATTERN = /^[0-9]{1,32}$/;

export type ProxyMethod = "GET" | "POST" | "PATCH" | "DELETE";

export interface ChannelProxyTarget {
  backendPath: string;
  method: ProxyMethod;
  query: URLSearchParams;
  body?: Record<string, unknown>;
  expectsNoContent?: boolean;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function positiveInt(value: string | null, fallback: number, maximum: number) {
  if (value === null) return fallback;
  if (!/^\d+$/.test(value)) return null;
  const number = Number(value);
  return number >= 1 && number <= maximum ? number : null;
}

function copyListFilters(params: URLSearchParams, allowed: Set<string>): URLSearchParams | null {
  const query = new URLSearchParams();
  for (const key of params.keys()) if (!allowed.has(key)) return null;

  const page = positiveInt(params.get("page"), 1, 1_000_000);
  const pageSize = positiveInt(params.get("page_size"), 20, 100);
  if (page === null || pageSize === null) return null;
  query.set("page", String(page));
  query.set("page_size", String(pageSize));

  const search = params.get("search");
  if (search !== null) {
    if (search.length > 100) return null;
    if (search) query.set("search", search);
  }
  return query;
}

function buildCreateBody(body: unknown): Record<string, unknown> | null {
  if (!isRecord(body)) return null;
  const allowed = new Set(["channel_type", "name", "external_account_id", "external_business_id"]);
  for (const key of Object.keys(body)) if (!allowed.has(key)) return null;

  const { channel_type, name } = body;
  if (typeof channel_type !== "string" || !(CHANNEL_TYPES as readonly string[]).includes(channel_type)) return null;
  if (typeof name !== "string") return null;
  const trimmed = name.trim();
  if (trimmed.length < 2 || trimmed.length > 150) return null;

  const out: Record<string, unknown> = { channel_type, name: trimmed };
  for (const key of ["external_account_id", "external_business_id"] as const) {
    const value = body[key];
    if (value === undefined) continue;
    if (typeof value !== "string" || !EXTERNAL_ID_PATTERN.test(value)) return null;
    out[key] = value;
  }
  return out;
}

function buildUpdateBody(body: unknown): Record<string, unknown> | null {
  if (!isRecord(body)) return null;
  const allowed = new Set(["name", "is_active"]);
  const keys = Object.keys(body);
  if (keys.length === 0) return null;
  for (const key of keys) if (!allowed.has(key)) return null;

  const out: Record<string, unknown> = {};
  if ("name" in body) {
    if (typeof body.name !== "string") return null;
    const trimmed = body.name.trim();
    if (trimmed.length < 2 || trimmed.length > 150) return null;
    out.name = trimmed;
  }
  if ("is_active" in body) {
    if (typeof body.is_active !== "boolean") return null;
    out.is_active = body.is_active;
  }
  return out;
}

function buildConnectBody(body: unknown): Record<string, unknown> | null {
  if (!isRecord(body)) return null;
  const allowed = new Set(["phone_number_id", "waba_id", "access_token", "code"]);
  for (const key of Object.keys(body)) if (!allowed.has(key)) return null;

  const { phone_number_id, waba_id, access_token, code } = body;
  const hasAccessToken = typeof access_token === "string" && access_token.length >= 1 && access_token.length <= 4096;
  const hasCode = typeof code === "string" && code.length >= 1 && code.length <= 4096;
  if (hasAccessToken === hasCode) return null;

  const out: Record<string, unknown> = hasAccessToken ? { access_token } : { code };

  if (hasAccessToken) {
    if (typeof phone_number_id !== "string" || !META_ID_PATTERN.test(phone_number_id)) return null;
    if (typeof waba_id !== "string" || !META_ID_PATTERN.test(waba_id)) return null;
    out.phone_number_id = phone_number_id;
    out.waba_id = waba_id;
  } else {
    if (phone_number_id !== undefined) {
      if (typeof phone_number_id !== "string" || !META_ID_PATTERN.test(phone_number_id)) return null;
      out.phone_number_id = phone_number_id;
    }
    if (waba_id !== undefined) {
      if (typeof waba_id !== "string" || !META_ID_PATTERN.test(waba_id)) return null;
      out.waba_id = waba_id;
    }
  }

  return out;
}

function buildFacebookConnectBody(body: unknown): Record<string, unknown> | null {
  if (!isRecord(body)) return null;
  const allowed = new Set(["page_id", "access_token"]);
  for (const key of Object.keys(body)) if (!allowed.has(key)) return null;

  const { page_id, access_token } = body;
  if (typeof page_id !== "string" || !META_ID_PATTERN.test(page_id)) return null;
  if (typeof access_token !== "string" || access_token.length < 1 || access_token.length > 4096) return null;
  return { page_id, access_token };
}

function buildInstagramConnectBody(body: unknown): Record<string, unknown> | null {
  if (!isRecord(body)) return null;
  const allowed = new Set(["instagram_id", "page_id", "access_token"]);
  for (const key of Object.keys(body)) if (!allowed.has(key)) return null;

  const { instagram_id, page_id, access_token } = body;
  if (typeof instagram_id !== "string" || !META_ID_PATTERN.test(instagram_id)) return null;
  if (typeof page_id !== "string" || !META_ID_PATTERN.test(page_id)) return null;
  if (typeof access_token !== "string" || access_token.length < 1 || access_token.length > 4096) return null;
  return { instagram_id, page_id, access_token };
}

function buildOAuthSelectBody(body: unknown): Record<string, unknown> | null {
  if (!isRecord(body)) return null;
  const allowed = new Set(["token", "external_account_id"]);
  for (const key of Object.keys(body)) if (!allowed.has(key)) return null;

  const { token, external_account_id } = body;
  if (typeof token !== "string" || token.length < 10 || token.length > 128) return null;
  if (typeof external_account_id !== "string" || !EXTERNAL_ID_PATTERN.test(external_account_id)) return null;
  return { token, external_account_id };
}

export function buildChannelProxyTarget(
  method: string,
  segments: string[],
  params: URLSearchParams,
  body?: unknown,
): ChannelProxyTarget | null {
  const empty = new URLSearchParams();

  // Collection: list / create.
  if (segments.length === 0) {
    if (method === "GET") {
      const query = copyListFilters(params, new Set(["page", "page_size", "search", "channel_type", "status"]));
      if (!query) return null;
      const channelType = params.get("channel_type");
      if (channelType !== null) {
        if (!(CHANNEL_TYPES as readonly string[]).includes(channelType)) return null;
        query.set("channel_type", channelType);
      }
      const statusValue = params.get("status");
      if (statusValue !== null) {
        if (!(CHANNEL_STATUSES as readonly string[]).includes(statusValue)) return null;
        query.set("status", statusValue);
      }
      return { backendPath: "/channels", method: "GET", query };
    }
    if (method === "POST") {
      const created = buildCreateBody(body);
      if (!created) return null;
      return { backendPath: "/channels", method: "POST", query: empty, body: created };
    }
    return null;
  }

  const id = segments[0];

  // OAuth self-service flow
  if (id === "oauth") {
    if (segments.length === 3 && segments[2] === "start" && method === "POST" && params.size === 0) {
      const provider = segments[1];
      if (provider !== "facebook" && provider !== "instagram") return null;
      return { backendPath: `/channels/oauth/${provider}/start`, method: "POST", query: empty };
    }
    if (segments.length === 2 && segments[1] === "assets" && method === "GET") {
      const query = new URLSearchParams();
      const token = params.get("token");
      if (!token || token.length < 10 || token.length > 128) return null;
      query.set("token", token);
      return { backendPath: `/channels/oauth/assets`, method: "GET", query };
    }
    if (segments.length === 2 && segments[1] === "select" && method === "POST" && params.size === 0) {
      const select = buildOAuthSelectBody(body);
      if (!select) return null;
      return { backendPath: `/channels/oauth/select`, method: "POST", query: empty, body: select };
    }
    return null;
  }

  if (
    id === "whatsapp" &&
    segments.length === 3 &&
    segments[1] === "embedded-signup" &&
    segments[2] === "config" &&
    method === "GET" &&
    params.size === 0
  ) {
    return {
      backendPath: "/channels/whatsapp/embedded-signup/config",
      method: "GET",
      query: empty,
    };
  }

  if (!UUID_PATTERN.test(id)) return null;

  // Single channel: get / update / delete.
  if (segments.length === 1) {
    if (method === "GET" && params.size === 0) {
      return { backendPath: `/channels/${id}`, method: "GET", query: empty };
    }
    if (method === "PATCH") {
      const updated = buildUpdateBody(body);
      if (!updated) return null;
      return { backendPath: `/channels/${id}`, method: "PATCH", query: empty, body: updated };
    }
    if (method === "DELETE" && params.size === 0) {
      return { backendPath: `/channels/${id}`, method: "DELETE", query: empty, expectsNoContent: true };
    }
    return null;
  }

  if (segments.length === 2) {
    if (segments[1] === "disconnect" && method === "POST" && params.size === 0) {
      return { backendPath: `/channels/${id}/disconnect`, method: "POST", query: empty };
    }
    if (segments[1] === "templates" && method === "GET") {
      const allowed = new Set(["page", "page_size", "search", "status", "include_inactive"]);
      const query = copyListFilters(params, allowed);
      if (!query) return null;
      const statusValue = params.get("status");
      if (statusValue !== null) {
        if (!/^[A-Za-z_]{1,30}$/.test(statusValue)) return null;
        query.set("status", statusValue);
      }
      const includeInactive = params.get("include_inactive");
      if (includeInactive !== null) {
        if (includeInactive !== "true" && includeInactive !== "false") return null;
        query.set("include_inactive", includeInactive);
      }
      return { backendPath: `/channels/${id}/templates`, method: "GET", query };
    }
    return null;
  }

  if (segments.length === 3 && segments[1] === "whatsapp") {
    if (segments[2] === "connect" && method === "POST" && params.size === 0) {
      const connect = buildConnectBody(body);
      if (!connect) return null;
      return { backendPath: `/channels/${id}/whatsapp/connect`, method: "POST", query: empty, body: connect };
    }
    if (segments[2] === "test" && method === "POST" && params.size === 0) {
      return { backendPath: `/channels/${id}/whatsapp/test`, method: "POST", query: empty };
    }
    return null;
  }

  if (segments.length === 3 && segments[1] === "facebook") {
    if (segments[2] === "connect" && method === "POST" && params.size === 0) {
      const connect = buildFacebookConnectBody(body);
      if (!connect) return null;
      return { backendPath: `/channels/${id}/facebook/connect`, method: "POST", query: empty, body: connect };
    }
    if (segments[2] === "test" && method === "POST" && params.size === 0) {
      return { backendPath: `/channels/${id}/facebook/test`, method: "POST", query: empty };
    }
    return null;
  }

  if (segments.length === 3 && segments[1] === "instagram") {
    if (segments[2] === "connect" && method === "POST" && params.size === 0) {
      const connect = buildInstagramConnectBody(body);
      if (!connect) return null;
      return { backendPath: `/channels/${id}/instagram/connect`, method: "POST", query: empty, body: connect };
    }
    if (segments[2] === "test" && method === "POST" && params.size === 0) {
      return { backendPath: `/channels/${id}/instagram/test`, method: "POST", query: empty };
    }
    return null;
  }

  if (segments.length === 3 && segments[1] === "templates" && segments[2] === "sync" && method === "POST" && params.size === 0) {
    return { backendPath: `/channels/${id}/templates/sync`, method: "POST", query: empty };
  }

  // Web Chat activation: no body, no provider credentials.
  if (segments.length === 3 && segments[1] === "web-chat" && segments[2] === "connect" && method === "POST" && params.size === 0) {
    return { backendPath: `/channels/${id}/web-chat/connect`, method: "POST", query: empty };
  }

  return null;
}
