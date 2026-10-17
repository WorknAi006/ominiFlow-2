"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import type { Conversation } from "@/lib/api/conversations";

interface PageResult<T> {
  items: T[];
  total: number;
}

interface ChannelOption {
  id: string;
  name: string;
  channel_type: string;
}

interface DashboardData {
  recent: Conversation[];
  conversations: number;
  open: number;
  unread: number;
}

async function readJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { headers: { Accept: "application/json" }, cache: "no-store" });
  if (response.status === 401) {
    window.location.replace("/login?reason=session-expired");
    throw new Error("session-expired");
  }
  if (!response.ok) throw new Error("dashboard-request-failed");
  return response.json() as Promise<T>;
}

function formatActivity(value: string | null) {
  if (!value) return "No activity yet";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

export function DashboardClient() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [channels, setChannels] = useState<ChannelOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const hasLoadedRef = useRef(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const [recent, open, unread] = await Promise.all([
        readJson<PageResult<Conversation>>("/api/inbox/conversations?page=1&page_size=6"),
        readJson<PageResult<Conversation>>("/api/inbox/conversations?page=1&page_size=1&status=open"),
        readJson<PageResult<Conversation>>("/api/inbox/conversations?page=1&page_size=1&unread=true"),
      ]);
      setData({ recent: recent.items, conversations: recent.total, open: open.total, unread: unread.total });
      const channelResult = await readJson<PageResult<ChannelOption>>("/api/inbox/channels?page=1&page_size=100").catch(() => null);
      if (channelResult) setChannels(channelResult.items);
    } catch (cause) {
      if (!(cause instanceof Error) || cause.message !== "session-expired") setError(true);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (hasLoadedRef.current) return;
    hasLoadedRef.current = true;
    void refresh();
  }, [refresh]);

  const metrics = [
    { label: "Conversations", value: data?.conversations, detail: "Across your workspace", mark: "C", tone: "mint" },
    { label: "Open", value: data?.open, detail: "Waiting for your team", mark: "O", tone: "blue" },
    { label: "Unread", value: data?.unread, detail: "Need a first look", mark: "U", tone: "amber" },
  ] as const;

  return (
    <div className="dashboard-page page-enter">
      <header className="dashboard-heading">
        <div>
          <p className="eyebrow">WORKSPACE OVERVIEW</p>
          <h1 className="page-title mt-2">Good to have you back.</h1>
          <p className="page-subtitle mt-2">A live view of the conversations your team is handling.</p>
        </div>
        <button type="button" className="dashboard-refresh" onClick={() => void refresh()} disabled={loading}>
          <span aria-hidden="true">↻</span> {loading ? "Refreshing" : "Refresh"}
        </button>
      </header>

      {error && (
        <div className="dashboard-alert" role="status">
          <span>Workspace data could not be loaded right now.</span>
          <button type="button" onClick={() => void refresh()}>Try again</button>
        </div>
      )}

      <section className="dashboard-metrics" aria-label="Conversation summary">
        {metrics.map((metric) => (
          <article className="metric-card" key={metric.label}>
            <span className={`metric-icon metric-icon-${metric.tone}`} aria-hidden="true">{metric.mark}</span>
            <div className="metric-copy">
              <p>{metric.label}</p>
              <strong aria-live="polite">{loading ? "—" : (metric.value ?? 0).toLocaleString()}</strong>
              <span>{metric.detail}</span>
            </div>
          </article>
        ))}
      </section>

      <div className="dashboard-columns">
        <section className="dashboard-panel" aria-labelledby="recent-title">
          <div className="dashboard-panel-heading">
            <div>
              <p className="eyebrow">YOUR INBOX</p>
              <h2 id="recent-title">Recent conversations</h2>
            </div>
            <Link href="/inbox" className="dashboard-text-link">Open inbox <span aria-hidden="true">→</span></Link>
          </div>
          {loading ? (
            <div className="dashboard-empty" role="status">Loading workspace activity…</div>
          ) : data?.recent.length ? (
            <ul className="recent-list">
              {data.recent.map((conversation) => (
                <li key={conversation.id}>
                  <Link href={`/inbox?conversation=${encodeURIComponent(conversation.id)}`} className="recent-item">
                    <span className="recent-avatar" aria-hidden="true">{(conversation.contact.name || "?").slice(0, 1).toUpperCase()}</span>
                    <span className="recent-main">
                      <span className="recent-name">{conversation.contact.name || "Unnamed contact"}</span>
                      <span className="recent-meta">{conversation.channel.name} <span aria-hidden="true">·</span> {conversation.status}</span>
                    </span>
                    <span className="recent-end">
                      <time>{formatActivity(conversation.last_message_at)}</time>
                      {conversation.unread_count > 0 && <span className="recent-unread">{conversation.unread_count} unread</span>}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <div className="dashboard-empty">
              <span className="empty-inbox-mark" aria-hidden="true">✳</span>
              <strong>{error ? "Activity is unavailable" : "Your inbox is ready"}</strong>
              <span>{error ? "Refresh to try loading the latest workspace data." : "New customer conversations will appear here."}</span>
            </div>
          )}
        </section>

        <aside className="dashboard-side-column">
          <section className="dashboard-panel channels-panel" aria-labelledby="channels-title">
            <div className="dashboard-panel-heading">
              <div>
              <p className="eyebrow">CHANNELS</p>
              <h2 id="channels-title">Your channels</h2>
              </div>
              <Link href="/channels" className="dashboard-icon-link" aria-label="Manage channels">→</Link>
            </div>
            {channels.length ? (
              <ul className="channel-list">
                {channels.slice(0, 4).map((channel) => (
                  <li key={channel.id}>
                    <span className="channel-mark" aria-hidden="true">{channel.channel_type.slice(0, 1).toUpperCase()}</span>
                    <span><strong>{channel.name}</strong><small>{channel.channel_type}</small></span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="channels-empty">
                <p>No channels are configured yet.</p>
                <Link href="/channels">Explore channel setup <span aria-hidden="true">→</span></Link>
              </div>
            )}
          </section>

          <section className="dashboard-tip">
            <span className="tip-mark" aria-hidden="true">✦</span>
            <div><strong>Keep every reply in sync</strong><p>Open the inbox to reply and follow new conversation activity as it arrives.</p></div>
            <Link href="/inbox" aria-label="Go to inbox">→</Link>
          </section>
        </aside>
      </div>
    </div>
  );
}
