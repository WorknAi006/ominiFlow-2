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
        setChannels(channelsRes.items || []);
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
    if (selectedTags.length === 0) {
      setAudienceCount(0);
      return;
    }
    setPreviewing(true);
    setError(null);
    try {
      const res = await campaignsApi.previewAudience({ audience_config: { tags: selectedTags } });
      setAudienceCount(res.total_contacts);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setPreviewing(false);
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

    setSubmitting(true);
    setError(null);
    try {
      const payload: Record<string, unknown> = {
        name,
        channel_connection_id: channelId,
        audience_config: { tags: selectedTags },
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
          <h3 className="text-sm font-medium text-slate-900 mb-4">Audience Selection</h3>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Target Tags</label>
              <select
                multiple
                value={selectedTags}
                onChange={(e) => {
                  const values = Array.from(e.target.selectedOptions, option => option.value);
                  setSelectedTags(values);
                }}
                className="w-full text-sm border-slate-300 rounded-lg shadow-sm h-32"
              >
                {tags.map(t => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
              <p className="text-xs text-slate-500 mt-1">Hold Ctrl/Cmd to select multiple tags. Contacts with ANY of these tags will be targeted.</p>
            </div>

            <div className="flex items-center space-x-4 bg-slate-50 p-4 rounded-lg border border-slate-200">
              <button
                type="button"
                onClick={handlePreview}
                disabled={previewing}
                className="px-3 py-1.5 bg-white border border-slate-300 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                {previewing ? 'Calculating...' : 'Preview Audience Size'}
              </button>

              {audienceCount !== null && (
                <span className="text-sm font-medium text-indigo-600">
                  {audienceCount} recipients found
                </span>
              )}
            </div>
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
