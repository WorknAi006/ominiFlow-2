"use client";

import Image from "next/image";
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type FormEvent } from "react";

import { InboxApiError, assignInboxConversation, changeInboxConversationStatus, getInboxChannelAvailability, getInboxContactDetails, getInboxConversation, getInboxFilterOptions, getInboxTemplates, inboxMediaUrl, listInboxConversations, listInboxMessages, markInboxConversationRead, sendInboxTextMessage, sendInboxTemplateMessage, type InboxChannelOption, type InboxContactDetails, type InboxTemplateOption, type InboxUserOption } from "@/lib/api/inbox";
import type { Conversation, ConversationListParams, ConversationStatus } from "@/lib/api/conversations";
import { MAX_TEXT_LENGTH, type Message } from "@/lib/api/messages";
import { canSendWhatsAppReply, INBOX_STATUSES } from "@/lib/inbox/proxy-utils";
import { createInboxEventStream, type InboxConnectionState } from "@/lib/realtime/inbox";

const PAGE_SIZE = 25;
const MESSAGE_PAGE_SIZE = 100;

interface InboxClientProps {
  initialConversationId: string | null;
}

type Readiness = { can_send: boolean } | null;
type ContactAvailability = { is_blocked: boolean } | null;

function shortTime(value: string | null | undefined) {
  if (!value) return "No activity yet";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const now = new Date();
  return date.toDateString() === now.toDateString()
    ? date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })
    : date.toLocaleDateString([], { month: "short", day: "numeric" });
}

function fullTime(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleString([], {
    month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit",
  });
}

function conversationPreview(conversation: Conversation) {
  const latest = conversation.last_message;
  if (!latest) return "No messages yet";
  if (latest.text) return latest.text;
  const type = latest.message_type;
  if (type === "image") return "Image attachment";
  if (type === "video") return "Video attachment";
  if (type === "audio") return "Audio message";
  if (type === "document") return "Document attachment";
  if (type === "location") return "Shared a location";
  if (type === "template") return "Template message";
  return "Message";
}

function mergeMessages(current: Message[], incoming: Message[]) {
  const byId = new Map(current.map((message) => [message.id, message]));
  incoming.forEach((message) => byId.set(message.id, message));
  return [...byId.values()].sort((a, b) => {
    const aTime = new Date(a.sent_at ?? a.created_at).getTime();
    const bTime = new Date(b.sent_at ?? b.created_at).getTime();
    return aTime - bTime || a.id.localeCompare(b.id);
  });
}

function contactLine(conversation: Conversation) {
  return conversation.contact.phone_number ?? conversation.channel.name;
}

