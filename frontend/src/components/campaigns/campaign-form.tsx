'use client';

import { useState, useEffect, useMemo } from 'react';
import { campaignsApi } from '@/lib/campaigns/browser';
import { listTemplates } from '@/lib/templates/browser';
import type { MessageTemplate } from '@/lib/api/templates';
import { useRouter } from 'next/navigation';
import { uploadTemplateMedia } from '@/lib/templates/browser';

// Distinct {{1}}, {{2}} … body placeholders a template declares, in order.
function bodyVariables(template: MessageTemplate | undefined): string[] {
  if (!template) return [];
  const body = template.components.find((c) => String((c as { type?: string }).type).toLowerCase() === 'body');
  const text = body ? String((body as { text?: string }).text ?? '') : '';
  const found = new Set<string>();
  for (const m of text.matchAll(/\{\{\s*([a-z0-9_]+)\s*\}\}/gi)) found.add(m[1]);
  return Array.from(found);
}

function headerDetails(template: MessageTemplate | undefined) {
  if (!template) return { format: '', text: '', variables: [] as string[] };
  const header = template.components.find((c) => String((c as { type?: string }).type).toLowerCase() === 'header');
  const text = header && typeof (header as { text?: unknown }).text === 'string'
    ? String((header as { text: string }).text)
    : '';
  return {
    format: header ? String((header as { format?: unknown }).format ?? '').toUpperCase() : '',
    text,
    variables: [...new Set(text.match(/{{\s*[a-z_][a-z0-9_]*\s*}}|{{\s*\d+\s*}}/gi) ?? [])],
  };
}

