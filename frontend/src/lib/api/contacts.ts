import { apiRequest, type PaginatedResponse } from "./client";

export interface ContactIdentitySummary {
  channel_type: string;
  external_id: string;
  display_name: string | null;
}

export interface ContactTagSummary {
  id: string;
  name: string;
  color: string;
}

export interface Contact {
  id: string;
  name: string | null;
  phone_number: string | null;
  normalized_phone_number: string | null;
  email: string | null;
  first_name: string | null;
  last_name: string | null;
  display_name: string | null;
  profile_name: string | null;
  avatar_url: string | null;
  is_blocked: boolean;
  created_at: string;
  updated_at: string;
  identities: ContactIdentitySummary[];
  tags: ContactTagSummary[];
  field_values?: Record<string, string | number | boolean | string[] | null>;
}

export interface ContactListParams {
  page?: number;
  page_size?: number;
  search?: string;
  phone?: string;
  tag_id?: string;
  channel_type?: string;
}

/** At least one of phone_number or email is required. */
export interface ContactCreateInput {
  phone_number?: string;
  email?: string;
  first_name?: string;
  last_name?: string;
  display_name?: string;
}

export interface ContactUpdateInput {
  phone_number?: string;
  email?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  display_name?: string | null;
  is_blocked?: boolean;
}

export function listContacts(token: string, params: ContactListParams = {}) {
  return apiRequest<PaginatedResponse<Contact>>("/contacts", {
    token,
    query: { ...params },
  });
}

export function getContact(token: string, contactId: string) {
  return apiRequest<Contact>(`/contacts/${contactId}`, { token });
}

export function createContact(token: string, input: ContactCreateInput) {
  return apiRequest<Contact>("/contacts", { method: "POST", token, body: input });
}

export function updateContact(
  token: string,
  contactId: string,
  input: ContactUpdateInput,
) {
  return apiRequest<Contact>(`/contacts/${contactId}`, {
    method: "PATCH",
    token,
    body: input,
  });
}
