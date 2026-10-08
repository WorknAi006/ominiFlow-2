"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";

import {
  ContactApiError,
  createContact,
  getContact,
  listContactConversations,
  listContacts,
  updateContact,
  type Contact,
} from "@/lib/contacts/browser";
import type { Conversation } from "@/lib/api/conversations";

const PAGE_SIZE = 20;

type Notice = { kind: "success" | "error"; text: string } | null;

interface ContactForm {
  phone_number: string;
  email: string;
  first_name: string;
  last_name: string;
  display_name: string;
}

const EMPTY_FORM: ContactForm = { phone_number: "", email: "", first_name: "", last_name: "", display_name: "" };

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleDateString([], { year: "numeric", month: "short", day: "numeric" });
}

function formatDateTime(value: string | null | undefined) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleString([], { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" });
}

function toForm(contact: Contact): ContactForm {
  return {
    phone_number: contact.phone_number ?? "",
    email: contact.email ?? "",
    first_name: contact.first_name ?? "",
    last_name: contact.last_name ?? "",
    display_name: contact.display_name ?? "",
  };
}

export function ContactsClient() {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);

  const [createForm, setCreateForm] = useState<ContactForm | null>(null);
  const [editing, setEditing] = useState<{ contact: Contact; form: ContactForm } | null>(null);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  const [details, setDetails] = useState<Contact | null>(null);
  const [relatedLoading, setRelatedLoading] = useState(false);
  const [related, setRelated] = useState<Conversation[] | null>(null);
  const [blocking, setBlocking] = useState(false);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const load = useCallback(async (targetPage: number, searchTerm: string) => {
    setLoading(true);
    setLoadError(false);
    try {
      const result = await listContacts({ page: targetPage, page_size: PAGE_SIZE, search: searchTerm || undefined });
      setContacts(result.items);
      setTotal(result.total);
    } catch (error) {
      if (!(error instanceof ContactApiError && error.status === 401)) setLoadError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void Promise.resolve().then(() => load(page, search));
  }, [load, page, search]);

  // Debounce the search box, resetting to the first page on a new term.
  const firstRender = useRef(true);
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    const handle = setTimeout(() => {
      setPage(1);
      setSearch(searchInput.trim());
    }, 350);
    return () => clearTimeout(handle);
  }, [searchInput]);

  const handleError = (error: unknown, fallback: string) =>
    setNotice({ kind: "error", text: error instanceof ContactApiError ? error.message : fallback });

  function validate(form: ContactForm, requireIdentity: boolean): string | null {
    if (requireIdentity && !form.phone_number.trim() && !form.email.trim()) {
      return "Enter a phone number or an email address.";
    }
    if (form.email.trim() && !form.email.includes("@")) return "Enter a valid email address.";
    return null;
  }

  function buildPayload(form: ContactForm) {
    const payload: Record<string, string> = {};
    if (form.phone_number.trim()) payload.phone_number = form.phone_number.trim();
    if (form.email.trim()) payload.email = form.email.trim();
    if (form.first_name.trim()) payload.first_name = form.first_name.trim();
    if (form.last_name.trim()) payload.last_name = form.last_name.trim();
    if (form.display_name.trim()) payload.display_name = form.display_name.trim();
    return payload;
  }

  async function submitCreate(event: FormEvent) {
    event.preventDefault();
    if (!createForm) return;
    const error = validate(createForm, true);
    if (error) return setFormError(error);
    setSaving(true);
    setFormError("");
    try {
      await createContact(buildPayload(createForm));
      setCreateForm(null);
      setNotice({ kind: "success", text: "Contact created." });
      setPage(1);
      await load(1, search);
    } catch (err) {
      setFormError(err instanceof ContactApiError ? err.message : "Could not create this contact.");
    } finally {
      setSaving(false);
    }
  }

  async function submitEdit(event: FormEvent) {
    event.preventDefault();
    if (!editing) return;
    const error = validate(editing.form, true);
    if (error) return setFormError(error);
    setSaving(true);
    setFormError("");
    try {
      // Send changed fields; clear name/email with null, keep phone non-null.
      const original = editing.contact;
      const form = editing.form;
      const payload: Record<string, unknown> = {};
      if (form.phone_number.trim() && form.phone_number.trim() !== (original.phone_number ?? "")) {
        payload.phone_number = form.phone_number.trim();
      }
      const emailNext = form.email.trim();
      if (emailNext !== (original.email ?? "")) payload.email = emailNext || null;
      for (const key of ["first_name", "last_name", "display_name"] as const) {
        const next = form[key].trim();
        if (next !== (original[key] ?? "")) payload[key] = next || null;
      }
      if (Object.keys(payload).length === 0) {
        setEditing(null);
        return;
      }
      const updated = await updateContact(original.id, payload);
      setEditing(null);
      setNotice({ kind: "success", text: "Contact updated." });
      if (details?.id === updated.id) setDetails(updated);
      await load(page, search);
    } catch (err) {
      setFormError(err instanceof ContactApiError ? err.message : "Could not update this contact.");
    } finally {
      setSaving(false);
    }
  }

  const openDetails = useCallback(async (contact: Contact) => {
    setDetails(contact);
    setRelated(null);
    setRelatedLoading(true);
    try {
      const fresh = await getContact(contact.id);
      setDetails(fresh);
      const conversations = await listContactConversations(contact.id, 1, 20);
      setRelated(conversations.items);
    } catch (error) {
      if (!(error instanceof ContactApiError && error.status === 401)) setRelated([]);
    } finally {
      setRelatedLoading(false);
    }
  }, []);

  async function toggleBlock(contact: Contact) {
    setBlocking(true);
    setNotice(null);
    try {
      const updated = await updateContact(contact.id, { is_blocked: !contact.is_blocked });
      setDetails((prev) => (prev && prev.id === updated.id ? updated : prev));
      setNotice({
        kind: "success",
        text: updated.is_blocked ? "Contact blocked — they will not receive messages." : "Contact unblocked.",
      });
      await load(page, search);
    } catch (error) {
      handleError(error, "Could not update this contact.");
    } finally {
      setBlocking(false);
    }
  }

  const rangeLabel = useMemo(() => {
    if (total === 0) return "No contacts";
    const start = (page - 1) * PAGE_SIZE + 1;
    const end = Math.min(page * PAGE_SIZE, total);
    return `${start}–${end} of ${total}`;
  }, [page, total]);

  return (
    <section className="page-enter max-w-5xl">
      <header className="channel-header">
        <div>
          <p className="eyebrow">OMNIFLOW WORKSPACE</p>
          <h1 className="page-title mt-2">Contacts</h1>
          <p className="page-subtitle mt-2">Customer profiles and conversation history for your workspace.</p>
        </div>
        <button type="button" className="channel-primary-btn" onClick={() => { setFormError(""); setCreateForm({ ...EMPTY_FORM }); }}>
          <span aria-hidden="true">+</span> New contact
        </button>
      </header>

      {notice && (
        <div className={`channel-notice channel-notice-${notice.kind}`} role="status">
          <span>{notice.text}</span>
          <button type="button" onClick={() => setNotice(null)} aria-label="Dismiss">×</button>
        </div>
      )}

      <div className="contact-toolbar">
        <label className="contact-search">
          <span className="sr-only">Search contacts</span>
          <span className="contact-search-icon" aria-hidden="true">⌕</span>
          <input
            type="search"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search by name, phone or email"
            maxLength={100}
          />
        </label>
        <span className="contact-range" aria-live="polite">{rangeLabel}</span>
      </div>

      {loading ? (
        <div className="channel-state" role="status">Loading contacts…</div>
      ) : loadError ? (
        <div className="channel-state channel-state-error" role="alert">
          <strong>Contacts could not be loaded.</strong>
          <p>The contacts service did not respond. Please try again.</p>
          <button type="button" className="channel-secondary-btn" onClick={() => void load(page, search)}>Try again</button>
        </div>
      ) : contacts.length === 0 ? (
        <div className="channel-state channel-empty">
          <span className="channel-empty-mark" aria-hidden="true">C</span>
          <strong>{search ? "No matching contacts" : "No contacts yet"}</strong>
          <p>{search ? "Try a different name, phone number or email." : "Contacts are created from conversations, or add one manually."}</p>
          {!search && (
            <button type="button" className="channel-primary-btn" onClick={() => { setFormError(""); setCreateForm({ ...EMPTY_FORM }); }}>New contact</button>
          )}
        </div>
      ) : (
        <>
          <div className="contact-table" role="table" aria-label="Contacts">
            <div className="contact-row contact-head" role="row">
              <span role="columnheader">Name</span>
              <span role="columnheader">Phone</span>
              <span role="columnheader">Email</span>
              <span role="columnheader">Status</span>
              <span role="columnheader">Created</span>
              <span role="columnheader" className="contact-actions-col">Actions</span>
            </div>
            {contacts.map((contact) => (
              <div className="contact-row" role="row" key={contact.id}>
                <span role="cell" data-label="Name" className="contact-name-cell">
                  <span className="contact-avatar" aria-hidden="true">{(contact.name || "?").slice(0, 1).toUpperCase()}</span>
                  <button type="button" className="contact-link" onClick={() => void openDetails(contact)}>
                    {contact.name || "Unnamed contact"}
                  </button>
                </span>
                <span role="cell" data-label="Phone">{contact.phone_number || contact.normalized_phone_number || "—"}</span>
                <span role="cell" data-label="Email">{contact.email || "—"}</span>
                <span role="cell" data-label="Status">
                  <span className={`channel-pill ${contact.is_blocked ? "channel-pill-bad" : "channel-pill-ok"}`}>
                    {contact.is_blocked ? "Blocked" : "Active"}
                  </span>
                </span>
                <span role="cell" data-label="Created">{formatDate(contact.created_at)}</span>
                <span role="cell" data-label="Actions" className="contact-actions-col">
                  <button type="button" className="channel-action" onClick={() => void openDetails(contact)}>View</button>
                  <button type="button" className="channel-action" onClick={() => { setFormError(""); setEditing({ contact, form: toForm(contact) }); }}>Edit</button>
                </span>
              </div>
            ))}
          </div>

          <nav className="contact-pagination" aria-label="Pagination">
            <button type="button" className="channel-secondary-btn" disabled={page <= 1 || loading} onClick={() => setPage((p) => Math.max(1, p - 1))}>
              ← Previous
            </button>
            <span>Page {page} of {totalPages}</span>
            <button type="button" className="channel-secondary-btn" disabled={page >= totalPages || loading} onClick={() => setPage((p) => p + 1)}>
              Next →
            </button>
          </nav>
        </>
      )}

      {/* Create / Edit modal */}
      {(createForm || editing) && (
        <div className="channel-modal-scrim" role="dialog" aria-modal="true" aria-labelledby="contact-form-title">
          <div className="channel-modal">
            <h2 id="contact-form-title">{createForm ? "New contact" : "Edit contact"}</h2>
            <p className="channel-modal-sub">A contact needs at least a phone number or an email address.</p>
            <form onSubmit={createForm ? submitCreate : submitEdit} className="channel-form">
              {(["first_name", "last_name", "display_name", "phone_number", "email"] as const).map((field) => {
                const labels: Record<string, string> = {
                  first_name: "First name", last_name: "Last name", display_name: "Display name",
                  phone_number: "Phone number", email: "Email",
                };
                const form = createForm ?? editing!.form;
                return (
                  <label className="channel-field" key={field}>
                    <span>{labels[field]}</span>
                    <input
                      type={field === "email" ? "email" : field === "phone_number" ? "tel" : "text"}
                      value={form[field]}
                      onChange={(e) => {
                        const value = e.target.value;
                        if (createForm) setCreateForm({ ...createForm, [field]: value });
                        else if (editing) setEditing({ ...editing, form: { ...editing.form, [field]: value } });
                      }}
                      placeholder={field === "phone_number" ? "+15555550123" : field === "email" ? "name@example.com" : ""}
                      autoComplete="off"
                    />
                  </label>
                );
              })}
              {formError && <p className="channel-form-error" role="alert">{formError}</p>}
              <div className="channel-modal-actions">
                <button type="button" className="channel-secondary-btn" onClick={() => { setCreateForm(null); setEditing(null); }} disabled={saving}>Cancel</button>
                <button type="submit" className="channel-primary-btn" disabled={saving}>
                  {saving ? "Saving…" : createForm ? "Create contact" : "Save changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Details modal */}
      {details && (
        <div className="channel-modal-scrim" role="dialog" aria-modal="true" aria-labelledby="contact-details-title">
          <div className="channel-modal contact-detail-modal">
            <div className="contact-detail-head">
              <span className="contact-avatar contact-avatar-lg" aria-hidden="true">{(details.name || "?").slice(0, 1).toUpperCase()}</span>
              <div>
                <h2 id="contact-details-title">{details.name || "Unnamed contact"}</h2>
                <span className={`channel-pill ${details.is_blocked ? "channel-pill-bad" : "channel-pill-ok"}`}>
                  {details.is_blocked ? "Blocked" : "Active"}
                </span>
              </div>
              <button type="button" className="contact-close" onClick={() => setDetails(null)} aria-label="Close">×</button>
            </div>

            <dl className="channel-facts contact-detail-facts">
              <div><dt>Phone</dt><dd>{details.phone_number || details.normalized_phone_number || "—"}</dd></div>
              <div><dt>Email</dt><dd>{details.email || "—"}</dd></div>
              <div><dt>First name</dt><dd>{details.first_name || "—"}</dd></div>
              <div><dt>Last name</dt><dd>{details.last_name || "—"}</dd></div>
              <div><dt>Profile name</dt><dd>{details.profile_name || "—"}</dd></div>
              <div><dt>Tags</dt><dd>Not available yet</dd></div>
              <div><dt>Created</dt><dd>{formatDate(details.created_at)}</dd></div>
              <div><dt>Last updated</dt><dd>{formatDateTime(details.updated_at)}</dd></div>
            </dl>

            <div className="contact-related">
              <h3>Conversations</h3>
              {relatedLoading ? (
                <p className="contact-muted">Loading conversations…</p>
              ) : related && related.length > 0 ? (
                <ul className="contact-conv-list">
                  {related.map((conversation) => (
                    <li key={conversation.id}>
                      <Link href={`/inbox?conversation=${encodeURIComponent(conversation.id)}`} className="contact-conv-item">
                        <span className="contact-conv-main">
                          <strong>{conversation.channel.name}</strong>
                          <small>{conversation.status}{conversation.last_message?.text ? ` · ${conversation.last_message.text}` : ""}</small>
                        </span>
                        <span className="contact-conv-end">
                          <time>{formatDateTime(conversation.last_message_at)}</time>
                          <span aria-hidden="true">→</span>
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="contact-muted">No conversations yet for this contact.</p>
              )}
            </div>

            <div className="channel-modal-actions contact-detail-actions">
              <button type="button" className={details.is_blocked ? "channel-secondary-btn" : "channel-secondary-btn channel-btn-danger-outline"} onClick={() => void toggleBlock(details)} disabled={blocking}>
                {blocking ? "Working…" : details.is_blocked ? "Unblock" : "Block"}
              </button>
              <button type="button" className="channel-primary-btn" onClick={() => { setFormError(""); setEditing({ contact: details, form: toForm(details) }); setDetails(null); }}>
                Edit contact
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