export function CampaignForm() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [channelId, setChannelId] = useState('');
  const [msgType, setMsgType] = useState<'text' | 'template'>('text');
  const [textContent, setTextContent] = useState('');
  const [templateId, setTemplateId] = useState('');
  const [templateValues, setTemplateValues] = useState<Record<string, string>>({});
  const [headerValues, setHeaderValues] = useState<Record<string, string>>({});
  const [headerMediaFile, setHeaderMediaFile] = useState<File | null>(null);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [audienceType, setAudienceType] = useState<'all' | 'tags'>('all');
  const [newTagName, setNewTagName] = useState('');
  const [creatingTag, setCreatingTag] = useState(false);
  const [tagCreateOpen, setTagCreateOpen] = useState(false);

  const [channels, setChannels] = useState<{ id: string; name: string; channel_type: string }[]>([]);
  const [tags, setTags] = useState<{ id: string; name: string }[]>([]);
  const [templates, setTemplates] = useState<MessageTemplate[]>([]);
  const [audienceCount, setAudienceCount] = useState<number | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadDependencies = async () => {
      try {
        const [channelsRes, tagsRes] = await Promise.all([
          fetch('/api/channels').then(res => res.json()),
          fetch('/api/tags').then(res => res.json())
        ]);
        const ch = channelsRes.items || [];
        setChannels(ch);
        if (ch.length > 0) {
          setChannelId((prev) => prev || ch[0].id);
        }
        setTags(tagsRes.items || []);
      } catch (e) {
        setError('Failed to load dependencies: ' + (e instanceof Error ? e.message : String(e)));
      }
      try {
        const t = await listTemplates({ page_size: 100 });
        setTemplates(t.items);
      } catch { setTemplates([]); }
    };
    loadDependencies();
  }, []);

  const selectedTemplate = useMemo(() => templates.find(t => t.id === templateId && t.channel_connection_id === channelId), [templates, templateId, channelId]);
  const variables = useMemo(() => bodyVariables(selectedTemplate), [selectedTemplate]);
  const header = useMemo(() => headerDetails(selectedTemplate), [selectedTemplate]);

  const handlePreview = async () => {
    if (audienceType === 'tags' && selectedTags.length === 0) {
      setAudienceCount(0);
      return;
    }
    setPreviewing(true);
    setError(null);
    try {
      const config = audienceType === 'all'
        ? { all_contacts: true, tags: [] }
        : { all_contacts: false, tags: selectedTags };
      const res = await campaignsApi.previewAudience({ audience_config: config });
      setAudienceCount(res.total_contacts);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setPreviewing(false);
    }
  };

  // Automatically recalculate audience preview when audienceType or selectedTags change
  useEffect(() => {
    const timer = setTimeout(() => {
      void handlePreview();
    }, 250);
    return () => clearTimeout(timer);
  }, [audienceType, selectedTags]);

  const handleCreateTag = async () => {
    if (!newTagName.trim()) return;
    setCreatingTag(true);
    try {
      const res = await fetch('/api/tags', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newTagName.trim() }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => null);
        throw new Error(d?.error || 'Failed to create tag');
      }
      const newTag = await res.json();
      setTags((prev) => [...prev, newTag]);
      setSelectedTags((prev) => [...prev, newTag.id]);
      setNewTagName('');
      setTagCreateOpen(false);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setCreatingTag(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !channelId) {
      setError('Name and Channel are required.');
      return;
    }
    if (msgType === 'template' && !templateId) {
      setError('Select a template.');
      return;
    }
    if (msgType === 'template' && !selectedTemplate) {
      setError('Select an approved template for the selected WhatsApp channel.');
      return;
    }
    if (msgType === 'template' && ['IMAGE', 'VIDEO', 'DOCUMENT'].includes(header.format) && !headerMediaFile) {
      setError(`Choose a ${header.format.toLowerCase()} header file.`);
      return;
    }
    if (msgType === 'text' && !textContent.trim()) {
      setError('Enter the message text.');
      return;
    }
    if (audienceType === 'tags' && selectedTags.length === 0) {
      setError('Please select at least one tag for target audience, or choose "All Contacts".');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const audienceConfig = audienceType === 'all'
        ? { all_contacts: true, tags: [] }
        : { all_contacts: false, tags: selectedTags };

      const payload: Record<string, unknown> = {
        name,
        channel_connection_id: channelId,
        audience_config: audienceConfig,
      };
      if (msgType === 'template') {
        payload.message_template_id = templateId;
        const components: Record<string, unknown>[] = [];
        const named = selectedTemplate?.parameter_format?.toUpperCase() === 'NAMED';
        if (header.format === 'TEXT' && header.variables.length) {
          components.push({
            type: 'header',
            parameters: header.variables.map((v) => ({
              type: 'text',
              text: headerValues[v] || '',
              ...(named && /^[{\s]*[a-z_]/i.test(v) ? { parameter_name: v.replace(/[{}\s]/g, '') } : {}),
            })),
          });
        } else if (['IMAGE', 'VIDEO', 'DOCUMENT'].includes(header.format)) {
          if (!headerMediaFile) throw new Error(`Choose a ${header.format.toLowerCase()} header file.`);
          const media = await uploadTemplateMedia(
            channelId,
            header.format.toLowerCase() as 'image' | 'video' | 'document',
            headerMediaFile,
          );
          components.push({
            type: 'header',
            parameters: [{
              type: header.format.toLowerCase(),
              id: media.id,
              ...(header.format === 'DOCUMENT' ? { filename: media.filename } : {}),
            }],
          });
        }
        if (variables.length) {
          components.push({
            type: 'body',
            parameters: variables.map((v) => ({
              type: 'text',
              text: templateValues[v] || '',
              ...(named && /^[{\s]*[a-z_]/i.test(v) ? { parameter_name: v.replace(/[{}\s]/g, '') } : {}),
            })),
          });
        }
        payload.template_params = components;
      } else {
        payload.text_content = textContent;
      }
      await campaignsApi.create(payload);
      router.push('/campaigns');
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
      <div className="p-6 space-y-6">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Broadcast Name</label>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full text-sm border-slate-300 rounded-lg shadow-sm"
            placeholder="e.g., Summer Sale Broadcast"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Channel</label>
          <select
            required
            value={channelId}
            onChange={(e) => {
              setChannelId(e.target.value);
              setTemplateId('');
              setTemplateValues({});
              setHeaderValues({});
              setHeaderMediaFile(null);
            }}
            className="w-full text-sm border-slate-300 rounded-lg shadow-sm"
          >
            <option value="">Select a channel</option>
            {channels.map(c => (
              <option key={c.id} value={c.id}>{c.name} ({c.channel_type})</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">Message</label>
          <div className="inline-flex rounded-lg border border-slate-200 p-1 mb-3">
            {(['template', 'text'] as const).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setMsgType(t)}
                className={`px-3 py-1.5 text-sm font-medium rounded-md ${msgType === t ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-50'}`}
              >
                {t === 'template' ? 'Template' : 'Text'}
              </button>
            ))}
          </div>

          {msgType === 'template' ? (
            <div className="space-y-3">
              <select
                value={templateId}
                onChange={(e) => { setTemplateId(e.target.value); setTemplateValues({}); setHeaderValues({}); setHeaderMediaFile(null); }}
                className="w-full text-sm border-slate-300 rounded-lg shadow-sm"
              >
                <option value="">Select a template</option>
                {templates.filter((t) => t.channel_connection_id === channelId).map((t) => (
                  <option key={t.id} value={t.id} disabled={!t.is_usable}>
                    {t.name} · {t.language}{t.is_usable ? '' : ` (${t.status})`}
                  </option>
                ))}
              </select>
              {templates.filter((t) => t.channel_connection_id === channelId && t.is_usable).length === 0 && (
                <p className="text-xs text-slate-500">No synced templates. Sync them on the Templates page first.</p>
              )}
              {header.variables.map((v) => (
                <div key={`header-${v}`}>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Header variable {v}</label>
                  <input
                    type="text"
                    value={headerValues[v] || ''}
                    onChange={(e) => setHeaderValues((prev) => ({ ...prev, [v]: e.target.value }))}
                    className="w-full text-sm border-slate-300 rounded-lg shadow-sm"
                    placeholder={`Value for ${v}`}
                  />
                </div>
              ))}
              {['IMAGE', 'VIDEO', 'DOCUMENT'].includes(header.format) && (
                <label className="block text-xs font-medium text-slate-600">
                  {header.format.toLowerCase()} header file
                  <input
                    type="file"
                    required
                    accept={header.format === 'IMAGE' ? 'image/jpeg,image/png,.jpg,.jpeg,.png' : header.format === 'VIDEO' ? 'video/mp4,.mp4' : 'application/pdf,.pdf'}
                    onChange={(e) => setHeaderMediaFile(e.target.files?.[0] ?? null)}
                    className="mt-1 block w-full text-sm"
                  />
                </label>
              )}
              {variables.map((v) => (
                <div key={v}>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Variable {`{{${v}}}`}</label>
                  <input
                    type="text"
                    value={templateValues[v] || ''}
                    onChange={(e) => setTemplateValues((prev) => ({ ...prev, [v]: e.target.value }))}
                    className="w-full text-sm border-slate-300 rounded-lg shadow-sm"
                    placeholder={`Value for {{${v}}}`}
                  />
                </div>
              ))}
              {selectedTemplate && (
                <div className="mt-3 p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                  <div className="text-xs font-bold text-slate-700 flex items-center justify-between">
                    <span>Template Preview</span>
                    <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200 uppercase">
                      {selectedTemplate.status}
                    </span>
                  </div>
                  <div className="bg-white p-3 rounded-lg border border-slate-200 text-xs text-slate-800 shadow-2xs space-y-1.5">
                    {header.text && (
                      <div className="font-bold text-slate-900 border-b border-slate-100 pb-1">
                        {header.text}
                      </div>
                    )}
                    {header.format && header.format !== 'TEXT' && (
                      <div className="text-[11px] font-semibold text-slate-600 bg-slate-50 p-1.5 rounded border border-slate-200 flex items-center gap-1.5">
                        <span>📎</span>
                        <span>{header.format} Header</span>
                        {headerMediaFile && <span className="text-slate-400">({headerMediaFile.name})</span>}
                      </div>
                    )}
                    <div className="whitespace-pre-wrap leading-relaxed text-slate-700">
                      {String(selectedTemplate.components?.find((c: any) => String(c.type).toLowerCase() === 'body')?.text || '')}
                    </div>
                  </div>
                </div>
              )}
              <p className="text-xs text-slate-500">Templates can be delivered outside the 24-hour window — the right choice for broadcasts.</p>
            </div>
          ) : (
            <div>
              <textarea
                rows={4}
                value={textContent}
                onChange={(e) => setTextContent(e.target.value)}
                className="w-full text-sm border-slate-300 rounded-lg shadow-sm"
                placeholder="Write your message here..."
              />
              <p className="text-xs text-slate-500 mt-1">Free text only reaches contacts inside the 24-hour customer-service window. Use a template to reach everyone.</p>
            </div>
          )}
        </div>

        <div className="border-t border-slate-200 pt-6">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Audience Selection</h3>
              <p className="text-xs text-slate-500">Choose who will receive this broadcast campaign.</p>
            </div>
            {audienceCount !== null && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                {audienceCount} {audienceCount === 1 ? 'contact' : 'contacts'} targeted
              </span>
            )}
          </div>

          {/* Audience Mode Selector */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
            <button
              type="button"
              onClick={() => setAudienceType('all')}
              className={`p-4 rounded-xl border text-left transition cursor-pointer flex flex-col justify-between ${
                audienceType === 'all'
                  ? 'border-indigo-600 bg-indigo-50/40 ring-2 ring-indigo-500/20'
                  : 'border-slate-200 bg-white hover:border-slate-300'
              }`}
            >
              <div className="flex items-center justify-between w-full mb-1">
                <span className="font-bold text-sm text-slate-900 flex items-center gap-2">
                  <span>👥</span> All Contacts
                </span>
                <input
                  type="radio"
                  name="audienceTypeRadio"
                  checked={audienceType === 'all'}
                  onChange={() => setAudienceType('all')}
                  className="w-4 h-4 text-indigo-600 focus:ring-indigo-500"
                />
              </div>
              <p className="text-xs text-slate-500 leading-relaxed">
                Send broadcast to all contacts with valid WhatsApp phone numbers (no tag needed).
              </p>
            </button>

            <button
              type="button"
              onClick={() => setAudienceType('tags')}
              className={`p-4 rounded-xl border text-left transition cursor-pointer flex flex-col justify-between ${
                audienceType === 'tags'
                  ? 'border-indigo-600 bg-indigo-50/40 ring-2 ring-indigo-500/20'
                  : 'border-slate-200 bg-white hover:border-slate-300'
              }`}
            >
              <div className="flex items-center justify-between w-full mb-1">
                <span className="font-bold text-sm text-slate-900 flex items-center gap-2">
                  <span>🏷️</span> Filter by Tags
                </span>
                <input
                  type="radio"
                  name="audienceTypeRadio"
                  checked={audienceType === 'tags'}
                  onChange={() => setAudienceType('tags')}
                  className="w-4 h-4 text-indigo-600 focus:ring-indigo-500"
                />
              </div>
              <p className="text-xs text-slate-500 leading-relaxed">
                Target only contacts who have specific tags assigned to them.
              </p>
            </button>
          </div>

          {/* Tag Selection UI when 'tags' is chosen */}
          {audienceType === 'tags' && (
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-3 animate-in fade-in">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Target Tags ({selectedTags.length} selected)
                </label>
                <div className="flex items-center gap-2">
                  {tags.length > 0 && (
                    <>
                      <button
                        type="button"
                        onClick={() => setSelectedTags(tags.map((t) => t.id))}
                        className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold"
                      >
                        Select All
                      </button>
                      <span className="text-slate-300">·</span>
                      <button
                        type="button"
                        onClick={() => setSelectedTags([])}
                        className="text-xs text-slate-500 hover:text-slate-700 font-semibold"
                      >
                        Clear
                      </button>
                      <span className="text-slate-300">·</span>
                    </>
                  )}
                  <button
                    type="button"
                    onClick={() => setTagCreateOpen(!tagCreateOpen)}
                    className="text-xs text-emerald-600 hover:text-emerald-700 font-bold flex items-center gap-1"
                  >
                    + New Tag
                  </button>
                </div>
              </div>

              {/* Inline Tag Creator */}
              {tagCreateOpen && (
                <div className="p-3 bg-white rounded-lg border border-slate-200 flex items-center gap-2">
                  <input
                    type="text"
                    value={newTagName}
                    onChange={(e) => setNewTagName(e.target.value)}
                    placeholder="Enter new tag name..."
                    className="flex-1 px-3 py-1.5 text-xs border border-slate-300 rounded-lg outline-none focus:border-indigo-500"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        void handleCreateTag();
                      }
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => void handleCreateTag()}
                    disabled={creatingTag || !newTagName.trim()}
                    className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold disabled:opacity-50"
                  >
                    {creatingTag ? 'Creating...' : 'Add Tag'}
                  </button>
                  <button
                    type="button"
                    onClick={() => { setTagCreateOpen(false); setNewTagName(''); }}
                    className="px-2 py-1.5 text-xs text-slate-500 hover:text-slate-700 font-semibold"
                  >
                    Cancel
                  </button>
                </div>
              )}

              {tags.length === 0 ? (
                <div className="text-center py-6 bg-white rounded-lg border border-dashed border-slate-300">
                  <p className="text-xs text-slate-500 mb-2">No tags found in your account.</p>
                  <button
                    type="button"
                    onClick={() => setTagCreateOpen(true)}
                    className="text-xs px-3 py-1.5 bg-indigo-50 text-indigo-700 font-bold rounded-lg border border-indigo-100 hover:bg-indigo-100"
                  >
                    + Create Your First Tag
                  </button>
                </div>
              ) : (
                <div className="flex flex-wrap gap-2 max-h-48 overflow-y-auto p-1">
                  {tags.map((t) => {
                    const isSelected = selectedTags.includes(t.id);
                    return (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => {
                          setSelectedTags((prev) =>
                            isSelected ? prev.filter((id) => id !== t.id) : [...prev, t.id]
                          );
                        }}
                        className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition cursor-pointer border ${
                          isSelected
                            ? 'bg-indigo-600 text-white border-indigo-600 shadow-2xs'
                            : 'bg-white text-slate-700 border-slate-200 hover:border-slate-300'
                        }`}
                      >
                        <span className={`w-3.5 h-3.5 rounded flex items-center justify-center border text-[10px] ${
                          isSelected ? 'bg-white text-indigo-600 border-white font-bold' : 'border-slate-300'
                        }`}>
                          {isSelected && '✓'}
                        </span>
                        <span>{t.name}</span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Audience Preview bar */}
          <div className="mt-3 flex items-center justify-between bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs">
            <span className="text-slate-600 font-medium">
              {previewing ? 'Calculating recipients...' : audienceCount !== null ? (
                <span>Found <strong>{audienceCount}</strong> reachable contact{audienceCount === 1 ? '' : 's'}</span>
              ) : 'Ready to calculate audience'}
            </span>
            <button
              type="button"
              onClick={handlePreview}
              disabled={previewing}
              className="px-3 py-1 bg-white border border-slate-300 rounded-md font-semibold text-slate-700 hover:bg-slate-50 transition"
            >
              {previewing ? 'Recalculating...' : 'Refresh Count'}
            </button>
          </div>
        </div>
      </div>

      <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex justify-end space-x-3">
        <button
          type="button"
          onClick={() => router.push('/campaigns')}
          className="px-4 py-2 border border-slate-300 shadow-sm text-sm font-medium rounded-lg text-slate-700 bg-white hover:bg-slate-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={submitting}
          className="px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-lg text-white bg-indigo-600 hover:bg-indigo-700"
        >
          {submitting ? 'Saving...' : 'Save as Draft'}
        </button>
      </div>
    </form>
  );
}
