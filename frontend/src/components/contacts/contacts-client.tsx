"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";

import {
  ContactApiError,
  bulkApplyTags,
  bulkDeleteContacts,
  createContact,
  createContactConversation,
  deleteAllContacts,
  deleteContact,
  exportContactsCsv,
  importContactsCsv,
  getContact,
  listContactConversations,
  listContacts,
  setContactTags,
  updateContact,
  updateContactFields,
  type Contact,
} from "@/lib/contacts/browser";
import { TagApiError, createTag, deleteTag, listTags, updateTag, type Tag } from "@/lib/tags/browser";
import {
  CustomFieldApiError,
  createCustomField,
  deleteCustomField,
  listCustomFields,
  updateCustomField,
  type CustomFieldDefinition,
} from "@/lib/custom-fields/browser";
import type { Conversation } from "@/lib/api/conversations";

const PAGE_SIZE = 20;

type Tab = "contacts" | "tags" | "fields";
type Notice = { kind: "success" | "error"; text: string } | null;

interface ContactForm {
  phone_number: string;
  email: string;
  first_name: string;
  last_name: string;
  display_name: string;
}

const EMPTY_FORM: ContactForm = { phone_number: "", email: "", first_name: "", last_name: "", display_name: "" };

const CHANNEL_LABEL: Record<string, string> = {
  whatsapp: "WhatsApp",
  instagram: "Instagram",
  facebook: "Facebook",
  web_chat: "Web Chat",
};

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleDateString([], { year: "numeric", month: "short", day: "numeric" });
}

function formatTime(value: string | null | undefined) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
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

function secondaryId(contact: Contact) {
  return contact.phone_number || contact.normalized_phone_number || contact.identities[0]?.external_id || contact.email || "—";
}

