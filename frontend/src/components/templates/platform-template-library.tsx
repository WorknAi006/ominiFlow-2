"use client";

import { useCallback, useEffect, useState } from "react";

import { listChannels, type ChannelConnection } from "@/lib/channels/browser";
import {
  createPlatformTemplate,
  getPlatformTemplateAdminStatus,
  listPlatformTemplates,
  setPlatformTemplateActive,
  submitPlatformTemplate,
  TemplateApiError,
  type PlatformTemplate,
} from "@/lib/templates/browser";

function variableCount(body: string) {
  const matches = [...body.matchAll(/\{\{\s*(\d+)\s*\}\}/g)];
  return new Set(matches.map((match) => match[1])).size;
}

export function PlatformTemplateLibrary() {
  const [templates, setTemplates] = useState<PlatformTemplate[]>([]);
  const [channels, setChannels] = useState<ChannelConnection[]>([]);
  const [isAdmin, setIsAdmin] = useState(false);
  const [channelId, setChannelId] = useState("");
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [results, setResults] = useState<Record<string, string>>({});
  const [bodies, setBodies] = useState<Record<string, string>>({});
  const [examples, setExamples] = useState<Record<string, string[]>>({});
  const [form, setForm] = useState({
    name: "",
    label: "",
    language: "en_US",
    category: "marketing",
    body_text: "",
  });

  const fetchLibrary = useCallback(async () => {
    const [library, admin, channelList] = await Promise.all([
        listPlatformTemplates(),
        getPlatformTemplateAdminStatus(),
        listChannels({ page: 1, page_size: 100, channel_type: "whatsapp" }),
    ]);
    return {
      templates: library.items,
      isAdmin: admin.is_platform_super_admin,
      channels: channelList.items.filter((item) => item.status === "connected"),
    };
  }, []);

  const applyLibrary = useCallback((data: Awaited<ReturnType<typeof fetchLibrary>>) => {
    setTemplates(data.templates);
    setIsAdmin(data.isAdmin);
    setChannels(data.channels);
    setChannelId((current) => data.channels.some((item) => item.id === current) ? current : data.channels[0]?.id ?? "");
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      applyLibrary(await fetchLibrary());
    } catch (cause) {
      setError(cause instanceof TemplateApiError ? cause.message : "Could not load the common template library.");
    } finally {
      setLoading(false);
    }
  }, [applyLibrary, fetchLibrary]);

  useEffect(() => {
    let active = true;
    void fetchLibrary()
      .then((data) => { if (active) applyLibrary(data); })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof TemplateApiError ? cause.message : "Could not load the common template library.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [applyLibrary, fetchLibrary]);

  async function createTemplate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
    setError("");
    setNotice("");
    try {
      await createPlatformTemplate({
        ...form,
        name: form.name.trim(),
        label: form.label.trim(),
        body_text: form.body_text.trim(),
      });
      setForm({ ...form, name: "", label: "", body_text: "" });
      setNotice("Common template added to the library.");
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not create this common template.");
    } finally {
      setWorking(false);
    }
  }

  async function toggleTemplate(template: PlatformTemplate) {
    setWorking(true);
    setError("");
    try {
      await setPlatformTemplateActive(template.id, !template.is_active);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not update this library template.");
    } finally {
      setWorking(false);
    }
  }

  async function submitTemplate(template: PlatformTemplate) {
    const body = bodies[template.id] ?? template.body_text;
    const count = variableCount(body);
    const values = examples[template.id] ?? [];
    setWorking(true);
    setError("");
    setNotice("");
    try {
      const result = await submitPlatformTemplate(template.id, {
        channel_connection_id: channelId,
        body_text: body,
        examples: values.slice(0, count),
      });
      setResults((current) => ({ ...current, [template.id]: result.template.status }));
      setNotice(result.message);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not submit this template to Meta.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <section className="mb-8 rounded-2xl border border-indigo-200 bg-white p-5 shadow-sm" aria-labelledby="common-template-title">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="common-template-title" className="text-lg font-bold text-slate-900">Common WhatsApp template library</h2>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Choose a shared draft and submit a separate copy to this workspace&apos;s WhatsApp Business Account. Meta reviews each business account independently.
          </p>
        </div>
        {channels.length > 0 && (
          <label className="text-sm text-slate-600">
            WhatsApp channel
            <select className="ml-2 rounded-md border border-slate-300 px-2 py-1.5" value={channelId} onChange={(event) => setChannelId(event.target.value)}>
              {channels.map((channel) => <option key={channel.id} value={channel.id}>{channel.name}</option>)}
            </select>
          </label>
        )}
      </div>

      {error && <p className="mt-3 rounded-md bg-rose-50 p-3 text-sm text-rose-700" role="alert">{error}</p>}
      {notice && <p className="mt-3 rounded-md bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{notice}</p>}

      {isAdmin && (
        <details className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
          <summary className="cursor-pointer text-sm font-semibold text-indigo-700">Platform super-admin: add a common template</summary>
          <form className="mt-4 grid gap-3 md:grid-cols-2" onSubmit={(event) => void createTemplate(event)}>
            <label className="text-sm text-slate-700">Meta template name
              <input className="mt-1 w-full rounded-md border border-slate-300 p-2" required pattern="[a-z0-9_]{1,512}" maxLength={512} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="order_update" />
            </label>
            <label className="text-sm text-slate-700">Dashboard label
              <input className="mt-1 w-full rounded-md border border-slate-300 p-2" required minLength={2} maxLength={150} value={form.label} onChange={(event) => setForm({ ...form, label: event.target.value })} placeholder="Order update" />
            </label>
            <label className="text-sm text-slate-700">Language code
              <input className="mt-1 w-full rounded-md border border-slate-300 p-2" required pattern="[A-Za-z]{2,3}(_[A-Za-z0-9]{2,8})?" maxLength={20} value={form.language} onChange={(event) => setForm({ ...form, language: event.target.value })} />
            </label>
            <label className="text-sm text-slate-700">Category
              <select className="mt-1 w-full rounded-md border border-slate-300 p-2" value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })}>
                <option value="marketing">Marketing</option>
                <option value="utility">Utility</option>
              </select>
            </label>
            <label className="text-sm text-slate-700 md:col-span-2">Body (numbered placeholders: {"{{1}}"}, {"{{2}}"})
              <textarea className="mt-1 w-full rounded-md border border-slate-300 p-2" rows={3} required maxLength={1024} value={form.body_text} onChange={(event) => setForm({ ...form, body_text: event.target.value })} />
            </label>
            <button className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 md:col-span-2 md:justify-self-end" type="submit" disabled={working}>
              {working ? "Saving…" : "Add to shared library"}
            </button>
          </form>
        </details>
      )}

      {loading ? <p className="py-6 text-sm text-slate-500">Loading common templates…</p> : templates.length === 0 ? (
        <p className="py-6 text-sm text-slate-500">{isAdmin ? "Add the first common template above." : "No common templates are available yet."}</p>
      ) : (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          {templates.map((template) => {
            const body = bodies[template.id] ?? template.body_text;
            const count = variableCount(body);
            const values = examples[template.id] ?? [];
            return (
              <article key={template.id} className={`rounded-xl border p-4 ${template.is_active ? "border-slate-200" : "border-amber-200 bg-amber-50"}`}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="font-semibold text-slate-900">{template.label}</h3>
                    <p className="text-xs text-slate-500">{template.name} · {template.language} · {template.category}</p>
                  </div>
                  {isAdmin && <button type="button" className="text-xs font-medium text-indigo-700" disabled={working} onClick={() => void toggleTemplate(template)}>{template.is_active ? "Deactivate" : "Activate"}</button>}
                </div>
                <label className="mt-3 block text-xs font-medium text-slate-600">Message body (keep the numbered placeholders)
                  <textarea className="mt-1 w-full rounded-md border border-slate-300 p-2 text-sm" rows={3} maxLength={1024} disabled={!template.is_active} value={body} onChange={(event) => setBodies((current) => ({ ...current, [template.id]: event.target.value }))} />
                </label>
                {Array.from({ length: count }, (_, index) => (
                  <label key={index} className="mt-2 block text-xs text-slate-600">Example for {"{{"}{index + 1}{"}}"}
                    <input className="mt-1 w-full rounded-md border border-slate-300 p-2 text-sm" maxLength={1024} value={values[index] ?? ""} onChange={(event) => setExamples((current) => {
                      const next = [...(current[template.id] ?? [])];
                      next[index] = event.target.value;
                      return { ...current, [template.id]: next };
                    })} />
                  </label>
                ))}
                <div className="mt-3 flex items-center justify-between gap-2">
                  <span className="text-xs text-slate-500">{results[template.id] ? `Meta status: ${results[template.id]}` : "Requires Meta review for this WABA"}</span>
                  <button type="button" className="rounded-md bg-indigo-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50" disabled={!template.is_active || !channelId || working || values.slice(0, count).some((value) => !value?.trim())} onClick={() => void submitTemplate(template)}>
                    {working ? "Submitting…" : "Submit to my WhatsApp"}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}
      {!channels.length && !loading && <p className="mt-3 text-sm text-amber-700">Connect a WhatsApp channel first. Only connected channels in this workspace are listed.</p>}
    </section>
  );
}
