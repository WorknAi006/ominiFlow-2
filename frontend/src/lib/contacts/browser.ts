// Browser-side client for Contacts. Calls the same-origin Next proxy
// (/api/contacts/...), which attaches the HttpOnly session token and
// forwards to the backend. The access token is never held in client state.

import type {
  Contact,
  ContactCreateInput,
  ContactListParams,
  ContactTagSummary,
  ContactIdentitySummary,
  ContactUpdateInput,
} from "@/lib/api/contacts";
import type { Conversation } from "@/lib/api/conversations";
import type { PaginatedResponse } from "@/lib/api/client";

export type { Contact, ContactTagSummary, ContactIdentitySummary };

export class ContactApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "ContactApiError";
  }
}

export interface ImportResult {
  accepted: number;
  skipped: number;
  errors: string[];
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
    response = await fetch(`/api/contacts${path}`, {
      method: options.method ?? "GET",
      headers: {
        Accept: "application/json",
        ...(options.body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      ...(options.body !== undefined ? { body: JSON.stringify(options.body) } : {}),
      cache: "no-store",
    });
  } catch {
    throw new ContactApiError(0, "Could not reach the contacts service. Try again.");
  }

  if (response.status === 401) {
    redirectToLogin();
    throw new ContactApiError(401, "Your session has expired. Sign in again.");
  }
  if (response.status === 204) return undefined as T;

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const message =
      payload && typeof payload === "object" && "error" in payload && typeof payload.error === "string"
        ? payload.error
        : "The contacts request could not be completed.";
    throw new ContactApiError(response.status, message);
  }
  return payload as T;
}

function toQuery(params: Record<string, unknown>) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
  }
  return query.size ? `?${query.toString()}` : "";
}

export function listContacts(params: ContactListParams = {}) {
  return request<PaginatedResponse<Contact>>(toQuery({ ...params }));
}

export function getContact(contactId: string) {
  return request<Contact>(`/${encodeURIComponent(contactId)}`);
}

export function createContact(input: ContactCreateInput) {
  return request<Contact>("", { method: "POST", body: input });
}

export function createContactConversation(contactId: string, channelType?: string) {
  return request<Conversation>(`/${encodeURIComponent(contactId)}/conversations`, {
    method: "POST",
    body: channelType ? { channel_type: channelType } : {},
  });
}

export function updateContact(contactId: string, input: ContactUpdateInput) {
  return request<Contact>(`/${encodeURIComponent(contactId)}`, { method: "PATCH", body: input });
}

export function listContactConversations(contactId: string, page = 1, pageSize = 20) {
  return request<PaginatedResponse<Conversation>>(
    `/${encodeURIComponent(contactId)}/conversations${toQuery({ page, page_size: pageSize })}`,
  );
}

export function deleteContact(contactId: string) {
  return request<void>(`/${encodeURIComponent(contactId)}`, { method: "DELETE" });
}

export function bulkDeleteContacts(contactIds: string[]) {
  return request<{ deleted: number }>("/bulk-delete", { method: "POST", body: { contact_ids: contactIds } });
}

export function deleteAllContacts(confirm: string) {
  return request<{ deleted: number }>("/all/delete", { method: "POST", body: { confirm } });
}

export function setContactTags(contactId: string, tagIds: string[]) {
  return request<Contact>(`/${encodeURIComponent(contactId)}/tags`, { method: "POST", body: { tag_ids: tagIds } });
}

export function bulkApplyTags(contactIds: string[], addTagIds: string[], removeTagIds: string[] = []) {
  return request<{ affected: number }>("/tags", {
    method: "POST",
    body: { contact_ids: contactIds, add_tag_ids: addTagIds, remove_tag_ids: removeTagIds },
  });
}

export function updateContactFields(contactId: string, fieldValues: Record<string, string | number | boolean | string[] | null>) {
  return request<Contact>(`/${encodeURIComponent(contactId)}/fields`, { method: "PATCH", body: fieldValues });
}

export async function exportContactsCsv(params: ContactListParams = {}): Promise<Blob> {
  const query = toQuery({ search: params.search, tag_id: params.tag_id, channel_type: params.channel_type });
  let response: Response;
  try {
    response = await fetch(`/api/contacts/export${query}`, { headers: { Accept: "text/csv" }, cache: "no-store" });
  } catch {
    throw new ContactApiError(0, "Could not reach the contacts service. Try again.");
  }
  if (response.status === 401) {
    redirectToLogin();
    throw new ContactApiError(401, "Your session has expired. Sign in again.");
  }
  if (!response.ok) throw new ContactApiError(response.status, "The export could not be completed.");
  return response.blob();
}

export async function importContactsCsv(file: File): Promise<ImportResult> {
  const formData = new FormData();
  formData.append("file", file);
  
  let response: Response;
  try {
    response = await fetch("/api/contacts/import", {
      method: "POST",
      body: formData,
    });
  } catch {
    throw new ContactApiError(0, "Could not reach the contacts service. Try again.");
  }
  
  if (response.status === 401) {
    redirectToLogin();
    throw new ContactApiError(401, "Your session has expired. Sign in again.");
  }
  
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const message = payload && typeof payload === "object" && "error" in payload && typeof payload.error === "string"
        ? payload.error : "The import could not be completed.";
    throw new ContactApiError(response.status, message);
  }
  return payload as ImportResult;
}