export function ContactsClient() {
  const [tab, setTab] = useState<Tab>("contacts");
  const [notice, setNotice] = useState<Notice>(null);

  // Contacts
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [channelFilter, setChannelFilter] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);

  // Selection + bulk
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [assignTagsOpen, setAssignTagsOpen] = useState(false);
  const [assignTagIds, setAssignTagIds] = useState<Set<string>>(new Set());
  const [deleteTargets, setDeleteTargets] = useState<string[] | null>(null);
  const [deleteAllOpen, setDeleteAllOpen] = useState(false);
  const [deleteAllInput, setDeleteAllInput] = useState("");
  const [working, setWorking] = useState(false);
  const [exporting, setExporting] = useState(false);

  // Create / edit / details
  const [createForm, setCreateForm] = useState<ContactForm | null>(null);
  const [editing, setEditing] = useState<{ contact: Contact; form: ContactForm } | null>(null);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);
  const [details, setDetails] = useState<Contact | null>(null);
  const [relatedLoading, setRelatedLoading] = useState(false);
  const [related, setRelated] = useState<Conversation[] | null>(null);
  const [blocking, setBlocking] = useState(false);

  // Tags
  const [tags, setTags] = useState<Tag[]>([]);
  const [tagForm, setTagForm] = useState<{ id: string | null; name: string; color: string } | null>(null);
  const [tagError, setTagError] = useState("");
  const [tagSaving, setTagSaving] = useState(false);

  // Custom Fields
  const [fields, setFields] = useState<CustomFieldDefinition[]>([]);
  const [fieldForm, setFieldForm] = useState<{ id: string | null; label: string; field_type: string; options: string } | null>(null);
  const [fieldError, setFieldError] = useState("");
  const [fieldSaving, setFieldSaving] = useState(false);

  // Filters popover
  const [filtersOpen, setFiltersOpen] = useState(false);

  // Import
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<{ accepted: number; skipped: number; errors: string[] } | null>(null);

  // Contact field values (for details modal)
  const [editingFields, setEditingFields] = useState<Record<string, string | number | boolean | string[] | null> | null>(null);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const load = useCallback(async (targetPage: number, searchTerm: string, channel: string, tagId: string) => {
    setLoading(true);
    setLoadError(false);
    try {
      const result = await listContacts({
        page: targetPage, page_size: PAGE_SIZE,
        search: searchTerm || undefined,
        channel_type: channel || undefined,
        tag_id: tagId || undefined,
      });
      setContacts(result.items);
      setTotal(result.total);
    } catch (error) {
      if (!(error instanceof ContactApiError && error.status === 401)) setLoadError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void Promise.resolve().then(() => load(page, search, channelFilter, tagFilter));
  }, [load, page, search, channelFilter, tagFilter]);

  const loadTagsAndFields = useCallback(async () => {
    try {
      const [tagsRes, fieldsRes] = await Promise.all([listTags(), listCustomFields()]);
      setTags(tagsRes.items);
      setFields(fieldsRes.items);
    } catch {
      // Tags and fields are optional context for the contacts view.
    }
  }, []);

  useEffect(() => { void loadTagsAndFields(); }, [loadTagsAndFields]);

  const firstRender = useRef(true);
  useEffect(() => {
    if (firstRender.current) { firstRender.current = false; return; }
    const handle = setTimeout(() => { setPage(1); setSearch(searchInput.trim()); }, 350);
    return () => clearTimeout(handle);
  }, [searchInput]);

  const handleError = (error: unknown, fallback: string) =>
    setNotice({ kind: "error", text: error instanceof ContactApiError || error instanceof TagApiError ? error.message : fallback });

  function buildPayload(form: ContactForm) {
    const payload: Record<string, string> = {};
    if (form.phone_number.trim()) payload.phone_number = form.phone_number.trim();
    if (form.email.trim()) payload.email = form.email.trim();
    if (form.first_name.trim()) payload.first_name = form.first_name.trim();
    if (form.last_name.trim()) payload.last_name = form.last_name.trim();
    if (form.display_name.trim()) payload.display_name = form.display_name.trim();
    return payload;
  }

  function validate(form: ContactForm): string | null {
    if (!form.phone_number.trim() && !form.email.trim()) return "Enter a phone number or an email address.";
    if (form.email.trim() && !form.email.includes("@")) return "Enter a valid email address.";
    return null;
  }

  async function submitCreate(event: FormEvent) {
    event.preventDefault();
    if (!createForm) return;
    const error = validate(createForm);
    if (error) return setFormError(error);
    setSaving(true); setFormError("");
    try {
      await createContact(buildPayload(createForm));
      setCreateForm(null);
      setNotice({ kind: "success", text: "Contact created." });
      setPage(1);
      await load(1, search, channelFilter, tagFilter);
    } catch (err) {
      setFormError(err instanceof ContactApiError ? err.message : "Could not create this contact.");
    } finally { setSaving(false); }
  }

  async function submitEdit(event: FormEvent) {
    event.preventDefault();
    if (!editing) return;
    const error = validate(editing.form);
    if (error) return setFormError(error);
    setSaving(true); setFormError("");
    try {
      const original = editing.contact;
      const form = editing.form;
      const payload: Record<string, unknown> = {};
      if (form.phone_number.trim() && form.phone_number.trim() !== (original.phone_number ?? "")) payload.phone_number = form.phone_number.trim();
      const emailNext = form.email.trim();
      if (emailNext !== (original.email ?? "")) payload.email = emailNext || null;
      for (const key of ["first_name", "last_name", "display_name"] as const) {
        const next = form[key].trim();
        if (next !== (original[key] ?? "")) payload[key] = next || null;
      }
      if (Object.keys(payload).length === 0) { setEditing(null); return; }
      const updated = await updateContact(original.id, payload);
      setEditing(null);
      setNotice({ kind: "success", text: "Contact updated." });
      if (details?.id === updated.id) setDetails(updated);
      await load(page, search, channelFilter, tagFilter);
    } catch (err) {
      setFormError(err instanceof ContactApiError ? err.message : "Could not update this contact.");
    } finally { setSaving(false); }
  }

  const openDetails = useCallback(async (contact: Contact) => {
    setDetails(contact); setRelated(null); setRelatedLoading(true);
    try {
      const fresh = await getContact(contact.id);
      setDetails(fresh);
      const conversations = await listContactConversations(contact.id, 1, 20);
      setRelated(conversations.items);
    } catch (error) {
      if (!(error instanceof ContactApiError && error.status === 401)) setRelated([]);
    } finally { setRelatedLoading(false); }
  }, []);

  async function toggleBlock(contact: Contact) {
    setBlocking(true); setNotice(null);
    try {
      const updated = await updateContact(contact.id, { is_blocked: !contact.is_blocked });
      setDetails((prev) => (prev && prev.id === updated.id ? updated : prev));
      setNotice({ kind: "success", text: updated.is_blocked ? "Contact blocked." : "Contact unblocked." });
      await load(page, search, channelFilter, tagFilter);
    } catch (error) { handleError(error, "Could not update this contact."); }
    finally { setBlocking(false); }
  }

  async function sendMessageToContact(contact: Contact) {
    setBlocking(true);
    setNotice(null);
    try {
      const preferredChannel = contact.identities.find((i) => i.channel_type === "whatsapp" || i.channel_type === "web_chat")?.channel_type ?? "whatsapp";
      const conversation = await createContactConversation(contact.id, preferredChannel);
      window.location.assign(`/inbox?conversation=${encodeURIComponent(conversation.id)}`);
    } catch (error) { handleError(error, "Could not open the inbox conversation."); }
    finally { setBlocking(false); }
  }

  // ----- selection -----
  const allVisibleSelected = contacts.length > 0 && contacts.every((c) => selected.has(c.id));
  function toggleOne(id: string) {
    setSelected((prev) => { const next = new Set(prev); next.has(id) ? next.delete(id) : next.add(id); return next; });
  }
  function toggleAll() {
    setSelected((prev) => {
      if (contacts.every((c) => prev.has(c.id))) { const next = new Set(prev); contacts.forEach((c) => next.delete(c.id)); return next; }
      const next = new Set(prev); contacts.forEach((c) => next.add(c.id)); return next;
    });
  }
  const clearSelection = () => setSelected(new Set());

  // ----- bulk actions -----
  async function runBulkAssignTags() {
    const ids = [...selected];
    if (ids.length === 0 || assignTagIds.size === 0) return;
    setWorking(true);
    try {
      await bulkApplyTags(ids, [...assignTagIds], []);
      setAssignTagsOpen(false); setAssignTagIds(new Set());
      setNotice({ kind: "success", text: `Tagged ${ids.length} contact${ids.length === 1 ? "" : "s"}.` });
      await load(page, search, channelFilter, tagFilter);
      await loadTagsAndFields();
    } catch (error) { handleError(error, "Could not assign tags."); }
    finally { setWorking(false); }
  }

  async function runDelete() {
    if (!deleteTargets) return;
    setWorking(true);
    try {
      if (deleteTargets.length === 1) await deleteContact(deleteTargets[0]);
      else await bulkDeleteContacts(deleteTargets);
      const count = deleteTargets.length;
      setDeleteTargets(null);
      setSelected((prev) => { const next = new Set(prev); deleteTargets.forEach((id) => next.delete(id)); return next; });
      setDetails(null);
      setNotice({ kind: "success", text: `Deleted ${count} contact${count === 1 ? "" : "s"}.` });
      await load(1, search, channelFilter, tagFilter);
      setPage(1);
    } catch (error) { handleError(error, "Could not delete the selected contacts."); }
    finally { setWorking(false); }
  }

  async function runDeleteAll() {
    setWorking(true);
    try {
      const result = await deleteAllContacts(deleteAllInput.trim());
      setDeleteAllOpen(false); setDeleteAllInput(""); clearSelection();
      setNotice({ kind: "success", text: `Deleted ${result.deleted} contacts.` });
      setPage(1);
      await load(1, "", "", "");
      setSearch(""); setSearchInput(""); setChannelFilter(""); setTagFilter("");
    } catch (error) { handleError(error, "Could not delete all contacts."); }
    finally { setWorking(false); }
  }

  async function runExport() {
    setExporting(true);
    try {
      const blob = await exportContactsCsv({ search: search || undefined, channel_type: channelFilter || undefined, tag_id: tagFilter || undefined });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url; link.download = "contacts.csv"; link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) { handleError(error, "Could not export contacts."); }
    finally { setExporting(false); }
  }

  // ----- tags tab -----
  async function submitTag(event: FormEvent) {
    event.preventDefault();
    if (!tagForm) return;
    const name = tagForm.name.trim();
    if (name.length < 1) return setTagError("Enter a tag name.");
    setTagSaving(true); setTagError("");
    try {
      if (tagForm.id) await updateTag(tagForm.id, { name, color: tagForm.color });
      else await createTag({ name, color: tagForm.color });
      setTagForm(null);
      setNotice({ kind: "success", text: tagForm.id ? "Tag updated." : "Tag created." });
      await loadTagsAndFields();
    } catch (error) { setTagError(error instanceof TagApiError ? error.message : "Could not save this tag."); }
    finally { setTagSaving(false); }
  }

  async function removeTag(tag: Tag) {
    setWorking(true);
    try {
      await deleteTag(tag.id);
      setNotice({ kind: "success", text: "Tag deleted." });
      await loadTagsAndFields();
      if (tagFilter === tag.id) setTagFilter("");
      await load(page, search, channelFilter, tagFilter === tag.id ? "" : tagFilter);
    } catch (error) { handleError(error, "Could not delete this tag."); }
    finally { setWorking(false); }
  }

  // ----- fields tab -----
  async function submitField(event: FormEvent) {
    event.preventDefault();
    if (!fieldForm) return;
    const label = fieldForm.label.trim();
    if (label.length < 1) return setFieldError("Enter a field name.");
    const fieldType = fieldForm.field_type as "text" | "number" | "date" | "select" | "multiselect" | "boolean";
    const opts = ["select", "multiselect"].includes(fieldType)
      ? fieldForm.options.split(",").map((s) => s.trim()).filter(Boolean)
      : null;
    if (opts !== null && opts.length === 0) return setFieldError("Enter at least one option.");
    
    setFieldSaving(true); setFieldError("");
    try {
      if (fieldForm.id) await updateCustomField(fieldForm.id, { label, options: opts });
      else await createCustomField({ label, field_type: fieldType, options: opts });
      setFieldForm(null);
      setNotice({ kind: "success", text: fieldForm.id ? "Field updated." : "Field created." });
      await loadTagsAndFields();
    } catch (error) { setFieldError(error instanceof CustomFieldApiError ? error.message : "Could not save this field."); }
    finally { setFieldSaving(false); }
  }

  async function removeField(field: CustomFieldDefinition) {
    setWorking(true);
    try {
      await deleteCustomField(field.id);
      setNotice({ kind: "success", text: "Field deleted." });
      await loadTagsAndFields();
    } catch (error) { handleError(error, "Could not delete this field."); }
    finally { setWorking(false); }
  }

  // ----- import -----
  async function handleImport(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    event.target.value = "";
    
    setImporting(true); setNotice(null);
    try {
      const result = await importContactsCsv(file);
      setImportResult(result);
      if (result.accepted > 0) {
        setPage(1);
        await load(1, search, channelFilter, tagFilter);
      }
    } catch (error) { handleError(error, "Could not import contacts."); }
    finally { setImporting(false); }
  }

  const rangeLabel = useMemo(() => {
    if (total === 0) return "No contacts";
    const start = (page - 1) * PAGE_SIZE + 1;
    const end = Math.min(page * PAGE_SIZE, total);
    return `${start}–${end} of ${total}`;
  }, [page, total]);

  return (
    <section className="page-enter">
      <header className="channel-header">
        <div>
          <p className="eyebrow">OMNIFLOW WORKSPACE</p>
          <h1 className="page-title mt-2">Contacts</h1>
          <p className="page-subtitle mt-2">Manage and organize your contacts.</p>
        </div>
      </header>

      <div className="contacts-tabs" role="tablist" aria-label="Contacts sections">
        {([["contacts", "Contacts"], ["tags", "Tags"], ["fields", "Custom Fields"]] as const).map(([key, label]) => (
          <button key={key} type="button" role="tab" aria-selected={tab === key}
            className={`contacts-tab ${tab === key ? "contacts-tab-active" : ""}`} onClick={() => setTab(key)}>
            {label}
          </button>
        ))}
      </div>

      {notice && (
        <div className={`channel-notice channel-notice-${notice.kind}`} role="status">
          <span>{notice.text}</span>
          <button type="button" onClick={() => setNotice(null)} aria-label="Dismiss">×</button>
        </div>
      )}

      {tab === "contacts" && (
        <>
          <div className="contacts-toolbar">
            <label className="contact-search">
              <span className="sr-only">Search contacts</span>
              <span className="contact-search-icon" aria-hidden="true">⌕</span>
              <input type="search" value={searchInput} onChange={(e) => setSearchInput(e.target.value)} placeholder="Search contacts…" maxLength={100} />
            </label>
            <div className="contacts-toolbar-actions relative">
              <button type="button" className="channel-secondary-btn" onClick={() => setFiltersOpen(!filtersOpen)}>
                Filters {(channelFilter || tagFilter) ? " (Active)" : ""}
              </button>
              {filtersOpen && (
                <div className="absolute top-full right-0 mt-2 w-64 bg-white border border-slate-200 rounded-lg shadow-xl z-10 p-4 text-left">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-medium text-slate-800">Filter Contacts</h3>
                    <button type="button" className="text-slate-400 hover:text-slate-600" onClick={() => setFiltersOpen(false)} aria-label="Close">×</button>
                  </div>
                  
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-slate-700 mb-1">Source</label>
                    <select className="contacts-filter w-full" value={channelFilter} onChange={(e) => { setChannelFilter(e.target.value); setPage(1); }} aria-label="Filter by channel">
                      <option value="">All channels</option>
                      {Object.entries(CHANNEL_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                    </select>
                  </div>

                  <div className="mb-4">
                    <label className="block text-sm font-medium text-slate-700 mb-1">Tags</label>
                    <select className="contacts-filter w-full" value={tagFilter} onChange={(e) => { setTagFilter(e.target.value); setPage(1); }} aria-label="Filter by tag">
                      <option value="">All tags</option>
                      {tags.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                    </select>
                  </div>

                  <button type="button" className="w-full channel-secondary-btn" onClick={() => { setChannelFilter(""); setTagFilter(""); setPage(1); }}>
                    Clear Filters
                  </button>
                </div>
              )}
              <input type="file" ref={fileInputRef} onChange={(e) => void handleImport(e)} accept=".csv" className="hidden" />
              <button type="button" className="channel-secondary-btn" disabled={importing} onClick={() => fileInputRef.current?.click()}>
                {importing ? "Importing…" : "↓ Import CSV"}
              </button>
              <button type="button" className="channel-secondary-btn" disabled={exporting || total === 0} onClick={() => void runExport()}>
                {exporting ? "Exporting…" : "↑ Export CSV"}
              </button>
              <button type="button" className="channel-primary-btn" onClick={() => { setFormError(""); setCreateForm({ ...EMPTY_FORM }); }}>
                <span aria-hidden="true">+</span> Add Contact
              </button>
            </div>
          </div>

          {selected.size > 0 && (
            <div className="contacts-bulkbar" role="region" aria-label="Bulk actions">
              <span>{selected.size} contact{selected.size === 1 ? "" : "s"} selected</span>
              <div className="contacts-bulk-actions">
                <button type="button" className="channel-action" onClick={clearSelection}>Clear selection</button>
                <button type="button" className="channel-action" onClick={() => { setAssignTagIds(new Set()); setAssignTagsOpen(true); }}>Assign tags…</button>
                <button type="button" className="channel-action channel-action-danger" onClick={() => setDeleteTargets([...selected])}>Delete selected</button>
              </div>
            </div>
          )}

          {loading ? (
            <div className="channel-state" role="status">Loading contacts…</div>
          ) : loadError ? (
            <div className="channel-state channel-state-error" role="alert">
              <strong>Contacts could not be loaded.</strong>
              <p>The contacts service did not respond. Please try again.</p>
              <button type="button" className="channel-secondary-btn" onClick={() => void load(page, search, channelFilter, tagFilter)}>Try again</button>
            </div>
          ) : contacts.length === 0 ? (
            <div className="channel-state channel-empty">
              <span className="channel-empty-mark" aria-hidden="true">C</span>
              <strong>{search || channelFilter || tagFilter ? "No matching contacts" : "No contacts yet"}</strong>
              <p>{search || channelFilter || tagFilter ? "Try a different search or filter." : "Contacts are created from conversations, or add one manually."}</p>
            </div>
          ) : (
            <>
              <div className="contacts-table" role="table" aria-label="Contacts">
                <div className="contacts-grid contacts-head" role="row">
                  <span role="columnheader"><input type="checkbox" checked={allVisibleSelected} onChange={toggleAll} aria-label="Select all visible contacts" /></span>
                  <span role="columnheader">Contact info</span>
                  <span role="columnheader">Source</span>
                  <span role="columnheader">Assigned agent</span>
                  <span role="columnheader">Created</span>
                  <span role="columnheader">Tags</span>
                  <span role="columnheader" className="contacts-actions-col">Actions</span>
                </div>
                {contacts.map((contact) => (
                  <div className={`contacts-grid contacts-body-row ${selected.has(contact.id) ? "contacts-row-selected" : ""}`} role="row" key={contact.id}>
                    <span role="cell"><input type="checkbox" checked={selected.has(contact.id)} onChange={() => toggleOne(contact.id)} aria-label={`Select ${contact.name ?? "contact"}`} /></span>
                    <span role="cell" data-label="Contact" className="contact-name-cell">
                      <span className="contact-avatar" aria-hidden="true">{(contact.name || "?").slice(0, 1).toUpperCase()}</span>
                      <span className="contact-info-text">
                        <button type="button" className="contact-link" onClick={() => void openDetails(contact)}>{contact.name || "Unknown Contact"}</button>
                        <small>{secondaryId(contact)}</small>
                      </span>
                    </span>
                    <span role="cell" data-label="Source" className="contacts-source">
                      {contact.identities.length === 0 ? <span className="contacts-muted">Manual</span> : contact.identities.map((i) => (
                        <span key={i.channel_type} className={`source-badge source-${i.channel_type}`}>{CHANNEL_LABEL[i.channel_type] ?? i.channel_type}</span>
                      ))}
                    </span>
                    <span role="cell" data-label="Assigned agent"><span className="contacts-muted">Unassigned</span></span>
                    <span role="cell" data-label="Created">
                      <span className="contacts-created">{formatDate(contact.created_at)}</span>
                      <small>{formatTime(contact.created_at)}</small>
                    </span>
                    <span role="cell" data-label="Tags" className="contacts-tags-cell">
                      {contact.tags.length === 0 ? <span className="contacts-muted">No tags</span> : contact.tags.map((t) => (
                        <span key={t.id} className="tag-chip" style={{ borderColor: t.color, color: t.color }}>{t.name}</span>
                      ))}
                    </span>
                    <span role="cell" data-label="Actions" className="contacts-actions-col">
                      <button type="button" className="channel-action" onClick={() => void openDetails(contact)}>View</button>
                      <button type="button" className="channel-action" onClick={() => void sendMessageToContact(contact)}>Message</button>
                      <button type="button" className="channel-action" onClick={() => { setFormError(""); setEditing({ contact, form: toForm(contact) }); }}>Edit</button>
                      <button type="button" className="channel-action channel-action-danger" onClick={() => setDeleteTargets([contact.id])}>Delete</button>
                    </span>
                  </div>
                ))}
              </div>

              <div className="contacts-footer">
                <button type="button" className="contacts-danger-link" onClick={() => { setDeleteAllInput(""); setDeleteAllOpen(true); }}>Delete ALL contacts</button>
                <nav className="contact-pagination" aria-label="Pagination">
                  <button type="button" className="channel-secondary-btn" disabled={page <= 1 || loading} onClick={() => setPage((p) => Math.max(1, p - 1))}>← Previous</button>
                  <span>{rangeLabel} · Page {page} of {totalPages}</span>
                  <button type="button" className="channel-secondary-btn" disabled={page >= totalPages || loading} onClick={() => setPage((p) => p + 1)}>Next →</button>
                </nav>
              </div>
            </>
          )}
        </>
      )}

      {tab === "tags" && (
        <div className="contacts-tabpanel">
          <div className="contacts-toolbar">
            <p className="page-subtitle">Organize contacts with tenant-wide tags.</p>
            <button type="button" className="channel-primary-btn" onClick={() => { setTagError(""); setTagForm({ id: null, name: "", color: "#176b59" }); }}>
              <span aria-hidden="true">+</span> Create Tag
            </button>
          </div>
          {tags.length === 0 ? (
            <div className="channel-state channel-empty"><span className="channel-empty-mark" aria-hidden="true">#</span><strong>No tags yet</strong><p>Create a tag to label and filter your contacts.</p></div>
          ) : (
            <div className="contacts-table" role="table" aria-label="Tags">
              <div className="tags-grid contacts-head" role="row">
                <span role="columnheader">Tag</span><span role="columnheader">Contacts</span><span role="columnheader">Color</span><span role="columnheader">Created</span><span role="columnheader" className="contacts-actions-col">Actions</span>
              </div>
              {tags.map((t) => (
                <div className="tags-grid contacts-body-row" role="row" key={t.id}>
                  <span role="cell" data-label="Tag"><span className="tag-chip" style={{ borderColor: t.color, color: t.color }}>{t.name}</span></span>
                  <span role="cell" data-label="Contacts">{t.contact_count}</span>
                  <span role="cell" data-label="Color"><span className="tag-swatch" style={{ background: t.color }} aria-hidden="true" /> {t.color}</span>
                  <span role="cell" data-label="Created">{formatDate(t.created_at)}</span>
                  <span role="cell" data-label="Actions" className="contacts-actions-col">
                    <button type="button" className="channel-action" onClick={() => { setTagError(""); setTagForm({ id: t.id, name: t.name, color: t.color }); }}>Edit</button>
                    <button type="button" className="channel-action channel-action-danger" disabled={working} onClick={() => void removeTag(t)}>Delete</button>
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === "fields" && (
        <div className="contacts-tabpanel">
          <div className="contacts-toolbar">
            <p className="page-subtitle">Define your own contact fields (company, city, lead source, and more).</p>
            <button type="button" className="channel-primary-btn" onClick={() => { setFieldError(""); setFieldForm({ id: null, label: "", field_type: "text", options: "" }); }}>
              <span aria-hidden="true">+</span> Create Field
            </button>
          </div>
          {fields.length === 0 ? (
            <div className="channel-state channel-empty">
              <span className="channel-empty-mark" aria-hidden="true">⋮</span>
              <strong>No custom fields yet</strong>
              <p>Create fields to store additional information about your contacts.</p>
            </div>
          ) : (
            <div className="contacts-table" role="table" aria-label="Custom Fields">
              <div className="tags-grid contacts-head" role="row">
                <span role="columnheader">Field Name</span>
                <span role="columnheader">Type</span>
                <span role="columnheader">Created</span>
                <span role="columnheader" className="contacts-actions-col">Actions</span>
              </div>
              {fields.map((f) => (
                <div className="tags-grid contacts-body-row" role="row" key={f.id}>
                  <span role="cell" data-label="Field Name"><strong>{f.label}</strong></span>
                  <span role="cell" data-label="Type">
                    <span className="channel-pill channel-pill-ok">{f.field_type}</span>
                  </span>
                  <span role="cell" data-label="Created">{formatDate(f.created_at)}</span>
                  <span role="cell" data-label="Actions" className="contacts-actions-col">
                    <button type="button" className="channel-action" onClick={() => { setFieldError(""); setFieldForm({ id: f.id, label: f.label, field_type: f.field_type, options: f.options ? f.options.join(", ") : "" }); }}>Edit</button>
                    <button type="button" className="channel-action channel-action-danger" disabled={working} onClick={() => void removeField(f)}>Delete</button>
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Create / Edit modal */}
      {(createForm || editing) && (
        <div className="channel-modal-scrim" role="dialog" aria-modal="true" aria-labelledby="contact-form-title">
          <div className="channel-modal">
            <h2 id="contact-form-title">{createForm ? "Add contact" : "Edit contact"}</h2>
            <p className="channel-modal-sub">A contact needs at least a phone number or an email address.</p>
            <form onSubmit={createForm ? submitCreate : submitEdit} className="channel-form">
              {(["first_name", "last_name", "display_name", "phone_number", "email"] as const).map((field) => {
                const labels: Record<string, string> = { first_name: "First name", last_name: "Last name", display_name: "Display name", phone_number: "Phone number", email: "Email" };
                const form = createForm ?? editing!.form;
                return (
                  <label className="channel-field" key={field}>
                    <span>{labels[field]}</span>
                    <input type={field === "email" ? "email" : field === "phone_number" ? "tel" : "text"} value={form[field]}
                      onChange={(e) => { const value = e.target.value; setFormError(""); if (createForm) setCreateForm({ ...createForm, [field]: value }); else if (editing) setEditing({ ...editing, form: { ...editing.form, [field]: value } }); }}
                      placeholder={field === "phone_number" ? "+15555550123" : field === "email" ? "name@example.com" : ""} autoComplete="off" />
                  </label>
                );
              })}
              {formError && <p className="channel-form-error" role="alert">{formError}</p>}
              <div className="channel-modal-actions">
                <button type="button" className="channel-secondary-btn" onClick={() => { setCreateForm(null); setEditing(null); }} disabled={saving}>Cancel</button>
                <button type="submit" className="channel-primary-btn" disabled={saving}>{saving ? "Saving…" : createForm ? "Create contact" : "Save changes"}</button>
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
                <h2 id="contact-details-title">{details.name || "Unknown Contact"}</h2>
                <span className={`channel-pill ${details.is_blocked ? "channel-pill-bad" : "channel-pill-ok"}`}>{details.is_blocked ? "Blocked" : "Active"}</span>
              </div>
              <button type="button" className="contact-close" onClick={() => setDetails(null)} aria-label="Close">×</button>
            </div>

            <dl className="channel-facts contact-detail-facts">
              <div><dt>Phone</dt><dd>{details.phone_number || details.normalized_phone_number || "—"}</dd></div>
              <div><dt>Email</dt><dd>{details.email || "—"}</dd></div>
              <div><dt>Source</dt><dd>{details.identities.length ? details.identities.map((i) => CHANNEL_LABEL[i.channel_type] ?? i.channel_type).join(", ") : "Manual"}</dd></div>
              <div><dt>Created</dt><dd>{formatDateTime(details.created_at)}</dd></div>
            </dl>

            <div className="contact-related">
              <div className="flex items-center justify-between">
                <h3>Custom Fields</h3>
                {fields.length > 0 && !editingFields && (
                  <button type="button" className="text-sm font-medium text-indigo-600 hover:text-indigo-700" onClick={() => setEditingFields(details.field_values || {})}>Edit Fields</button>
                )}
              </div>
              
              {fields.length === 0 ? (
                <p className="contact-muted mt-2">No custom fields defined.</p>
              ) : editingFields ? (
                <form className="mt-4 space-y-3" onSubmit={async (e) => {
                  e.preventDefault();
                  setWorking(true);
                  try {
                    const updated = await updateContactFields(details.id, editingFields);
                    setDetails({ ...details, field_values: updated.field_values });
                    setEditingFields(null);
                    setNotice({ kind: "success", text: "Contact fields updated." });
                    await load(page, search, channelFilter, tagFilter);
                  } catch (error) { handleError(error, "Could not update custom fields."); }
                  finally { setWorking(false); }
                }}>
                  {fields.map(f => (
                    <label key={f.id} className="channel-field mb-2">
                      <span>{f.label}</span>
                      {f.field_type === "boolean" ? (
                        <select className="channel-input" value={editingFields[f.id] === true ? "true" : editingFields[f.id] === false ? "false" : ""} onChange={e => setEditingFields({ ...editingFields, [f.id]: e.target.value === "true" ? true : e.target.value === "false" ? false : null })}>
                          <option value="">--</option>
                          <option value="true">Yes</option>
                          <option value="false">No</option>
                        </select>
                      ) : f.field_type === "select" ? (
                        <select className="channel-input" value={String(editingFields[f.id] ?? "")} onChange={e => setEditingFields({ ...editingFields, [f.id]: e.target.value || null })}>
                          <option value="">--</option>
                          {f.options?.map(o => <option key={o} value={o}>{o}</option>)}
                        </select>
                      ) : f.field_type === "multiselect" ? (
                        <div className="flex flex-col gap-1 mt-1">
                          {f.options?.map(o => {
                            const arr = (editingFields[f.id] as string[]) || [];
                            return (
                              <label key={o} className="flex items-center gap-2 text-sm font-normal cursor-pointer">
                                <input type="checkbox" checked={arr.includes(o)} onChange={e => {
                                  const next = e.target.checked ? [...arr, o] : arr.filter(x => x !== o);
                                  setEditingFields({ ...editingFields, [f.id]: next.length > 0 ? next : null });
                                }} className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-600" /> {o}
                              </label>
                            );
                          })}
                        </div>
                      ) : f.field_type === "date" ? (
                        <input type="date" className="channel-input" value={String(editingFields[f.id] ?? "")} onChange={e => setEditingFields({ ...editingFields, [f.id]: e.target.value || null })} />
                      ) : f.field_type === "number" ? (
                        <input type="number" step="any" className="channel-input" value={(editingFields[f.id] as string | number) ?? ""} onChange={e => setEditingFields({ ...editingFields, [f.id]: e.target.value ? Number(e.target.value) : null })} />
                      ) : (
                        <input type="text" className="channel-input" value={String(editingFields[f.id] ?? "")} onChange={e => setEditingFields({ ...editingFields, [f.id]: e.target.value || null })} />
                      )}
                    </label>
                  ))}
                  <div className="flex gap-2 mt-4">
                    <button type="button" className="channel-secondary-btn flex-1" disabled={working} onClick={() => setEditingFields(null)}>Cancel</button>
                    <button type="submit" className="channel-primary-btn flex-1" disabled={working}>{working ? "Saving..." : "Save Fields"}</button>
                  </div>
                </form>
              ) : (
                <dl className="channel-facts contact-detail-facts mt-3">
                  {fields.map(f => {
                    const val = details.field_values?.[f.id];
                    let display = "—";
                    if (val !== undefined && val !== null && val !== "") {
                      if (f.field_type === "boolean") display = val ? "Yes" : "No";
                      else if (f.field_type === "multiselect") display = Array.isArray(val) ? val.join(", ") : String(val);
                      else display = String(val);
                    }
                    return (
                      <div key={f.id}><dt>{f.label}</dt><dd>{display}</dd></div>
                    );
                  })}
                </dl>
              )}
            </div>

            <div className="contact-related">
              <h3>Tags</h3>
              <div className="contacts-tags-cell mt-2">
                {tags.length === 0 ? <span className="contacts-muted">No tags defined. Create tags in the Tags tab.</span> : tags.map((t) => {
                  const on = details.tags.some((ct) => ct.id === t.id);
                  return (
                    <button key={t.id} type="button" className={`tag-chip tag-chip-toggle ${on ? "tag-chip-on" : ""}`}
                      style={on ? { background: t.color, borderColor: t.color, color: "#fff" } : { borderColor: t.color, color: t.color }}
                      onClick={async () => {
                        const nextIds = on ? details.tags.filter((ct) => ct.id !== t.id).map((ct) => ct.id) : [...details.tags.map((ct) => ct.id), t.id];
                        try {
                          const updated = await setContactTags(details.id, nextIds);
                          setDetails(updated);
                          await load(page, search, channelFilter, tagFilter);
                          await loadTagsAndFields();
                        } catch (error) { handleError(error, "Could not update tags."); }
                      }}>{t.name}</button>
                  );
                })}
              </div>
            </div>

            <div className="contact-related">
              <h3>Conversations</h3>
              {relatedLoading ? <p className="contact-muted">Loading conversations…</p> : related && related.length > 0 ? (
                <ul className="contact-conv-list">
                  {related.map((conversation) => (
                    <li key={conversation.id}>
                      <Link href={`/inbox?conversation=${encodeURIComponent(conversation.id)}`} className="contact-conv-item">
                        <span className="contact-conv-main"><strong>{conversation.channel.name}</strong><small>{conversation.status}{conversation.last_message?.text ? ` · ${conversation.last_message.text}` : ""}</small></span>
                        <span className="contact-conv-end"><time>{formatDateTime(conversation.last_message_at)}</time><span aria-hidden="true">→</span></span>
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : <p className="contact-muted">No conversations yet for this contact.</p>}
            </div>

            <div className="channel-modal-actions contact-detail-actions">
              <button type="button" className={details.is_blocked ? "channel-secondary-btn" : "channel-secondary-btn channel-btn-danger-outline"} onClick={() => void toggleBlock(details)} disabled={blocking}>
                {blocking ? "Working…" : details.is_blocked ? "Unblock" : "Block"}
              </button>
              <button type="button" className="channel-primary-btn" onClick={() => { void sendMessageToContact(details); }} disabled={blocking}>Message</button>
              <button type="button" className="channel-primary-btn" onClick={() => { setFormError(""); setEditing({ contact: details, form: toForm(details) }); setDetails(null); }}>Edit contact</button>
            </div>
          </div>
        </div>
      )}

      {/* Bulk assign tags modal */}
      {assignTagsOpen && (
        <div className="channel-modal-scrim" role="dialog" aria-modal="true" aria-labelledby="assign-tags-title">
          <div className="channel-modal">
            <h2 id="assign-tags-title">Assign tags</h2>
            <p className="channel-modal-sub">Add tags to {selected.size} selected contact{selected.size === 1 ? "" : "s"}.</p>
            <div className="channel-form">
              {tags.length === 0 ? <p className="contacts-muted">No tags defined yet. Create tags in the Tags tab.</p> : tags.map((t) => (
                <label key={t.id} className="contacts-check-row">
                  <input type="checkbox" checked={assignTagIds.has(t.id)} onChange={() => setAssignTagIds((prev) => { const next = new Set(prev); next.has(t.id) ? next.delete(t.id) : next.add(t.id); return next; })} />
                  <span className="tag-chip" style={{ borderColor: t.color, color: t.color }}>{t.name}</span>
                </label>
              ))}
            </div>
            <div className="channel-modal-actions">
              <button type="button" className="channel-secondary-btn" onClick={() => setAssignTagsOpen(false)} disabled={working}>Cancel</button>
              <button type="button" className="channel-primary-btn" disabled={working || assignTagIds.size === 0} onClick={() => void runBulkAssignTags()}>{working ? "Applying…" : "Apply tags"}</button>
            </div>
          </div>
        </div>
      )}

      {/* Delete selected confirm */}
      {deleteTargets && (
        <div className="channel-modal-scrim" role="dialog" aria-modal="true" aria-labelledby="delete-title">
          <div className="channel-modal channel-modal-sm">
            <h2 id="delete-title">Delete {deleteTargets.length} contact{deleteTargets.length === 1 ? "" : "s"}?</h2>
            <p className="channel-modal-sub">This also removes their conversations and messages. This action cannot be undone.</p>
            <div className="channel-modal-actions">
              <button type="button" className="channel-secondary-btn" onClick={() => setDeleteTargets(null)} disabled={working}>Cancel</button>
              <button type="button" className="channel-primary-btn channel-btn-danger" onClick={() => void runDelete()} disabled={working}>{working ? "Deleting…" : "Delete"}</button>
            </div>
          </div>
        </div>
      )}

      {/* Delete ALL confirm */}
      {deleteAllOpen && (
        <div className="channel-modal-scrim" role="dialog" aria-modal="true" aria-labelledby="delete-all-title">
          <div className="channel-modal channel-modal-sm">
            <h2 id="delete-all-title">Delete ALL contacts?</h2>
            <p className="channel-modal-sub">This permanently deletes every contact in this workspace, along with their conversations and messages. Type <strong>DELETE ALL</strong> to confirm.</p>
            <label className="channel-field"><span className="sr-only">Confirmation</span>
              <input value={deleteAllInput} onChange={(e) => setDeleteAllInput(e.target.value)} placeholder="DELETE ALL" autoFocus />
            </label>
            <div className="channel-modal-actions">
              <button type="button" className="channel-secondary-btn" onClick={() => { setDeleteAllOpen(false); setDeleteAllInput(""); }} disabled={working}>Cancel</button>
              <button type="button" className="channel-primary-btn channel-btn-danger" disabled={working || deleteAllInput.trim() !== "DELETE ALL"} onClick={() => void runDeleteAll()}>{working ? "Deleting…" : "Delete all contacts"}</button>
            </div>
          </div>
        </div>
      )}

      {/* Tag create/edit modal */}
      {tagForm && (
        <div className="channel-modal-scrim" role="dialog" aria-modal="true" aria-labelledby="tag-form-title">
          <div className="channel-modal channel-modal-sm">
            <h2 id="tag-form-title">{tagForm.id ? "Edit tag" : "Create tag"}</h2>
            <form onSubmit={submitTag} className="channel-form">
              <label className="channel-field"><span>Name</span>
                <input value={tagForm.name} onChange={(e) => setTagForm({ ...tagForm, name: e.target.value })} maxLength={60} placeholder="VIP" autoFocus />
              </label>
              <label className="channel-field"><span>Color</span>
                <input type="color" value={tagForm.color} onChange={(e) => setTagForm({ ...tagForm, color: e.target.value })} className="tag-color-input" />
              </label>
              {tagError && <p className="channel-form-error" role="alert">{tagError}</p>}
              <div className="channel-modal-actions">
                <button type="button" className="channel-secondary-btn" onClick={() => setTagForm(null)} disabled={tagSaving}>Cancel</button>
                <button type="submit" className="channel-primary-btn" disabled={tagSaving}>{tagSaving ? "Saving…" : tagForm.id ? "Save" : "Create tag"}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Field create/edit modal */}
      {fieldForm && (
        <div className="channel-modal-scrim" role="dialog" aria-modal="true" aria-labelledby="field-form-title">
          <div className="channel-modal channel-modal-sm">
            <h2 id="field-form-title">{fieldForm.id ? "Edit field" : "Create field"}</h2>
            <form onSubmit={submitField} className="channel-form">
              <label className="channel-field"><span>Label</span>
                <input value={fieldForm.label} onChange={(e) => setFieldForm({ ...fieldForm, label: e.target.value })} maxLength={60} placeholder="Company Name" autoFocus />
              </label>
              {!fieldForm.id && (
                <label className="channel-field"><span>Field Type</span>
                  <select value={fieldForm.field_type} onChange={(e) => setFieldForm({ ...fieldForm, field_type: e.target.value })} className="channel-input">
                    <option value="text">Text</option>
                    <option value="number">Number</option>
                    <option value="date">Date</option>
                    <option value="boolean">Yes/No (Boolean)</option>
                    <option value="select">Dropdown (Select)</option>
                    <option value="multiselect">Multiple Choice</option>
                  </select>
                </label>
              )}
              {["select", "multiselect"].includes(fieldForm.field_type) && (
                <label className="channel-field"><span>Options (Comma separated)</span>
                  <input value={fieldForm.options} onChange={(e) => setFieldForm({ ...fieldForm, options: e.target.value })} placeholder="Option 1, Option 2" />
                </label>
              )}
              {fieldError && <p className="channel-form-error" role="alert">{fieldError}</p>}
              <div className="channel-modal-actions">
                <button type="button" className="channel-secondary-btn" onClick={() => setFieldForm(null)} disabled={fieldSaving}>Cancel</button>
                <button type="submit" className="channel-primary-btn" disabled={fieldSaving}>{fieldSaving ? "Saving…" : fieldForm.id ? "Save" : "Create field"}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Import Result modal */}
      {importResult && (
        <div className="channel-modal-scrim" role="dialog" aria-modal="true" aria-labelledby="import-result-title">
          <div className="channel-modal channel-modal-sm">
            <h2 id="import-result-title">Import Complete</h2>
            <div className="channel-form">
              <p className="mt-2 text-slate-700">Successfully imported <strong>{importResult.accepted}</strong> contacts.</p>
              {importResult.skipped > 0 && (
                <p className="mt-2 text-slate-500">Skipped {importResult.skipped} rows.</p>
              )}
              {importResult.errors.length > 0 && (
                <div className="mt-4">
                  <strong className="text-red-600 block mb-2">Errors:</strong>
                  <ul className="text-sm text-red-500 list-disc pl-4 max-h-32 overflow-y-auto">
                    {importResult.errors.map((e, i) => <li key={i}>{e}</li>)}
                  </ul>
                </div>
              )}
            </div>
            <div className="channel-modal-actions">
              <button type="button" className="channel-primary-btn" onClick={() => setImportResult(null)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
