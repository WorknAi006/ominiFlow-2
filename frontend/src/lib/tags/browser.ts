// Browser-side client for Tags. Calls the same-origin Next proxy
// (/api/tags/...), which attaches the HttpOnly session token and forwards
// to the backend. The access token is never held in client state.

export interface Tag {
  id: string;
  name: string;
  color: string;
  contact_count: number;
  created_at: string;
  updated_at: string;
}

export interface TagListResponse {
  items: Tag[];
  total: number;
}

export class TagApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "TagApiError";
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
    response = await fetch(`/api/tags${path}`, {
      method: options.method ?? "GET",
      headers: {
        Accept: "application/json",
        ...(options.body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      ...(options.body !== undefined ? { body: JSON.stringify(options.body) } : {}),
      cache: "no-store",
    });
  } catch {
    throw new TagApiError(0, "Could not reach the tags service. Try again.");
  }

  if (response.status === 401) {
    redirectToLogin();
    throw new TagApiError(401, "Your session has expired. Sign in again.");
  }
  if (response.status === 204) return undefined as T;

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const message =
      payload && typeof payload === "object" && "error" in payload && typeof payload.error === "string"
        ? payload.error
        : "The tags request could not be completed.";
    throw new TagApiError(response.status, message);
  }
  return payload as T;
}

export function listTags() {
  return request<TagListResponse>("");
}

export function createTag(input: { name: string; color?: string }) {
  return request<Tag>("", { method: "POST", body: input });
}

export function updateTag(tagId: string, input: { name?: string; color?: string }) {
  return request<Tag>(`/${encodeURIComponent(tagId)}`, { method: "PATCH", body: input });
}

export function deleteTag(tagId: string) {
  return request<void>(`/${encodeURIComponent(tagId)}`, { method: "DELETE" });
}
