"use client";

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import {
  ChannelApiError,
  connectWebChat,
  connectWhatsApp,
  createChannel,
  disconnectChannel,
  listChannels,
  syncChannelTemplates,
  testWhatsAppConnection,
  type ChannelConnection,
  type ChannelStatus,
  type ConnectionCheck,
  type TemplateSyncResult,
} from "@/lib/channels/browser";

const STATUS_META: Record<ChannelStatus, { label: string; tone: string }> = {
  connected: { label: "Connected", tone: "channel-pill-ok" },
  pending: { label: "Pending", tone: "channel-pill-warn" },
  disconnected: { label: "Disconnected", tone: "channel-pill-muted" },
  error: { label: "Error", tone: "channel-pill-bad" },
  revoked: { label: "Revoked", tone: "channel-pill-bad" },
};

const PROVIDER_LABEL: Record<string, string> = {
  whatsapp: "WhatsApp",
  instagram: "Instagram",
  facebook: "Facebook",
  web_chat: "Web Chat",
};

function widgetSnippet(publicKey: string) {
  const origin = typeof window !== "undefined" ? window.location.origin : "https://your-app";
  return `<script src="${origin}/omniflow-webchat.js"\n        data-omniflow-key="${publicKey}"\n        data-omniflow-api="YOUR_OMNIFLOW_API_URL"></script>`;
}

const META_ID = /^[0-9]{1,32}$/;

