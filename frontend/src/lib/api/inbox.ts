import type { Conversation, ConversationListParams } from "@/lib/api/conversations";
import type { Message } from "@/lib/api/messages";
import type { PaginatedResponse } from "@/lib/api/client";

export class InboxApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly outcome: "rejected" | null = null,
  ) {
    super(message);
    this.name = "InboxApiError";
  }
}

export interface InboxChannelOption {
  id: string;
  name: string;
  channel_type: string;
}

export interface InboxUserOption {
  id: string;
  first_name: string;
  last_name: string | null;
  role: string;
}

export interface InboxTemplateOption {
  id: string;
  name: string;
  language: string;
  components: Record<string, unknown>[];
}

export interface InboxContactDetails {
  id: string | null;
  name: string | null;
  phone_number: string | null;
  email: string | null;
  is_blocked: boolean;
}

function handleExpiredSession() {
  if (typeof window === "undefined") return;
  const destination = `${window.location.pathname}${window.location.search}`;
  window.location.replace(`/login?reason=session-expired&next=${encodeURIComponent(destination)}`);
}

async function inboxRequest<T>(path: string, options: { method?: "GET" | "POST"; body?: unknown; idempotencyKey?: string } = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: options.method ?? "GET",
      headers: {
        Accept: "application/json",
        ...(options.body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...(options.idempotencyKey ? { "Idempotency-Key": options.idempotencyKey } : {}),
      },
      ...(options.body !== undefined ? { body: JSON.stringify(options.body) } : {}),
      cache: "no-store",
    });
  } catch {
    throw new InboxApiError(0, "Could not reach the inbox service. Try again.");
  }

  const payload: unknown = await response.json().catch(() => null);
  if (response.status === 401) handleExpiredSession();
  if (!response.ok) {
    const message = payload && typeof payload === "object" && "error" in payload && typeof payload.error === "string"
      ? payload.error
      : "The inbox request could not be completed.";
    const outcome = payload && typeof payload === "object" && "outcome" in payload && payload.outcome === "rejected"
      ? "rejected"
      : null;
    throw new InboxApiError(response.status, message, outcome);
  }
  return payload as T;
}

export function listInboxConversations(params: ConversationListParams) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
  }
  const suffix = query.size ? `?${query.toString()}` : "";
  return inboxRequest<PaginatedResponse<Conversation>>(`/api/inbox/conversations${suffix}`);
}

export function getInboxConversation(conversationId: string) {
  return inboxRequest<Conversation>(`/api/inbox/conversations/${encodeURIComponent(conversationId)}`);
}

export function listInboxMessages(conversationId: string, page = 1, pageSize = 100) {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  return inboxRequest<PaginatedResponse<Message>>(
    `/api/inbox/conversations/${encodeURIComponent(conversationId)}/messages?${query}`,
  );
}

export function markInboxConversationRead(conversationId: string) {
  return inboxRequest<Conversation>(`/api/inbox/conversations/${encodeURIComponent(conversationId)}/read`, { method: "POST" });
}

export function sendInboxTextMessage(conversationId: string, text: string, idempotencyKey = crypto.randomUUID()) {
  return inboxRequest<Message>(`/api/inbox/conversations/${encodeURIComponent(conversationId)}/messages`, {
    method: "POST",
    idempotencyKey,
    body: { type: "text", text },
  });
}

export function sendInboxTemplateMessage(conversationId: string, input: { type: "template"; template_name: string; language: string; components: Record<string, unknown>[] }, idempotencyKey = crypto.randomUUID()) {
  return inboxRequest<Message>(`/api/inbox/conversations/${encodeURIComponent(conversationId)}/messages`, {
    method: "POST", idempotencyKey, body: input,
  });
}

export function getInboxTemplates(channelId: string) {
  return inboxRequest<{ items: InboxTemplateOption[] }>(`/api/inbox/channels/${encodeURIComponent(channelId)}/templates?page=1&page_size=100`);
}

export function assignInboxConversation(conversationId: string, assigned_user_id: string | null) {
  return inboxRequest<Conversation>(`/api/inbox/conversations/${encodeURIComponent(conversationId)}/assign`, { method: "POST", body: { assigned_user_id } });
}

export function changeInboxConversationStatus(conversationId: string, status: Conversation["status"]) {
  return inboxRequest<Conversation>(`/api/inbox/conversations/${encodeURIComponent(conversationId)}/status`, { method: "POST", body: { status } });
}

export function getInboxChannelAvailability(channelId: string) {
  return inboxRequest<{ can_send: boolean }>(`/api/inbox/channels/${encodeURIComponent(channelId)}`);
}

export function getInboxContactAvailability(contactId: string) {
  return inboxRequest<{ is_blocked: boolean }>(`/api/inbox/contacts/${encodeURIComponent(contactId)}`);
}

export function getInboxContactDetails(contactId: string) {
  return inboxRequest<InboxContactDetails>(`/api/inbox/contacts/${encodeURIComponent(contactId)}`);
}

export async function getInboxFilterOptions() {
  const [channels, users] = await Promise.allSettled([
    inboxRequest<{ items: InboxChannelOption[] }>("/api/inbox/channels?page=1&page_size=100"),
    inboxRequest<{ items: InboxUserOption[] }>("/api/inbox/users?page=1&page_size=100"),
  ]);
  return {
    channels: channels.status === "fulfilled" ? channels.value.items : [],
    users: users.status === "fulfilled" ? users.value.items : [],
  };
}

export function inboxMediaUrl(messageId: string) {
  return `/api/inbox/messages/${encodeURIComponent(messageId)}/media`;
}
