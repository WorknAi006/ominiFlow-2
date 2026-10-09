const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export type ProxyMethod = "GET" | "POST" | "PATCH" | "DELETE";

export interface KeywordProxyTarget {
  backendPath: string;
  method: ProxyMethod;
  query: URLSearchParams;
  body?: Record<string, unknown>;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function buildKeywordProxyTarget(
  method: string,
  segments: string[],
  body?: unknown,
): KeywordProxyTarget | null {
  const empty = new URLSearchParams();

  if (segments.length === 0) {
    if (method === "GET") return { backendPath: "/keywords", method: "GET", query: empty };
    if (method === "POST") {
      if (!isRecord(body)) return null;
      if (typeof body.keyword_text !== "string" || body.keyword_text.trim().length < 1 || body.keyword_text.length > 255) return null;
      if (typeof body.match_type !== "string" || !["exact", "contains", "starts_with"].includes(body.match_type)) return null;
      
      const out: Record<string, unknown> = { 
        keyword_text: body.keyword_text.trim(), 
        match_type: body.match_type 
      };
      
      if ("is_active" in body && typeof body.is_active === "boolean") {
        out.is_active = body.is_active;
      }
      if ("flow_id" in body) {
        if (body.flow_id === null || (typeof body.flow_id === "string" && UUID_PATTERN.test(body.flow_id))) {
          out.flow_id = body.flow_id;
        }
      }
      if ("reply_text" in body) {
        if (body.reply_text === null || typeof body.reply_text === "string") {
          out.reply_text = body.reply_text;
        }
      }
      
      return { backendPath: "/keywords", method: "POST", query: empty, body: out };
    }
    return null;
  }

  const id = segments[0];
  if (segments.length === 1 && UUID_PATTERN.test(id)) {
    if (method === "GET") return { backendPath: `/keywords/${id}`, method: "GET", query: empty };
    if (method === "PATCH") {
      if (!isRecord(body)) return null;
      const out: Record<string, unknown> = {};
      if ("keyword_text" in body && typeof body.keyword_text === "string") out.keyword_text = body.keyword_text.trim();
      if ("match_type" in body && typeof body.match_type === "string" && ["exact", "contains", "starts_with"].includes(body.match_type)) {
        out.match_type = body.match_type;
      }
      if ("is_active" in body && typeof body.is_active === "boolean") out.is_active = body.is_active;
      if ("flow_id" in body) {
        if (body.flow_id === null || (typeof body.flow_id === "string" && UUID_PATTERN.test(body.flow_id))) {
          out.flow_id = body.flow_id;
        }
      }
      if ("reply_text" in body) {
        if (body.reply_text === null || typeof body.reply_text === "string") {
          out.reply_text = body.reply_text;
        }
      }
      if (Object.keys(out).length === 0) return null;
      return { backendPath: `/keywords/${id}`, method: "PATCH", query: empty, body: out };
    }
    if (method === "DELETE") return { backendPath: `/keywords/${id}`, method: "DELETE", query: empty };
  }

  return null;
}
