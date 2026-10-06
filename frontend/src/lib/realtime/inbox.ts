/**
 * Minimal realtime inbox client (message.created, message.status_changed,
 * conversation.updated).
 *
 * Protocol with /api/v1/ws/inbox:
 *  1. open the socket
 *  2. send {"type": "auth", "token": <access token>} (never in the URL)
 *  3. server replies {"event": "ready"}, then streams message.created
 *
 * The tenant is decided by the server from the token; nothing tenant- or
 * role-related is sent by the client. Reconnects use exponential backoff
 * with jitter and fetch a fresh token each time (tokens are short-lived
 * and the server closes the socket when they expire).
 */
import { API_BASE_URL } from "@/lib/api/client";

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

export interface InboxRealtimeOptions {
  /** Returns the current access token (called on every (re)connect). */
  getToken: () => string | Promise<string>;
  /** Defaults to API_BASE_URL with ws(s):// and /api/v1/ws/inbox. */
  url?: string;
  onStateChange?: (state: InboxConnectionState) => void;
  initialBackoffMs?: number;
  maxBackoffMs?: number;
  /** For tests: create the socket (defaults to the global WebSocket). */
  webSocketFactory?: (url: string) => WebSocket;
}

type MessageCreatedHandler = (event: MessageCreatedEvent) => void;
type MessageStatusChangedHandler = (event: MessageStatusChangedEvent) => void;
type ConversationUpdatedHandler = (event: ConversationUpdatedEvent) => void;

/** Server close code: authenticated but not allowed. Retrying won't help. */
const CLOSE_FORBIDDEN = 4403;

function defaultUrl(): string {
  const url = new URL("/api/v1/ws/inbox", API_BASE_URL);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

export class InboxRealtimeClient {
  private socket: WebSocket | null = null;
  private handlers = new Set<MessageCreatedHandler>();
  private statusHandlers = new Set<MessageStatusChangedHandler>();
  private conversationHandlers = new Set<ConversationUpdatedHandler>();
  private attempts = 0;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private stopped = true;
  private currentState: InboxConnectionState = "disconnected";

  constructor(private readonly options: InboxRealtimeOptions) {}

  get state(): InboxConnectionState {
    return this.currentState;
  }

  connect(): void {
    if (!this.stopped) return;
    this.stopped = false;
    this.attempts = 0;
    this.open();
  }

  disconnect(): void {
    this.stopped = true;
    this.clearRetry();
    this.socket?.close(1000);
    this.socket = null;
    this.setState("disconnected");
  }

  /** Reconnect now (e.g. after login or a token refresh), resetting backoff. */
  reconnect(): void {
    this.stopped = false;
    this.attempts = 0;
    this.clearRetry();
    const previous = this.socket;
    this.socket = null;
    previous?.close(1000);
    this.open();
  }

  /** Subscribe to message.created. Returns an unsubscribe function. */
  onMessageCreated(handler: MessageCreatedHandler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  /** Subscribe to message.status_changed. Returns an unsubscribe function. */
  onMessageStatusChanged(handler: MessageStatusChangedHandler): () => void {
    this.statusHandlers.add(handler);
    return () => this.statusHandlers.delete(handler);
  }

  /** Subscribe to conversation.updated. Returns an unsubscribe function. */
  onConversationUpdated(handler: ConversationUpdatedHandler): () => void {
    this.conversationHandlers.add(handler);
    return () => this.conversationHandlers.delete(handler);
  }

  private open(): void {
    this.setState(this.attempts === 0 ? "connecting" : "reconnecting");

    const url = this.options.url ?? defaultUrl();
    const socket = this.options.webSocketFactory
      ? this.options.webSocketFactory(url)
      : new WebSocket(url);
    this.socket = socket;

    socket.onopen = async () => {
      try {
        const token = await this.options.getToken();
        if (this.socket === socket) {
          socket.send(JSON.stringify({ type: "auth", token }));
        }
      } catch {
        socket.close(4000);
      }
    };

    socket.onmessage = (message: MessageEvent) => {
      const event = parseRealtimeEvent(String(message.data));
      if (event === null) return;

      if (event.event === "ready") {
        this.attempts = 0;
        this.setState("connected");
      } else if (event.event === "message.created") {
        console.log("Realtime message received", event);
        this.handlers.forEach((handler) => handler(event));
      } else if (event.event === "message.status_changed") {
        console.log("Realtime message status changed", event);
        this.statusHandlers.forEach((handler) => handler(event));
      } else if (event.event === "conversation.updated") {
        console.log("Realtime conversation updated", event);
        this.conversationHandlers.forEach((handler) => handler(event));
      }
    };

    socket.onclose = (closeEvent: CloseEvent) => {
      if (this.socket !== socket) return; // superseded by reconnect()
      this.socket = null;

      if (this.stopped || closeEvent.code === CLOSE_FORBIDDEN) {
        this.stopped = true;
        this.setState("disconnected");
        return;
      }
      this.scheduleReconnect();
    };
  }

  private scheduleReconnect(): void {
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

export function createInboxRealtime(options: InboxRealtimeOptions): InboxRealtimeClient {
  return new InboxRealtimeClient(options);
}