function formatTime(value: string | null | undefined) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString([], { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" });
}

type Notice = { kind: "success" | "error"; text: string } | null;

interface ConnectForm {
  mode: "new" | "reconnect";
  channel: ChannelConnection | null;
  name: string;
  phone_number_id: string;
  waba_id: string;
  access_token: string;
}

const EMPTY_FORM: ConnectForm = {
  mode: "new",
  channel: null,
  name: "",
  phone_number_id: "",
  waba_id: "",
  access_token: "",
};

export function ChannelsClient() {
  const [channels, setChannels] = useState<ChannelConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);

  const [busy, setBusy] = useState<Record<string, boolean>>({});
  const [checks, setChecks] = useState<Record<string, ConnectionCheck>>({});
  const [syncResults, setSyncResults] = useState<Record<string, TemplateSyncResult>>({});

  const [connectForm, setConnectForm] = useState<ConnectForm | null>(null);
  const [connectError, setConnectError] = useState("");
  const [connecting, setConnecting] = useState(false);

  const [confirmTarget, setConfirmTarget] = useState<ChannelConnection | null>(null);
  const [confirming, setConfirming] = useState(false);

  const [creatingWebChat, setCreatingWebChat] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setLoadError(false);
    try {
      const result = await listChannels({ page: 1, page_size: 100 });
      setChannels(result.items);
    } catch (error) {
      if (!(error instanceof ChannelApiError && error.status === 401)) setLoadError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void Promise.resolve().then(() => refresh());
  }, [refresh]);

  const setChannelBusy = (id: string, value: boolean) =>
    setBusy((prev) => ({ ...prev, [id]: value }));

  const handleError = (error: unknown, fallback: string) => {
    const text = error instanceof ChannelApiError ? error.message : fallback;
    setNotice({ kind: "error", text });
  };

  async function runTest(channel: ChannelConnection) {
    setChannelBusy(channel.id, true);
    setNotice(null);
    try {
      const result = await testWhatsAppConnection(channel.id);
      setChecks((prev) => ({ ...prev, [channel.id]: result }));
      setNotice({
        kind: result.healthy ? "success" : "error",
        text: result.healthy ? "WhatsApp connection is healthy." : result.detail,
      });
    } catch (error) {
      handleError(error, "Could not test this connection.");
    } finally {
      setChannelBusy(channel.id, false);
    }
  }

  async function runSync(channel: ChannelConnection) {
    setChannelBusy(channel.id, true);
    setNotice(null);
    try {
      const result = await syncChannelTemplates(channel.id);
      setSyncResults((prev) => ({ ...prev, [channel.id]: result }));
      const total = result.created + result.updated;
      setNotice({
        kind: "success",
        text: `Templates synchronized — ${result.received} received, ${total} added or updated, ${result.deactivated} deactivated.`,
      });
    } catch (error) {
      handleError(error, "Could not synchronize templates.");
    } finally {
      setChannelBusy(channel.id, false);
    }
  }

  function openConnect(channel: ChannelConnection | null) {
    setConnectError("");
    if (channel) {
      setConnectForm({
        mode: "reconnect",
        channel,
        name: channel.name,
        phone_number_id: channel.external_account_id ?? "",
        waba_id: channel.external_business_id ?? "",
        access_token: "",
      });
    } else {
      setConnectForm({ ...EMPTY_FORM });
    }
  }

  async function submitConnect(event: FormEvent) {
    event.preventDefault();
    if (!connectForm) return;
    const name = connectForm.name.trim();
    const phone = connectForm.phone_number_id.trim();
    const waba = connectForm.waba_id.trim();
    const token = connectForm.access_token.trim();

    if (connectForm.mode === "new" && (name.length < 2 || name.length > 150)) {
      setConnectError("Enter a channel name between 2 and 150 characters.");
      return;
    }
    if (!META_ID.test(phone)) {
      setConnectError("Phone Number ID must be numeric (up to 32 digits).");
      return;
    }
    if (!META_ID.test(waba)) {
      setConnectError("WhatsApp Business Account ID must be numeric (up to 32 digits).");
      return;
    }
    if (!token) {
      setConnectError("Paste the access token issued for your Meta app.");
      return;
    }

    setConnecting(true);
    setConnectError("");
    try {
      let channelId = connectForm.channel?.id;
      if (connectForm.mode === "new") {
        const created = await createChannel({ channel_type: "whatsapp", name });
        channelId = created.id;
      }
      await connectWhatsApp(channelId as string, {
        phone_number_id: phone,
        waba_id: waba,
        access_token: token,
      });
      setConnectForm(null);
      setNotice({ kind: "success", text: "WhatsApp channel connected." });
      await refresh();
    } catch (error) {
      setConnectError(error instanceof ChannelApiError ? error.message : "Could not connect this channel.");
      // A new channel may have been created in a pending/error state; reflect it.
      if (connectForm.mode === "new") void refresh();
    } finally {
      setConnecting(false);
    }
  }

  async function createWebChat() {
    setCreatingWebChat(true);
    setNotice(null);
    try {
      const created = await createChannel({ channel_type: "web_chat", name: "Web Chat" });
      await connectWebChat(created.id);
      setNotice({ kind: "success", text: "Web Chat channel created. Copy the widget snippet below to embed it." });
      await refresh();
    } catch (error) {
      handleError(error, "Could not create the Web Chat channel.");
      void refresh();
    } finally {
      setCreatingWebChat(false);
    }
  }

  async function activateWebChat(channel: ChannelConnection) {
    setChannelBusy(channel.id, true);
    setNotice(null);
    try {
      await connectWebChat(channel.id);
      setNotice({ kind: "success", text: "Web Chat channel activated." });
      await refresh();
    } catch (error) {
      handleError(error, "Could not activate this Web Chat channel.");
    } finally {
      setChannelBusy(channel.id, false);
    }
  }

  async function confirmDisconnect() {
    if (!confirmTarget) return;
    setConfirming(true);
    setNotice(null);
    try {
      await disconnectChannel(confirmTarget.id);
      setChecks((prev) => {
        const next = { ...prev };
        delete next[confirmTarget.id];
        return next;
      });
      setConfirmTarget(null);
      setNotice({ kind: "success", text: "Channel disconnected. Its history is kept." });
      await refresh();
    } catch (error) {
      handleError(error, "Could not disconnect this channel.");
    } finally {
      setConfirming(false);
    }
  }

  const connectedCount = useMemo(
    () => channels.filter((c) => c.status === "connected").length,
    [channels],
  );

  return (
    <section className="page-enter max-w-5xl">
      <header className="channel-header">
        <div>
          <p className="eyebrow">OMNIFLOW WORKSPACE</p>
          <h1 className="page-title mt-2">Channels</h1>
          <p className="page-subtitle mt-2">
            Connect and monitor the messaging channels for your workspace.
            {channels.length > 0 && ` ${connectedCount} of ${channels.length} connected.`}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="channel-primary-btn" onClick={() => openConnect(null)}>
            <span aria-hidden="true">+</span> Connect WhatsApp
          </button>
          <button type="button" className="channel-secondary-btn" disabled={creatingWebChat} onClick={() => void createWebChat()}>
            <span aria-hidden="true">+</span> {creatingWebChat ? "Creating…" : "Create Web Chat"}
          </button>
        </div>
      </header>

      {notice && (
        <div className={`channel-notice channel-notice-${notice.kind}`} role="status">
          <span>{notice.text}</span>
          <button type="button" onClick={() => setNotice(null)} aria-label="Dismiss">×</button>
        </div>
      )}

      {loading ? (
        <div className="channel-state" role="status">Loading your channels…</div>
      ) : loadError ? (
        <div className="channel-state channel-state-error" role="alert">
          <strong>Channels could not be loaded.</strong>
          <p>The channel service did not respond. Please try again.</p>
          <button type="button" className="channel-secondary-btn" onClick={() => void refresh()}>Try again</button>
        </div>
      ) : channels.length === 0 ? (
        <div className="channel-state channel-empty">
          <span className="channel-empty-mark" aria-hidden="true">↗</span>
          <strong>No channels yet</strong>
          <p>Connect your WhatsApp Business number, or add a Web Chat widget to your website, to start messaging.</p>
          <div className="flex flex-wrap justify-center gap-2">
            <button type="button" className="channel-primary-btn" onClick={() => openConnect(null)}>Connect WhatsApp</button>
            <button type="button" className="channel-secondary-btn" disabled={creatingWebChat} onClick={() => void createWebChat()}>
              {creatingWebChat ? "Creating…" : "Create Web Chat"}
            </button>
          </div>
        </div>
      ) : (
        <ul className="channel-grid">
          {channels.map((channel) => {
            const meta = STATUS_META[channel.status];
            const isWhatsApp = channel.channel_type === "whatsapp";
            const isWebChat = channel.channel_type === "web_chat";
            const isConnected = channel.status === "connected";
            const isBusy = busy[channel.id] ?? false;
            const check = checks[channel.id];
            const sync = syncResults[channel.id];
            return (
              <li key={channel.id} className="channel-card">
                <div className="channel-card-top">
                  <span className="channel-logo" aria-hidden="true">{PROVIDER_LABEL[channel.channel_type]?.[0] ?? "?"}</span>
                  <div className="channel-card-title">
                    <strong>{channel.name}</strong>
                    <span>{PROVIDER_LABEL[channel.channel_type] ?? channel.channel_type}</span>
                  </div>
                  <span className={`channel-pill ${meta.tone}`}>{meta.label}</span>
                </div>

                <dl className="channel-facts">
                  <div><dt>Phone / account</dt><dd>{channel.external_account_id ?? "—"}</dd></div>
                  <div><dt>Business ID</dt><dd>{channel.external_business_id ?? "—"}</dd></div>
                  <div><dt>Credentials</dt><dd>{channel.has_credentials ? "Stored (encrypted)" : "None"}</dd></div>
                  <div><dt>Last connected</dt><dd>{formatTime(channel.last_connected_at)}</dd></div>
                  <div>
                    <dt>Webhook</dt>
                    <dd>
                      {check
                        ? check.webhook_subscribed === null
                          ? "Unknown"
                          : check.webhook_subscribed
                            ? "Active"
                            : "Not subscribed"
                        : isConnected
                          ? "Subscribed at connect — run a test"
                          : "—"}
                    </dd>
                  </div>
                </dl>

                {channel.status === "error" && channel.last_error && (
                  <p className="channel-error-line">{channel.last_error}</p>
                )}

                {check && (
                  <div className={`channel-check ${check.healthy ? "channel-check-ok" : "channel-check-bad"}`} role="status">
                    <strong>{check.healthy ? "Connection healthy" : "Connection problem"}</strong>
                    <span>{check.detail}</span>
                    {check.display_phone_number && <span>Number: {check.display_phone_number}</span>}
                    {check.quality_rating && <span>Quality: {check.quality_rating}</span>}
                    {check.last_event_at && <span>Last webhook event: {formatTime(check.last_event_at)}</span>}
                  </div>
                )}

                {sync && (
                  <p className="channel-sync-line">
                    {sync.received} received · {sync.created} new · {sync.updated} updated · {sync.deactivated} deactivated
                  </p>
                )}

                {isWebChat && isConnected && channel.external_account_id && (
                  <div className="channel-check channel-check-ok" role="group" aria-label="Web Chat installation">
                    <strong>Widget install</strong>
                    <span>Public key: <code>{channel.external_account_id}</code></span>
                    <span>Paste this snippet before <code>&lt;/body&gt;</code> on your website:</span>
                    <pre style={{ whiteSpace: "pre-wrap", fontSize: "11px", margin: "4px 0 0", userSelect: "all" }}>{widgetSnippet(channel.external_account_id)}</pre>
                  </div>
                )}

                <div className="channel-actions">
                  {isConnected ? (
                    isWebChat ? (
                      <button type="button" className="channel-action channel-action-danger" disabled={isBusy} onClick={() => setConfirmTarget(channel)}>
                        Disconnect
                      </button>
                    ) : (
                      <>
                        <button type="button" className="channel-action" disabled={isBusy || !isWhatsApp} onClick={() => void runTest(channel)}>
                          {isBusy ? "Working…" : "Test connection"}
                        </button>
                        <button type="button" className="channel-action" disabled={isBusy || !isWhatsApp} onClick={() => void runSync(channel)}>
                          Sync templates
                        </button>
                        <button type="button" className="channel-action" disabled={isBusy || !isWhatsApp} onClick={() => openConnect(channel)}>
                          Reconnect
                        </button>
                        <button type="button" className="channel-action channel-action-danger" disabled={isBusy} onClick={() => setConfirmTarget(channel)}>
                          Disconnect
                        </button>
                      </>
                    )
                  ) : isWhatsApp ? (
                    <button type="button" className="channel-action channel-action-primary" disabled={isBusy} onClick={() => openConnect(channel)}>
                      {channel.status === "disconnected" || channel.status === "error" ? "Reconnect" : "Connect"}
                    </button>
                  ) : isWebChat ? (
                    <button type="button" className="channel-action channel-action-primary" disabled={isBusy} onClick={() => void activateWebChat(channel)}>
                      {isBusy ? "Working…" : "Activate"}
                    </button>
                  ) : (
                    <span className="channel-soon">Setup for {PROVIDER_LABEL[channel.channel_type]} is coming soon.</span>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {connectForm && (
        <div className="channel-modal-scrim" role="dialog" aria-modal="true" aria-labelledby="connect-title">
          <div className="channel-modal">
            <h2 id="connect-title">{connectForm.mode === "new" ? "Connect a WhatsApp channel" : `Reconnect ${connectForm.channel?.name ?? "channel"}`}</h2>
            <p className="channel-modal-sub">
              Enter your WhatsApp Cloud API details. The access token is sent securely to your workspace, encrypted at rest, and never displayed again.
            </p>
            <form onSubmit={submitConnect} className="channel-form">
              {connectForm.mode === "new" && (
                <label className="channel-field">
                  <span>Channel name</span>
                  <input
                    value={connectForm.name}
                    onChange={(e) => setConnectForm({ ...connectForm, name: e.target.value })}
                    maxLength={150}
                    placeholder="Support WhatsApp"
                    autoFocus
                    required
                  />
                </label>
              )}
              <label className="channel-field">
                <span>Phone Number ID</span>
                <input
                  value={connectForm.phone_number_id}
                  onChange={(e) => setConnectForm({ ...connectForm, phone_number_id: e.target.value })}
                  inputMode="numeric"
                  placeholder="1000000000000001"
                  required
                />
              </label>
              <label className="channel-field">
                <span>WhatsApp Business Account ID</span>
                <input
                  value={connectForm.waba_id}
                  onChange={(e) => setConnectForm({ ...connectForm, waba_id: e.target.value })}
                  inputMode="numeric"
                  placeholder="2000000000000001"
                  required
                />
              </label>
              <label className="channel-field">
                <span>Access token</span>
                <input
                  type="password"
                  value={connectForm.access_token}
                  onChange={(e) => setConnectForm({ ...connectForm, access_token: e.target.value })}
                  placeholder="System user / business integration token"
                  autoComplete="off"
                  required
                />
              </label>

              {connectError && <p className="channel-form-error" role="alert">{connectError}</p>}

              <div className="channel-modal-actions">
                <button type="button" className="channel-secondary-btn" onClick={() => setConnectForm(null)} disabled={connecting}>
                  Cancel
                </button>
                <button type="submit" className="channel-primary-btn" disabled={connecting}>
                  {connecting ? "Connecting…" : connectForm.mode === "new" ? "Connect" : "Reconnect"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {confirmTarget && (
        <div className="channel-modal-scrim" role="dialog" aria-modal="true" aria-labelledby="disconnect-title">
          <div className="channel-modal channel-modal-sm">
            <h2 id="disconnect-title">Disconnect {confirmTarget.name}?</h2>
            <p className="channel-modal-sub">
              Stored credentials will be removed and this channel will stop sending and receiving messages.
              Conversations, contacts and message history are kept. You can reconnect later.
            </p>
            <div className="channel-modal-actions">
              <button type="button" className="channel-secondary-btn" onClick={() => setConfirmTarget(null)} disabled={confirming}>
                Cancel
              </button>
              <button type="button" className="channel-primary-btn channel-btn-danger" onClick={() => void confirmDisconnect()} disabled={confirming}>
                {confirming ? "Disconnecting…" : "Disconnect"}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
