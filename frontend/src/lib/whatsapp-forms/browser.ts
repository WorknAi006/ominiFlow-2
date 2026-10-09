import type { PaginatedResponse } from "@/lib/api/client";

export interface WhatsAppForm {
  id: string;
  name: string;
  status: string;
  category: string | null;
  config: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export class FormsApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "FormsApiError";
  }
}

async function request<T>(path: string, options: { method?: string; body?: unknown } = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/whatsapp-forms${path}`, {
      method: options.method ?? "GET",
      headers: {
        Accept: "application/json",
        ...(options.body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      ...(options.body !== undefined ? { body: JSON.stringify(options.body) } : {}),
      cache: "no-store",
    });
  } catch {
    throw new FormsApiError(0, "Could not reach the forms service.");
  }
  
  if (response.status === 401 && typeof window !== "undefined") {
    window.location.replace(`/login?reason=session-expired&next=${encodeURIComponent(location.pathname + location.search)}`);
  }
  
  if (response.status === 204) return {} as T;

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new FormsApiError(
      response.status,
      payload && typeof payload === "object" && "error" in payload && typeof payload.error === "string"
        ? payload.error
        : "The request failed."
    );
  }
  return payload as T;
}

export const listForms = (page = 1, size = 100) => request<{ items: WhatsAppForm[], total: number }>(`?page=${page}&size=${size}`);
export const getForm = (id: string) => request<WhatsAppForm>(`/${id}`);
export const createForm = (input: { name: string; category?: string; config?: any }) => request<WhatsAppForm>("", { method: "POST", body: input });
export const updateForm = (id: string, body: { name?: string; category?: string; status?: string; config?: any }) => request<WhatsAppForm>(`/${id}`, { method: "PATCH", body });
export const deleteForm = (id: string) => request<void>(`/${id}`, { method: "DELETE" });