function supportsInboxTemplate(template: InboxTemplateOption) {
  const header = template.components.find((component) => String(component.type).toUpperCase() === "HEADER");
  if (header && (String(header.format).toUpperCase() !== "TEXT" || typeof header.text === "string" && /{{/.test(header.text))) return false;
  const buttons = template.components.find((component) => String(component.type).toUpperCase() === "BUTTONS");
  return !Array.isArray(buttons?.buttons) || buttons.buttons.every((button) =>
    !button || typeof button !== "object" || String((button as Record<string, unknown>).type).toUpperCase() !== "URL" ||
    typeof (button as Record<string, unknown>).url !== "string" || !String((button as Record<string, unknown>).url).includes("{{"));
}

export function InboxClient({ initialConversationId }: InboxClientProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<ConversationStatus | "all">("all");
  const [unreadFilter, setUnreadFilter] = useState<"all" | "unread" | "read">("all");
  const [channelFilter, setChannelFilter] = useState("");
  const [assigneeFilter, setAssigneeFilter] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [channels, setChannels] = useState<InboxChannelOption[]>([]);
  const [users, setUsers] = useState<InboxUserOption[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState("");
  const [selectedId, setSelectedId] = useState(initialConversationId);
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [messageTotal, setMessageTotal] = useState(0);
  const [messagesLoading, setMessagesLoading] = useState(Boolean(initialConversationId));
  const [messagesError, setMessagesError] = useState("");
  const [readiness, setReadiness] = useState<Readiness>(null);
  const [contactAvailability, setContactAvailability] = useState<ContactAvailability>(null);
  const [contactDetails, setContactDetails] = useState<InboxContactDetails | null>(null);
  const [availabilityError, setAvailabilityError] = useState("");
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const sendingRef = useRef(false);
  const [loadingEarlier, setLoadingEarlier] = useState(false);
  const [sendError, setSendError] = useState("");
  const [uncertainSend, setUncertainSend] = useState(false);
  const [liveState, setLiveState] = useState<InboxConnectionState>("connecting");
  const [liveMessage, setLiveMessage] = useState("");
  const [mobileThread, setMobileThread] = useState(Boolean(initialConversationId));
  const [templates, setTemplates] = useState<InboxTemplateOption[]>([]);
  const [templateOpen, setTemplateOpen] = useState(false);
  const [templateId, setTemplateId] = useState("");
  const [templateValues, setTemplateValues] = useState<string[]>([]);
  const [templateBusy, setTemplateBusy] = useState(false);

  const selectedIdRef = useRef(selectedId);
  const selectedConversationRef = useRef(selectedConversation);
  const listRequestId = useRef(0);
  const messageRequestId = useRef(0);
  const messagePageRef = useRef(1);
  const loadConversationsRef = useRef<(showLoading?: boolean) => Promise<void>>(async () => {});
  const refreshThreadRef = useRef<(conversationId: string) => Promise<void>>(async () => {});
  const threadRef = useRef<HTMLDivElement>(null);
  const scrollMode = useRef<"bottom" | number | null>(null);

  useEffect(() => { selectedIdRef.current = selectedId; }, [selectedId]);
  useEffect(() => { selectedConversationRef.current = selectedConversation; }, [selectedConversation]);

  const updateUrl = useCallback((conversationId: string | null) => {
    const url = new URL(window.location.href);
    if (conversationId) url.searchParams.set("conversation", conversationId);
    else url.searchParams.delete("conversation");
    window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
  }, []);

  const loadConversations = useCallback(async (showLoading = false) => {
    const requestId = ++listRequestId.current;
    if (showLoading) setListLoading(true);
    setListError("");
    const params: ConversationListParams = {
      page,
      page_size: PAGE_SIZE,
      ...(statusFilter !== "all" ? { status: statusFilter } : {}),
      ...(unreadFilter !== "all" ? { unread: unreadFilter === "unread" } : {}),
      ...(channelFilter ? { channel_id: channelFilter } : {}),
      ...(assigneeFilter === "unassigned" ? { unassigned: true } : assigneeFilter ? { assigned_user_id: assigneeFilter } : {}),
      ...(appliedSearch ? { search: appliedSearch } : {}),
    };

    try {
      const result = await listInboxConversations(params);
      if (requestId !== listRequestId.current) return;
      setConversations(result.items);
      setTotal(result.total);
      const selected = selectedIdRef.current;
      const latestSelected = result.items.find((item) => item.id === selected);
      if (latestSelected) setSelectedConversation(latestSelected);
      if (!selected && result.items[0]) {
        setSelectedId(result.items[0].id);
        setSelectedConversation(result.items[0]);
        setMessages([]);
        setMessageTotal(0);
        setMessagesLoading(true);
        setLoadingEarlier(false);
        setReadiness(null);
        setContactAvailability(null);
        setAvailabilityError("");
        setMobileThread(true);
        updateUrl(result.items[0].id);
      }
    } catch (error) {
      if (requestId === listRequestId.current) {
        setListError(error instanceof Error ? error.message : "Could not load conversations.");
      }
    } finally {
      if (requestId === listRequestId.current) setListLoading(false);
    }
  }, [page, statusFilter, unreadFilter, channelFilter, assigneeFilter, appliedSearch, updateUrl]);

  useEffect(() => { loadConversationsRef.current = loadConversations; }, [loadConversations]);

  useEffect(() => { void Promise.resolve().then(() => loadConversations()); }, [loadConversations]);

  useEffect(() => {
    let active = true;
    void getInboxFilterOptions().then((options) => {
      if (!active) return;
      setChannels(options.channels);
      setUsers(options.users);
    }).catch(() => {
      // Conversation search/list remains available if optional filter data cannot load.
    });
    return () => { active = false; };
  }, []);

  const loadMessages = useCallback(async (conversationId: string, appendOlder = false) => {
    const requestId = ++messageRequestId.current;
    setMessagesError("");
    if (!appendOlder) setMessagesLoading(true);
    const nextPage = appendOlder ? messagePageRef.current + 1 : 1;
    if (appendOlder) setLoadingEarlier(true);

    try {
      const result = await listInboxMessages(conversationId, nextPage, MESSAGE_PAGE_SIZE);
      if (requestId !== messageRequestId.current) return;
      const chronological = [...result.items].reverse();
      if (appendOlder) {
        scrollMode.current = threadRef.current?.scrollHeight ?? 0;
        setMessages((current) => mergeMessages(chronological, current));
        messagePageRef.current = nextPage;
      } else {
        const nearBottom = !threadRef.current ||
          threadRef.current.scrollHeight - threadRef.current.scrollTop - threadRef.current.clientHeight < 100;
        if (nearBottom) scrollMode.current = "bottom";
        setMessages((current) => current.length ? mergeMessages(current, chronological) : chronological);
      }
      setMessageTotal(result.total);
    } catch (error) {
      if (requestId === messageRequestId.current) {
        setMessagesError(error instanceof Error ? error.message : "Could not load message history.");
      }
    } finally {
      if (requestId === messageRequestId.current) {
        if (!appendOlder) setMessagesLoading(false);
        else setLoadingEarlier(false);
      }
    }
  }, []);

  useLayoutEffect(() => {
    const element = threadRef.current;
    const mode = scrollMode.current;
    if (!element || mode === null) return;
    if (mode === "bottom") element.scrollTop = element.scrollHeight;
    else element.scrollTop += element.scrollHeight - mode;
    scrollMode.current = null;
  }, [messages]);

  useEffect(() => {
    if (!selectedId) {
      messageRequestId.current += 1;
      return;
    }

    let active = true;
    const selectionRequestId = ++messageRequestId.current;
    const selectedBefore = selectedConversationRef.current;
    const conversationPromise = selectedBefore?.id === selectedId
      ? Promise.resolve(selectedBefore)
      : getInboxConversation(selectedId);

    messagePageRef.current = 1;
    void conversationPromise.then(async (conversation) => {
      if (!active) return;
      setSelectedConversation(conversation);
      setMessagesLoading(true);
      setMessagesError("");
      setReadiness(null);
      setContactAvailability(null);
      setContactDetails(null);
      setAvailabilityError("");
      setSendError("");
      setUncertainSend(false);
      const [history, channel, contact] = await Promise.allSettled([
        listInboxMessages(selectedId, 1, MESSAGE_PAGE_SIZE),
        getInboxChannelAvailability(conversation.channel.id),
        getInboxContactDetails(conversation.contact.id),
      ]);
      if (!active || selectionRequestId !== messageRequestId.current) return;

      const historyResult = history as PromiseSettledResult<Awaited<ReturnType<typeof listInboxMessages>>>;
      if (historyResult.status === "fulfilled") {
        const chronological = [...historyResult.value.items].reverse();
        scrollMode.current = "bottom";
        setMessages(chronological);
        setMessageTotal(historyResult.value.total);
      } else {
        setMessagesError(historyResult.reason instanceof Error ? historyResult.reason.message : "Could not load message history.");
      }

      const channelResult = channel as PromiseSettledResult<{ can_send: boolean }>;
      const contactResult = contact as PromiseSettledResult<InboxContactDetails>;
      if (channelResult.status === "fulfilled") setReadiness(channelResult.value);
      else setAvailabilityError("Could not confirm the WhatsApp channel state. Refresh to try again.");
      if (contactResult.status === "fulfilled") {
        setContactDetails(contactResult.value);
        setContactAvailability({ is_blocked: contactResult.value.is_blocked });
      }
      else setAvailabilityError("Could not confirm whether this contact can receive messages. Refresh to try again.");

      if (conversation.unread_count > 0) {
        void markInboxConversationRead(selectedId).then((updated) => {
          if (!active) return;
          setSelectedConversation(updated);
          setConversations((current) => current.map((item) => item.id === updated.id ? updated : item));
        }).catch((error: unknown) => {
          if (active) setMessagesError(error instanceof Error ? "Messages loaded, but read status could not be updated." : "Read status could not be updated.");
        });
      }
      setMessagesLoading(false);
    }).catch((error: unknown) => {
      if (!active) return;
      const message = error instanceof Error ? error.message : "Conversation could not be opened.";
      setMessagesError(message);
      setSelectedConversation(null);
      if (error instanceof InboxApiError && error.status === 404) {
        setSelectedId(null);
        selectedIdRef.current = null;
        setMessages([]);
        setMessageTotal(0);
        setReadiness(null);
        setContactAvailability(null);
        updateUrl(null);
      }
      setMessagesLoading(false);
    });

    return () => { active = false; };
  }, [selectedId, updateUrl]);

  const refreshThread = useCallback(async (conversationId: string) => {
    const [conversationResult] = await Promise.allSettled([
      getInboxConversation(conversationId),
      loadMessages(conversationId),
    ]);
    if (conversationResult.status === "fulfilled" && selectedIdRef.current === conversationId) {
      setSelectedConversation(conversationResult.value);
    }
  }, [loadMessages]);

  useEffect(() => { refreshThreadRef.current = refreshThread; }, [refreshThread]);

  useEffect(() => {
    let refreshTimer: ReturnType<typeof setTimeout> | undefined;
    const stream = createInboxEventStream({
      onStateChange: (state) => {
        setLiveState(state);
        if (state === "connected") {
          void loadConversationsRef.current(false);
          const currentId = selectedIdRef.current;
          if (currentId) void refreshThreadRef.current(currentId);
        }
      },
      onAuthError: (code) => {
        if (code === 4401) {
          const destination = `${window.location.pathname}${window.location.search}`;
          window.location.replace(`/login?reason=session-expired&next=${encodeURIComponent(destination)}`);
        } else {
          setLiveMessage("Your role does not allow live inbox updates. You can still refresh manually.");
        }
      },
    });
    const unsubscribe = stream.onEvent((event) => {
      setLiveMessage("");
      if (refreshTimer) clearTimeout(refreshTimer);
      refreshTimer = setTimeout(() => {
        void loadConversationsRef.current(false);
        const currentId = selectedIdRef.current;
        if (currentId && event.conversation_id === currentId) {
          void refreshThreadRef.current(currentId);
        }
      }, 100);
    });
    stream.connect();
    return () => {
      if (refreshTimer) clearTimeout(refreshTimer);
      unsubscribe();
      stream.disconnect();
    };
  }, []);

  const selectConversation = useCallback((conversation: Conversation) => {
    setSelectedId(conversation.id);
    selectedIdRef.current = conversation.id;
    setSelectedConversation(conversation);
    setMessages([]);
    setMessageTotal(0);
    setMessagesLoading(true);
    setLoadingEarlier(false);
    setReadiness(null);
    setContactAvailability(null);
    setAvailabilityError("");
    setMobileThread(true);
    setDraft("");
    setSendError("");
    setUncertainSend(false);
    updateUrl(conversation.id);
  }, [updateUrl]);

  async function sendReply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedId || !draft.trim() || sendingRef.current || uncertainSend || canReplyReason) return;
    const outgoingText = draft;
    sendingRef.current = true;
    setSending(true);
    setSendError("");
    try {
      const message = await sendInboxTextMessage(selectedId, outgoingText);
      scrollMode.current = "bottom";
      setMessages((current) => mergeMessages(current, [message]));
      setDraft("");
      void loadConversations(false);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Message could not be sent.";
      setSendError(message);
      if (!(error instanceof InboxApiError) || error.status === 0 || error.status >= 500) {
        setUncertainSend(true);
      }
    } finally {
      sendingRef.current = false;
      setSending(false);
    }
  }

  async function updateConversation(updated: Conversation) {
    setSelectedConversation(updated);
    setConversations((current) => current.map((item) => item.id === updated.id ? updated : item));
    await loadConversations(false);
  }

  async function openTemplatePicker() {
    if (!selectedConversation) return;
    setTemplateOpen((open) => !open);
    if (templates.length) return;
    try {
      const result = await getInboxTemplates(selectedConversation.channel.id);
      setTemplates(result.items);
    } catch (error) {
      setSendError(error instanceof Error ? error.message : "Could not load approved templates.");
    }
  }

  const selectedTemplate = templates.find((template) => template.id === templateId) ?? null;
  const templateBody = selectedTemplate?.components.find((component) => String(component.type).toUpperCase() === "BODY");
  const templateBodyText = typeof templateBody?.text === "string" ? templateBody.text : "";
  const templateVariables = [...new Set(templateBodyText.match(/{{\s*[a-z_][a-z0-9_]*\s*}}|{{\s*\d+\s*}}/gi) ?? [])];

  async function sendTemplate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedId || !selectedTemplate || templateBusy || canReplyReason) return;
    setTemplateBusy(true);
    setSendError("");
    try {
      const bodyComponents = templateVariables.length ? [{
        type: "body",
        parameters: templateVariables.map((variable, index) => ({
          type: "text", text: templateValues[index] ?? "",
          ...( /^[{\s]*[a-z_]/i.test(variable) ? { parameter_name: variable.replace(/[{}\s]/g, "") } : {}),
        })),
      }] : [];
      const result = await sendInboxTemplateMessage(selectedId, {
        type: "template", template_name: selectedTemplate.name,
        language: selectedTemplate.language, components: bodyComponents,
      });
      setMessages((current) => mergeMessages(current, [result]));
      setTemplateOpen(false); setTemplateId(""); setTemplateValues([]);
      void loadConversations(false);
    } catch (error) {
      setSendError(error instanceof Error ? error.message : "Template could not be sent.");
    } finally {
      setTemplateBusy(false);
    }
  }

  const canReplyReason = selectedConversation
    ? availabilityError || canSendWhatsAppReply(selectedConversation, readiness, contactAvailability)
    : "Select a conversation to reply.";
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const canLoadEarlier = messages.length < messageTotal;
  const liveLabel = liveState === "connected"
    ? "Live updates on"
    : liveState === "connecting" || liveState === "reconnecting"
      ? "Reconnecting to live updates"
      : "Live updates offline";

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAppliedSearch(searchInput.trim().slice(0, 100));
    setPage(1);
  }

  function updateFilter<T>(setter: (value: T) => void, value: T) {
    setter(value);
    setPage(1);
  }

  return (
    <section className="inbox-page page-enter" aria-label="WhatsApp inbox">
      <div className="inbox-heading">
        <div>
          <p className="eyebrow">CUSTOMER MESSAGING</p>
          <h1 className="page-title mt-2">Inbox</h1>
          <p className="page-subtitle mt-2">Customer conversations across your connected channels.</p>
        </div>
        <div className="inbox-heading-actions">
          <span className={`live-indicator ${liveState === "connected" ? "live-indicator-on" : ""}`}>
            <span />{liveLabel}
          </span>
          <button type="button" className="refresh-button" onClick={() => {
            void loadConversations(false);
            if (selectedIdRef.current) void refreshThread(selectedIdRef.current);
          }} aria-label="Refresh conversations and messages">
            <span aria-hidden="true">↻</span><span className="refresh-label">Refresh</span>
          </button>
        </div>
      </div>

      {liveMessage && <p role="status" className="inbox-live-warning">{liveMessage}</p>}

      <div className={`inbox-layout grid min-h-[70vh] grid-cols-1 overflow-hidden rounded-xl border border-slate-200 bg-white xl:grid-cols-[minmax(260px,0.82fr)_minmax(400px,1.6fr)_minmax(210px,0.65fr)] ${mobileThread ? "inbox-has-selection" : ""}`}>
        <aside className={`conversation-pane min-h-0 flex-col border-r border-slate-200 ${mobileThread ? "hidden md:flex" : "flex"}`} aria-label="Conversation list">
          <div className="conversation-pane-header">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold text-slate-900">Conversations</h2>
                <p className="mt-1 text-xs text-slate-500">{total.toLocaleString()} total</p>
              </div>
              <span className="channel-pill"><span /> Channels</span>
            </div>

            <form className="inbox-search" onSubmit={submitSearch} role="search">
              <label className="sr-only" htmlFor="inbox-search">Search conversations</label>
              <span aria-hidden="true">⌕</span>
              <input id="inbox-search" value={searchInput} maxLength={100} onChange={(event) => setSearchInput(event.target.value)} placeholder="Search contacts or subject" />
              {searchInput && <button type="button" onClick={() => { setSearchInput(""); setAppliedSearch(""); setPage(1); }} aria-label="Clear search">×</button>}
            </form>

            <div className="inbox-filter-grid">
              <label>
                <span>Status</span>
                <select value={statusFilter} onChange={(event) => updateFilter(setStatusFilter, event.target.value as ConversationStatus | "all")}>
                  <option value="all">All statuses</option>
                  {INBOX_STATUSES.map((status) => <option key={status} value={status}>{status[0].toUpperCase() + status.slice(1)}</option>)}
                </select>
              </label>
              <label>
                <span>Unread</span>
                <select value={unreadFilter} onChange={(event) => updateFilter(setUnreadFilter, event.target.value as typeof unreadFilter)}>
                  <option value="all">All</option><option value="unread">Unread</option><option value="read">Read</option>
                </select>
              </label>
              <label>
                <span>Channel</span>
                <select value={channelFilter} onChange={(event) => updateFilter(setChannelFilter, event.target.value)}>
                  <option value="">All channels</option>
                  {channels.map((channel) => <option key={channel.id} value={channel.id}>{channel.name}</option>)}
                </select>
              </label>
              <label>
                <span>Assigned</span>
                <select value={assigneeFilter} onChange={(event) => updateFilter(setAssigneeFilter, event.target.value)}>
                  <option value="">Everyone</option><option value="unassigned">Unassigned</option>
                  {users.map((user) => <option key={user.id} value={user.id}>{[user.first_name, user.last_name].filter(Boolean).join(" ") || user.role}</option>)}
                </select>
              </label>
            </div>
          </div>

          {listError ? (
            <div className="inbox-list-state" role="alert">
              <span className="empty-state-mark">!</span>
              <p className="mt-3 text-sm font-semibold text-slate-800">Conversations could not load</p>
              <p className="mt-1 text-xs leading-5 text-slate-500">{listError}</p>
              <button className="text-action mt-3" type="button" onClick={() => void loadConversations(true)}>Try again</button>
            </div>
          ) : listLoading && conversations.length === 0 ? (
            <div className="inbox-list-state" role="status"><span className="loading-spinner" /><p className="mt-3 text-sm text-slate-500">Loading conversations…</p></div>
          ) : conversations.length === 0 ? (
            <div className="inbox-list-state">
              <span className="empty-state-mark">◎</span>
              <p className="mt-3 text-sm font-semibold text-slate-800">No conversations here yet</p>
              <p className="mt-1 max-w-52 text-xs leading-5 text-slate-500">New customer conversations will appear here when they arrive.</p>
              {(appliedSearch || statusFilter !== "all" || unreadFilter !== "all" || channelFilter || assigneeFilter) && (
                <button className="text-action mt-3" type="button" onClick={() => {
                  setAppliedSearch(""); setSearchInput(""); setStatusFilter("all"); setUnreadFilter("all"); setChannelFilter(""); setAssigneeFilter(""); setPage(1);
                }}>Clear filters</button>
              )}
            </div>
          ) : (
            <div className="conversation-list" aria-label="Conversations">
              {conversations.map((conversation) => (
                <button
                  type="button"
                  key={conversation.id}
                  className={`conversation-row ${selectedId === conversation.id ? "conversation-row-selected" : ""} ${conversation.unread_count > 0 ? "conversation-row-unread" : ""}`}
                  onClick={() => selectConversation(conversation)}
                  aria-current={selectedId === conversation.id ? "true" : undefined}
                >
                  <span className="contact-avatar" aria-hidden="true">{(conversation.contact.name || "?").trim().slice(0, 1).toUpperCase()}</span>
                  <span className="conversation-row-content">
                    <span className="conversation-row-top">
                      <span className="conversation-contact">{conversation.contact.name || "Unknown contact"}</span>
                      <time className="conversation-time" dateTime={conversation.last_message_at ?? conversation.updated_at}>{shortTime(conversation.last_message_at ?? conversation.updated_at)}</time>
                    </span>
                    <span className="conversation-row-middle">
                      <span className="conversation-phone">{contactLine(conversation)}</span>
                      <span className={`status-tag status-${conversation.status}`}>{conversation.status}</span>
                    </span>
                    <span className="conversation-row-bottom">
                      <span className="conversation-preview">{conversationPreview(conversation)}</span>
                      {conversation.unread_count > 0 && <span className="unread-count" aria-label={`${conversation.unread_count} unread messages`}>{conversation.unread_count > 99 ? "99+" : conversation.unread_count}</span>}
                    </span>
                    <span className="conversation-channel">{conversation.channel.name}{conversation.assigned_user ? ` · ${conversation.assigned_user.first_name}` : " · Unassigned"}</span>
                  </span>
                </button>
              ))}
            </div>
          )}

          <div className="conversation-pagination">
            <span>Page {page} of {pageCount}</span>
            <div className="flex gap-2">
              <button type="button" disabled={page <= 1 || listLoading} onClick={() => setPage((current) => Math.max(1, current - 1))} aria-label="Previous page">←</button>
              <button type="button" disabled={page >= pageCount || listLoading} onClick={() => setPage((current) => Math.min(pageCount, current + 1))} aria-label="Next page">→</button>
            </div>
          </div>
        </aside>

        <section className={`thread-pane min-w-0 flex-col ${mobileThread ? "flex" : "hidden md:flex"}`} aria-label="Message thread">
          {selectedConversation ? (
            <>
              <header className="thread-header">
                <button type="button" className="thread-back" onClick={() => setMobileThread(false)} aria-label="Back to conversations">←</button>
                <span className="contact-avatar contact-avatar-thread" aria-hidden="true">{(selectedConversation.contact.name || "?").trim().slice(0, 1).toUpperCase()}</span>
                <div className="min-w-0 flex-1">
                  <h2 className="truncate text-sm font-semibold text-slate-900">{selectedConversation.contact.name || "Unknown contact"}</h2>
                  <p className="mt-0.5 truncate text-xs text-slate-500">{selectedConversation.contact.phone_number ?? "Phone unavailable"}</p>
                </div>
                <div className="thread-header-meta">
                  <span className="thread-channel">{selectedConversation.channel.name}</span>
                  <span className={`status-tag status-${selectedConversation.status}`}>{selectedConversation.status}</span>
                </div>
              </header>

              <div className="flex flex-wrap items-center gap-3 border-b border-slate-200 bg-white px-4 py-2 text-xs">
                <label className="flex items-center gap-2 text-slate-600">
                  <span>Assignee</span>
                  <select aria-label="Assign conversation" value={selectedConversation.assigned_user?.id ?? ""}
                    onChange={(event) => void assignInboxConversation(selectedConversation.id, event.target.value || null)
                      .then(updateConversation).catch((error) => setSendError(error instanceof Error ? error.message : "Assignment could not be changed."))}>
                    <option value="">Unassigned</option>
                    {users.map((user) => <option key={user.id} value={user.id}>{[user.first_name, user.last_name].filter(Boolean).join(" ") || user.role}</option>)}
                  </select>
                </label>
                <label className="flex items-center gap-2 text-slate-600">
                  <span>Status</span>
                  <select aria-label="Conversation status" value={selectedConversation.status}
                    onChange={(event) => void changeInboxConversationStatus(selectedConversation.id, event.target.value as ConversationStatus)
                      .then(updateConversation).catch((error) => setSendError(error instanceof Error ? error.message : "Status could not be changed."))}>
                    {INBOX_STATUSES.map((status) => <option key={status} value={status}>{status[0].toUpperCase() + status.slice(1)}</option>)}
                  </select>
                </label>
                <a className="ml-auto text-sky-700 hover:underline" href="/contacts">Open Contacts</a>
              </div>
              <aside className="border-b border-slate-200 bg-slate-50 px-4 py-2 text-xs text-slate-600 xl:hidden" aria-label="Contact details">
                <span className="font-semibold text-slate-800">Contact</span>
                <span className="ml-3">{contactDetails?.name || selectedConversation.contact.name || "Unknown contact"}</span>
                <span className="ml-3">{contactDetails?.phone_number || selectedConversation.contact.phone_number || "Phone unavailable"}</span>
                {contactDetails?.email && <span className="ml-3">{contactDetails.email}</span>}
              </aside>

              <div className="thread-date-divider"><span>Conversation history</span></div>

              <div className="message-history min-h-0 flex-1 overflow-y-auto" ref={threadRef} aria-live="polite" aria-label="Messages">
                {canLoadEarlier && !messagesLoading && (
                  <button type="button" className="load-earlier-button" disabled={loadingEarlier} onClick={() => void loadMessages(selectedConversation.id, true)}>{loadingEarlier ? "Loading…" : "Load earlier messages"}</button>
                )}
                {messagesLoading && messages.length === 0 && <div className="thread-state" role="status"><span className="loading-spinner" /><span>Loading messages…</span></div>}
                {messagesError && messages.length === 0 && (
                  <div className="thread-state" role="alert"><p>{messagesError}</p><button className="text-action" type="button" onClick={() => void refreshThread(selectedConversation.id)}>Try again</button></div>
                )}
                {!messagesLoading && !messagesError && messages.length === 0 && (
                  <div className="thread-state"><span className="empty-state-mark">✉</span><p className="mt-3 text-sm text-slate-500">No messages in this conversation yet.</p></div>
                )}
                {messages.map((message) => <MessageBubble key={message.id} message={message} />)}
                {messagesError && messages.length > 0 && <p role="status" className="thread-inline-error">{messagesError}</p>}
              </div>

              <div className="composer-wrap">
                {canReplyReason && <p className="composer-notice" role="status">{canReplyReason}</p>}
                {sendError && <div className={`send-error ${uncertainSend ? "send-error-uncertain" : ""}`} role="alert">
                  <p>{sendError}</p>
                  {uncertainSend && <>
                    <p className="mt-1 text-xs leading-5">The message may already have reached WhatsApp. Refresh and check the thread before deciding whether to retry.</p>
                    <button type="button" className="text-action mt-2" onClick={() => void refreshThread(selectedConversation.id)}>Refresh message status</button>
                    <button type="button" className="retry-confirm" onClick={() => {
                      if (window.confirm("Only continue if you checked WhatsApp and confirmed the previous reply was not sent. Retrying can create a duplicate.")) {
                        setUncertainSend(false);
                        setSendError("");
                      }
                    }}>I verified it was not sent — allow one retry</button>
                  </>}
                </div>}
                {templateOpen && <form className="mb-3 rounded-lg border border-slate-200 bg-white p-3" onSubmit={sendTemplate}>
                  <div className="flex items-center justify-between gap-2">
                    <strong className="text-sm">Template Message</strong>
                    <button type="button" className="text-action" onClick={() => setTemplateOpen(false)}>Close</button>
                  </div>
                  <label className="mt-3 block text-xs text-slate-600">Approved WhatsApp template
                    <select className="mt-1 block w-full" value={templateId} onChange={(event) => { setTemplateId(event.target.value); setTemplateValues([]); }}>
                      <option value="">Choose a template</option>
                      {templates.filter(supportsInboxTemplate).map((template) => <option key={template.id} value={template.id}>{template.name} · {template.language}</option>)}
                    </select>
                  </label>
                  {selectedTemplate && templateVariables.map((variable, index) => <label key={`${variable}-${index}`} className="mt-2 block text-xs text-slate-600">Value for {variable}
                    <input className="mt-1 block w-full" required maxLength={1024} value={templateValues[index] ?? ""}
                      onChange={(event) => setTemplateValues((current) => { const next = [...current]; next[index] = event.target.value; return next; })} />
                  </label>)}
                  {selectedTemplate && <div className="mt-3 rounded bg-slate-50 p-2 text-sm text-slate-700" aria-label="Template preview">
                    {templateVariables.reduce((preview, variable, index) => preview.replace(variable, templateValues[index] || `[${variable}]`), templateBodyText) || selectedTemplate.name}
                  </div>}
                  <button className="send-button mt-3" type="submit" disabled={!selectedTemplate || templateBusy || Boolean(canReplyReason)}>{templateBusy ? "Sending…" : "Confirm and send template"}</button>
                </form>}
                <form className="reply-composer" onSubmit={sendReply}>
                  <label htmlFor="reply-message" className="sr-only">Write a WhatsApp reply</label>
                  <textarea
                    id="reply-message"
                    value={draft}
                    onChange={(event) => setDraft(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
                        event.preventDefault();
                        event.currentTarget.form?.requestSubmit();
                      }
                    }}
                    maxLength={MAX_TEXT_LENGTH}
                    placeholder={canReplyReason ? "Replies are unavailable" : "Write a reply…"}
                    disabled={Boolean(canReplyReason) || sending || uncertainSend}
                    rows={2}
                    aria-describedby="reply-guidance"
                  />
                  <div className="composer-footer">
                    <span id="reply-guidance" className="composer-guidance">Enter to send · Shift + Enter for a new line</span>
                    <div className="flex items-center gap-3">
                      <button type="button" className="text-action" disabled={Boolean(canReplyReason)} onClick={() => void openTemplatePicker()}>Template Message</button>
                      <span className="character-count">{Array.from(draft).length}/{MAX_TEXT_LENGTH}</span>
                      <button type="submit" disabled={!draft.trim() || Boolean(canReplyReason) || sending || uncertainSend} className="send-button">
                        {sending ? "Sending…" : <><span>Send</span><span aria-hidden="true">↑</span></>}
                      </button>
                    </div>
                  </div>
                </form>
              </div>
            </>
          ) : (
            <div className="thread-empty">
              <span className="thread-empty-icon" aria-hidden="true">◎</span>
              <h2 className="mt-4 text-lg font-semibold text-slate-800">Your conversations, together</h2>
              <p className="mt-2 max-w-xs text-center text-sm leading-6 text-slate-500">Select a conversation to read its history and reply to your customer.</p>
            </div>
          )}
        </section>
        {selectedConversation && <aside className="hidden border-l border-slate-200 bg-slate-50 p-4 xl:flex xl:flex-col" aria-label="Contact and conversation information">
          <h2 className="text-sm font-semibold text-slate-900">Contact details</h2>
          <p className="mt-4 text-sm font-medium text-slate-800">{contactDetails?.name || selectedConversation.contact.name || "Unknown contact"}</p>
          <p className="mt-1 break-all text-xs text-slate-600">{contactDetails?.phone_number || selectedConversation.contact.phone_number || "Phone unavailable"}</p>
          {contactDetails?.email && <p className="mt-2 break-all text-xs text-slate-600">{contactDetails.email}</p>}
          <a className="mt-3 text-xs text-sky-700 hover:underline" href="/contacts">Open Contacts</a>
          <hr className="my-4 border-slate-200" />
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Conversation</h3>
          <p className="mt-3 text-xs text-slate-700">Status: <span className="capitalize">{selectedConversation.status}</span></p>
          <p className="mt-2 text-xs text-slate-700">Channel: {selectedConversation.channel.name}</p>
          <p className="mt-2 text-xs text-slate-700">Assigned to: {selectedConversation.assigned_user ? [selectedConversation.assigned_user.first_name, selectedConversation.assigned_user.last_name].filter(Boolean).join(" ") : "Unassigned"}</p>
        </aside>}
      </div>
    </section>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const [mediaError, setMediaError] = useState(false);
  const [downloadingMedia, setDownloadingMedia] = useState(false);
  const outbound = message.direction === "outbound";
  const time = message.sent_at ?? message.created_at;
  const mediaUrl = message.media_url ? inboxMediaUrl(message.id) : null;
  const mediaLabel = message.message_type === "image" ? "Image" : message.message_type === "video" ? "Video" : message.message_type === "audio" ? "Audio" : message.message_type === "document" ? "Document" : "Attachment";

  async function downloadDocument() {
    if (!mediaUrl || downloadingMedia) return;
    setDownloadingMedia(true);
    setMediaError(false);
    try {
      const response = await fetch(mediaUrl, { cache: "no-store" });
      if (!response.ok) throw new Error("Media download failed.");
      const objectUrl = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = objectUrl;
      const contentDisposition = response.headers.get("content-disposition");
      const filename = contentDisposition?.match(/filename="?([^";]+)"?/i)?.[1];
      link.download = filename?.replace(/[^a-zA-Z0-9._ -]/g, "_").slice(0, 120) || mediaLabel.toLowerCase();
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1_000);
    } catch {
      setMediaError(true);
    } finally {
      setDownloadingMedia(false);
    }
  }

  return (
    <article className={`message-row ${outbound ? "message-row-outbound" : "message-row-inbound"}`}>
      <div className={`message-bubble ${outbound ? "message-bubble-outbound" : "message-bubble-inbound"}`}>
        {message.text && <p className="message-text">{message.text}</p>}
        {mediaUrl && !mediaError && message.message_type === "image" && (
          <a href={mediaUrl} target="_blank" rel="noreferrer" className="message-media-image-link">
            <Image src={mediaUrl} alt="Image attachment" width={480} height={360} unoptimized onError={() => setMediaError(true)} className="message-media-image" />
          </a>
        )}
        {mediaUrl && !mediaError && message.message_type === "audio" && <audio className="message-audio" controls preload="none" src={mediaUrl} onError={() => setMediaError(true)}>Audio message</audio>}
        {mediaUrl && !mediaError && message.message_type === "video" && <video className="message-video" controls preload="none" src={mediaUrl} onError={() => setMediaError(true)}>Video message</video>}
        {mediaUrl && !mediaError && message.message_type === "document" && <button className="message-document" type="button" disabled={downloadingMedia} onClick={() => void downloadDocument()}>{downloadingMedia ? "Downloading…" : `${mediaLabel} · Download file`}</button>}
        {mediaUrl && mediaError && <p className="message-attachment-pending" role="status">{mediaLabel} attachment could not be loaded. Refresh and try again.</p>}
        {!mediaUrl && ["image", "audio", "video", "document"].includes(message.message_type) && (
          <p className="message-attachment-pending">{mediaLabel} attachment is not available yet.</p>
        )}
        {!message.text && !["image", "audio", "video", "document"].includes(message.message_type) && (
          <p className="message-attachment-pending">{message.message_type === "location" ? "Location message" : `${message.message_type} message`}</p>
        )}
        <footer className="message-meta">
          <time dateTime={time} title={fullTime(time)}>{shortTime(time)}</time>
          {outbound && <span className={`message-delivery message-delivery-${message.status}`} title={`Message ${message.status}`}>
            {message.status === "pending" ? "Sending" : message.status === "failed" ? "Failed" : message.status === "read" ? "Read" : message.status === "delivered" ? "Delivered" : "Sent"}
          </span>}
        </footer>
        {outbound && message.status === "failed" && message.error_message && <p className="message-failure">{message.error_message}</p>}
      </div>
    </article>
  );
}
