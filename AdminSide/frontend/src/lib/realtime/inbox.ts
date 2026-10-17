/**
 * Inbox realtime event types and clients for message.created,
 * message.status_changed, and conversation.updated.
 *
 * The backend WebSocket expects a first-frame JWT. The Inbox uses a
 * same-origin server bridge to keep that token in the HttpOnly cookie and
 * relay the existing event payloads over an EventSource connection.
 */

export type InboxConnectionState =
  | "connecting"
  | "connected"
  | "disconnected"
  | "reconnecting";

export interface MessageCreatedEvent {
  event: "message.created";
  event_id: string;
  tenant_id: string;
  conversation_id: string;
  message_id: string;
  timestamp: string;
  data: {
    direction: "inbound" | "outbound";
    type: string;
    text: string | null;
    created_at: string | null;
    contact: { id: string; name: string | null; phone_number: string | null };
  };
}

export const DELIVERY_STATUSES = ["sent", "delivered", "read", "failed"] as const;
export type DeliveryStatus = (typeof DELIVERY_STATUSES)[number];

export interface MessageStatusChangedEvent {
  event: "message.status_changed";
  event_id: string;
  tenant_id: string;
  conversation_id: string;
  message_id: string;
  timestamp: string;
  data: {
    status: DeliveryStatus;
    sent_at: string | null;
    delivered_at: string | null;
    read_at: string | null;
    failed_at: string | null;
    error_code: string | null;
    error_message: string | null;
  };
}

export const CONVERSATION_STATUSES = ["open", "pending", "resolved", "closed"] as const;
export type ConversationStatus = (typeof CONVERSATION_STATUSES)[number];

/** Conversation-list state after a committed change (no contact PII). */
export interface ConversationUpdatedEvent {
  event: "conversation.updated";
  event_id: string;
  tenant_id: string;
  conversation_id: string;
  timestamp: string;
  data: {
    status: ConversationStatus;
    unread_count: number;
    last_message_at: string | null;
    last_message_id: string | null;
    last_message_direction: "inbound" | "outbound" | null;
    last_message_type: string | null;
    /** Single-line, at most 200 characters. */
    last_message_preview: string | null;
  };
}

export type InboxEvent =
  | { event: "ready" }
  | MessageCreatedEvent
  | MessageStatusChangedEvent
  | ConversationUpdatedEvent;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isConversationUpdatedData(data: Record<string, unknown>): boolean {
  return (
    CONVERSATION_STATUSES.includes(data.status as ConversationStatus) &&
    typeof data.unread_count === "number" &&
    Number.isInteger(data.unread_count) &&
    data.unread_count >= 0 &&
    isNullableString(data.last_message_at) &&
    isNullableString(data.last_message_id) &&
    (data.last_message_direction === null ||
      data.last_message_direction === "inbound" ||
      data.last_message_direction === "outbound") &&
    isNullableString(data.last_message_type) &&
    isNullableString(data.last_message_preview)
  );
}

/**
 * Parse one server frame. Returns null for malformed or unknown events, so
 * callers never act on unexpected data.
 */
export function parseRealtimeEvent(raw: unknown): InboxEvent | null {
  let payload: unknown;
  try {
    payload = typeof raw === "string" ? JSON.parse(raw) : raw;
  } catch {
    return null;
  }
  if (!isRecord(payload) || typeof payload.event !== "string") return null;

  if (payload.event === "ready") return { event: "ready" };

  if (typeof payload.conversation_id !== "string" || !isRecord(payload.data)) return null;
  const data = payload.data;

  if (payload.event === "conversation.updated") {
    return isConversationUpdatedData(data)
      ? (payload as unknown as ConversationUpdatedEvent)
      : null;
  }

  // Message events also require a message id.
  if (typeof payload.message_id !== "string") return null;

  if (payload.event === "message.created") {
    return payload as unknown as MessageCreatedEvent;
  }
  if (
    payload.event === "message.status_changed" &&
    DELIVERY_STATUSES.includes(data.status as DeliveryStatus)
  ) {
    return payload as unknown as MessageStatusChangedEvent;
  }
  return null;
}

