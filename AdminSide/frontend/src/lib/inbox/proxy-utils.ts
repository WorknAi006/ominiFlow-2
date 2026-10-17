export const INBOX_STATUSES = ["open", "pending", "resolved", "closed"] as const;

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const LIST_FILTERS = new Set([
  "page", "page_size", "status", "channel_id", "assigned_user_id",
  "unassigned", "unread", "search",
]);

export interface ProxyTarget {
  backendPath: string;
  query: URLSearchParams;
  kind: "json" | "channel" | "contact" | "media" | "channels" | "users" | "templates";
  body?: Record<string, unknown>;
}

function positiveInt(value: string | null, fallback: number, maximum: number) {
  if (value === null) return fallback;
  if (!/^\d+$/.test(value)) return null;
  const number = Number(value);
  return number >= 1 && number <= maximum ? number : null;
}

function addBoolean(query: URLSearchParams, params: URLSearchParams, key: string) {
  const value = params.get(key);
  if (value === null) return true;
  if (value !== "true" && value !== "false") return false;
  query.set(key, value);
  return true;
}

export function buildInboxProxyTarget(
  method: string,
  segments: string[],
  params: URLSearchParams,
  body?: unknown,
): ProxyTarget | null {
  const query = new URLSearchParams();

  if (method === "GET" && ["channels", "users"].includes(segments[0]) && segments.length === 1) {
    const allowed = segments[0] === "channels"
      ? new Set(["page", "page_size", "search", "channel_type", "status"])
      : new Set(["page", "page_size", "search"]);
    for (const key of params.keys()) if (!allowed.has(key)) return null;
    const page = positiveInt(params.get("page"), 1, 1_000_000);
    const pageSize = positiveInt(params.get("page_size"), 100, 100);
    if (page === null || pageSize === null) return null;
    query.set("page", String(page));
    query.set("page_size", String(pageSize));
    for (const key of ["search", "channel_type", "status"]) {
      const value = params.get(key);
      if (value !== null && value.length <= 100) query.set(key, value);
      else if (value !== null) return null;
    }
    if (segments[0] === "users" && (params.has("channel_type") || params.has("status"))) return null;
    return {
      backendPath: `/${segments[0]}`,
      query,
      kind: segments[0] === "channels" ? "channels" : "users",
    };
  }

  if (method === "GET" && segments.length === 1 && segments[0] === "conversations") {
    for (const key of params.keys()) if (!LIST_FILTERS.has(key)) return null;
    const page = positiveInt(params.get("page"), 1, 1_000_000);
    const pageSize = positiveInt(params.get("page_size"), 25, 100);
    if (page === null || pageSize === null) return null;
    query.set("page", String(page));
    query.set("page_size", String(pageSize));

    const status = params.get("status");
    if (status !== null) {
      if (!INBOX_STATUSES.includes(status as (typeof INBOX_STATUSES)[number])) return null;
      query.set("status", status);
    }
    for (const key of ["channel_id", "assigned_user_id"]) {
      const value = params.get(key);
      if (value !== null) {
        if (!UUID_PATTERN.test(value)) return null;
        query.set(key, value);
      }
    }
    if (!addBoolean(query, params, "unassigned") || !addBoolean(query, params, "unread")) return null;
    if (params.get("unassigned") === "true" && params.has("assigned_user_id")) return null;

    const search = params.get("search");
    if (search !== null) {
      if (search.length > 100) return null;
      if (search) query.set("search", search);
    }
    return { backendPath: "/conversations", query, kind: "json" };
  }

  if (segments.length === 2 && UUID_PATTERN.test(segments[1])) {
    const id = segments[1];
    if (method === "GET" && segments[0] === "conversations" && params.size === 0) {
      return { backendPath: `/conversations/${id}`, query, kind: "json" };
    }
    if (method === "GET" && segments[0] === "channels" && params.size === 0) {
      return { backendPath: `/channels/${id}`, query, kind: "channel" };
    }
    if (method === "GET" && segments[0] === "contacts" && params.size === 0) {
      return { backendPath: `/contacts/${id}`, query, kind: "contact" };
    }
    if (method === "GET" && segments[0] === "channels" && params.size === 2 && params.get("page") === "1" && params.get("page_size") === "100") {
      return { backendPath: `/channels/${id}/templates`, query: new URLSearchParams({ page: "1", page_size: "100" }), kind: "templates" };
    }
  }

  if (segments.length === 3 && UUID_PATTERN.test(segments[1])) {
    const id = segments[1];
    if (segments[0] === "conversations" && segments[2] === "messages" && method === "GET") {
      for (const key of params.keys()) if (key !== "page" && key !== "page_size") return null;
      const page = positiveInt(params.get("page"), 1, 1_000_000);
      const pageSize = positiveInt(params.get("page_size"), 100, 100);
      if (page === null || pageSize === null) return null;
      query.set("page", String(page));
      query.set("page_size", String(pageSize));
      return { backendPath: `/conversations/${id}/messages`, query, kind: "json" };
    }
    if (segments[0] === "conversations" && segments[2] === "read" && method === "POST" && params.size === 0) {
      return { backendPath: `/conversations/${id}/read`, query, kind: "json" };
    }
    if (segments[0] === "conversations" && segments[2] === "assign" && method === "POST" && params.size === 0 &&
      body && typeof body === "object" && !Array.isArray(body) && Object.keys(body).length === 1 &&
      "assigned_user_id" in body && (body.assigned_user_id === null || typeof body.assigned_user_id === "string" && UUID_PATTERN.test(body.assigned_user_id))) {
      return { backendPath: `/conversations/${id}/assign`, query, kind: "json", body: body as Record<string, unknown> };
    }
    if (segments[0] === "conversations" && segments[2] === "status" && method === "POST" && params.size === 0 &&
      body && typeof body === "object" && !Array.isArray(body) && Object.keys(body).length === 1 &&
      "status" in body && INBOX_STATUSES.includes(body.status as (typeof INBOX_STATUSES)[number])) {
      return { backendPath: `/conversations/${id}/status`, query, kind: "json", body: body as Record<string, unknown> };
    }
    if (segments[0] === "conversations" && segments[2] === "messages" && method === "POST" && params.size === 0) {
      if (!body || typeof body !== "object" || Array.isArray(body)) return null;
      const input = body as Record<string, unknown>;
      if (input.type === "text" && Object.keys(input).length === 2 && typeof input.text === "string" && input.text.trim() && Array.from(input.text).length <= 4096) {
        return { backendPath: `/conversations/${id}/messages`, query, kind: "json", body: input };
      }
      if (input.type === "template" && Object.keys(input).every((key) => ["type", "template_name", "language", "components"].includes(key)) &&
        typeof input.template_name === "string" && /^[a-z0-9_]{1,512}$/.test(input.template_name) &&
        typeof input.language === "string" && /^[A-Za-z]{2,3}(_[A-Za-z0-9]{2,8})?$/.test(input.language) &&
        (input.components === undefined || Array.isArray(input.components) && input.components.length <= 10)) {
        return { backendPath: `/conversations/${id}/messages`, query, kind: "json", body: input };
      }
      return null;
    }
  }

  if (segments.length === 3 && segments[0] === "messages" && UUID_PATTERN.test(segments[1]) && segments[2] === "media" && method === "GET" && params.size === 0) {
    return { backendPath: `/messages/${segments[1]}/media`, query, kind: "media" };
  }
  return null;
}

export function canSendWhatsAppReply(
  conversation: { channel: { channel_type: string } },
  channel: { can_send: boolean } | null,
  contact: { is_blocked: boolean } | null,
) {
  const type = conversation.channel.channel_type;
  if (type !== "whatsapp" && type !== "web_chat") {
    return "Replies are currently available for WhatsApp and Web Chat conversations only.";
  }
  if (!channel) return "Checking channel availability…";
  if (!channel.can_send) {
    return type === "web_chat"
      ? "This Web Chat channel is not connected."
      : "This WhatsApp channel is not connected and ready to send.";
  }
  if (!contact) return "Checking contact availability…";
  if (contact.is_blocked) return "This contact is blocked and cannot receive messages.";
  return null;
}
