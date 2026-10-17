import type { PaginatedResponse } from "@/lib/api/client";

export type MatchType = "exact" | "contains" | "starts_with" | "ends_with";

export interface Keyword {
  id: string;
  keyword_text: string;
  match_type: MatchType;
  is_active: boolean;
  flow_id: string | null;
  flow_name: string | null;
  reply_text: string | null;
  created_at: string;
}

export interface KeywordCreateInput {
  keyword_text: string;
  match_type: MatchType;
  is_active?: boolean;
  flow_id?: string | null;
  reply_text?: string | null;
}

export interface KeywordUpdateInput {
  keyword_text?: string;
  match_type?: MatchType;
  is_active?: boolean;
  flow_id?: string | null;
  reply_text?: string | null;
}

export class KeywordApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "KeywordApiError";
  }
}

function redirectToLogin() {
  if (typeof window === "undefined") return;
  const destination = `${window.location.pathname}${window.location.search}`;
  window.location.replace(`/login?reason=session-expired&next=${encodeURIComponent(destination)}`);
}

async function request<T>(
  path: string,
  options: { method?: "GET" | "POST" | "PATCH" | "DELETE"; body?: unknown } = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/keywords${path}`, {
      method: options.method ?? "GET",
      headers: {
        Accept: "application/json",
        ...(options.body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      ...(options.body !== undefined ? { body: JSON.stringify(options.body) } : {}),
      cache: "no-store",
    });
  } catch {
    throw new KeywordApiError(0, "Could not reach the keywords service. Try again.");
  }

  if (response.status === 401) {
    redirectToLogin();
    throw new KeywordApiError(401, "Your session has expired. Sign in again.");
  }
  if (response.status === 204) return undefined as T;

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const message =
      payload && typeof payload === "object" && "error" in payload && typeof payload.error === "string"
        ? payload.error
        : "The keywords request could not be completed.";
    throw new KeywordApiError(response.status, message);
  }
  return payload as T;
}

export function listKeywords() {
  return request<Keyword[]>("");
}

export function getKeyword(id: string) {
  return request<Keyword>(`/${encodeURIComponent(id)}`);
}

export function createKeyword(input: KeywordCreateInput) {
  return request<Keyword>("", { method: "POST", body: input });
}

export function updateKeyword(id: string, input: KeywordUpdateInput) {
  return request<Keyword>(`/${encodeURIComponent(id)}`, { method: "PATCH", body: input });
}

export function deleteKeyword(id: string) {
  return request<void>(`/${encodeURIComponent(id)}`, { method: "DELETE" });
}