export interface InboxEventStreamOptions {
  url?: string;
  onStateChange?: (state: InboxConnectionState) => void;
  onAuthError?: (code: number) => void;
  initialBackoffMs?: number;
  maxBackoffMs?: number;
  eventSourceFactory?: (url: string) => EventSource;
}

export class InboxEventStreamClient {
  private source: EventSource | null = null;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private attempts = 0;
  private stopped = true;
  private currentState: InboxConnectionState = "disconnected";
  private eventIds = new Set<string>();
  private eventHandlers = new Set<(event: Exclude<InboxEvent, { event: "ready" }>) => void>();

  constructor(private readonly options: InboxEventStreamOptions = {}) {}

  get state(): InboxConnectionState { return this.currentState; }

  connect(): void {
    if (!this.stopped) return;
    this.stopped = false;
    this.attempts = 0;
    this.open();
  }

  disconnect(): void {
    this.stopped = true;
    this.clearRetry();
    this.source?.close();
    this.source = null;
    this.setState("disconnected");
  }

  reconnect(): void {
    this.stopped = false;
    this.attempts = 0;
    this.clearRetry();
    this.source?.close();
    this.source = null;
    this.open();
  }

  onEvent(handler: (event: Exclude<InboxEvent, { event: "ready" }>) => void): () => void {
    this.eventHandlers.add(handler);
    return () => this.eventHandlers.delete(handler);
  }

  private open(): void {
    this.setState(this.attempts === 0 ? "connecting" : "reconnecting");
    let source: EventSource;
    try {
      source = this.options.eventSourceFactory
        ? this.options.eventSourceFactory(this.options.url ?? "/api/realtime/inbox")
        : new EventSource(this.options.url ?? "/api/realtime/inbox");
    } catch {
      this.scheduleReconnect();
      return;
    }
    this.source = source;

    source.onopen = () => {
      if (this.source !== source) return;
      this.attempts = 0;
      this.setState("connected");
    };
    source.onmessage = (message: MessageEvent<string>) => {
      if (this.source !== source) return;
      const event = parseRealtimeEvent(message.data);
      if (!event || event.event === "ready") return;
      if (event.event_id && this.eventIds.has(event.event_id)) return;
      if (event.event_id) {
        this.eventIds.add(event.event_id);
        if (this.eventIds.size > 500) this.eventIds.delete(this.eventIds.values().next().value!);
      }
      this.eventHandlers.forEach((handler) => handler(event));
    };
    source.addEventListener("auth_error", (rawEvent) => {
      if (this.source !== source) return;
      const message = rawEvent as MessageEvent<string>;
      let code = 4401;
      try {
        const payload: unknown = JSON.parse(message.data);
        if (isRecord(payload) && (payload.code === 4401 || payload.code === 4403)) code = payload.code;
      } catch { /* Keep the unauthenticated fallback. */ }
      this.stopped = true;
      source.close();
      this.source = null;
      this.clearRetry();
      this.setState("disconnected");
      this.options.onAuthError?.(code);
    });
    source.onerror = () => {
      if (this.source !== source || this.stopped) return;
      source.close();
      this.source = null;
      this.scheduleReconnect();
    };
  }

  private scheduleReconnect(): void {
    if (this.stopped) return;
    const initial = this.options.initialBackoffMs ?? 1_000;
    const max = this.options.maxBackoffMs ?? 30_000;
    const base = Math.min(max, initial * 2 ** this.attempts);
    const delay = base + Math.random() * base * 0.3;
    this.attempts += 1;
    this.setState("reconnecting");
    this.clearRetry();
    this.retryTimer = setTimeout(() => {
      this.retryTimer = null;
      if (!this.stopped) this.open();
    }, delay);
  }

  private clearRetry(): void {
    if (this.retryTimer !== null) {
      clearTimeout(this.retryTimer);
      this.retryTimer = null;
    }
  }

  private setState(state: InboxConnectionState): void {
    if (state === this.currentState) return;
    this.currentState = state;
    this.options.onStateChange?.(state);
  }
}

export function createInboxEventStream(options: InboxEventStreamOptions = {}): InboxEventStreamClient {
  return new InboxEventStreamClient(options);
}
