// Browser-side client for Custom Fields.
import type { PaginatedResponse } from "@/lib/api/client";

export interface CustomFieldDefinition {
  id: string;
  label: string;
  field_type: "text" | "number" | "date" | "select" | "multiselect" | "boolean";
  options: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface CustomFieldCreateInput {
  label: string;
  field_type: "text" | "number" | "date" | "select" | "multiselect" | "boolean";
  options?: string[] | null;
}

export interface CustomFieldUpdateInput {
  label?: string;
  options?: string[] | null;
}

export class CustomFieldApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "CustomFieldApiError";
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
    response = await fetch(`/api/custom-fields${path}`, {
      method: options.method ?? "GET",
      headers: {
        Accept: "application/json",
        ...(options.body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      ...(options.body !== undefined ? { body: JSON.stringify(options.body) } : {}),
      cache: "no-store",
    });
  } catch {
    throw new CustomFieldApiError(0, "Could not reach the custom fields service. Try again.");
  }

  if (response.status === 401) {
    redirectToLogin();
    throw new CustomFieldApiError(401, "Your session has expired. Sign in again.");
  }
  if (response.status === 204) return undefined as T;

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const message =
      payload && typeof payload === "object" && "error" in payload && typeof payload.error === "string"
        ? payload.error
        : "The custom fields request could not be completed.";
    throw new CustomFieldApiError(response.status, message);
  }
  return payload as T;
}

export function listCustomFields() {
  return request<PaginatedResponse<CustomFieldDefinition>>("");
}

export function createCustomField(input: CustomFieldCreateInput) {
  return request<CustomFieldDefinition>("", { method: "POST", body: input });
}

export function updateCustomField(id: string, input: CustomFieldUpdateInput) {
  return request<CustomFieldDefinition>(`/${encodeURIComponent(id)}`, { method: "PATCH", body: input });
}

export function deleteCustomField(id: string) {
  return request<void>(`/${encodeURIComponent(id)}`, { method: "DELETE" });
}
