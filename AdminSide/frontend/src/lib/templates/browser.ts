// Browser-side client for Templates. Calls the same-origin Next proxy
// (/api/templates/...), which attaches the HttpOnly session token and
// forwards to the backend. Sync reuses the existing Channel Management
// endpoint; no sync logic is reimplemented here.

import type { PaginatedResponse } from "@/lib/api/client";
import type { MessageTemplate, TemplateSyncResult } from "@/lib/api/templates";

export type { MessageTemplate, TemplateSyncResult };

export interface TemplateFilters {
  page?: number;
  page_size?: number;
  channel_id?: string;
  status?: string;
  category?: string;
  language?: string;
  search?: string;
  include_inactive?: boolean;
}

export class TemplateApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "TemplateApiError";
  }
}

function redirectToLogin() {
  if (typeof window === "undefined") return;
  const destination = `${window.location.pathname}${window.location.search}`;
  window.location.replace(`/login?reason=session-expired&next=${encodeURIComponent(destination)}`);
}

async function request<T>(path: string, options: { method?: "GET" | "POST" } = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/templates${path}`, {
      method: options.method ?? "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
  } catch {
    throw new TemplateApiError(0, "Could not reach the templates service. Try again.");
  }

  if (response.status === 401) {
    redirectToLogin();
    throw new TemplateApiError(401, "Your session has expired. Sign in again.");
  }

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const message =
      payload && typeof payload === "object" && "error" in payload && typeof payload.error === "string"
        ? payload.error
        : "The templates request could not be completed.";
    throw new TemplateApiError(response.status, message);
  }
  return payload as T;
}

export function listTemplates(filters: TemplateFilters = {}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
  }
  const suffix = query.size ? `?${query.toString()}` : "";
  return request<PaginatedResponse<MessageTemplate>>(suffix);
}

export function getTemplate(templateId: string) {
  return request<MessageTemplate>(`/${encodeURIComponent(templateId)}`);
}

export function syncTemplates(channelId: string) {
  return request<TemplateSyncResult>(`/sync/${encodeURIComponent(channelId)}`, { method: "POST" });
}
