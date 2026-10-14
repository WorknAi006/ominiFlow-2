'use client';

import { useState, useEffect } from 'react';
import { campaignsApi } from '@/lib/campaigns/browser';
import { useRouter } from 'next/navigation';

export function CampaignForm() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [channelId, setChannelId] = useState('');
  const [textContent, setTextContent] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  
  const [channels, setChannels] = useState<any[]>([]);
  const [tags, setTags] = useState<any[]>([]);
  const [audienceCount, setAudienceCount] = useState<number | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Load channels and tags
    const loadDependencies = async () => {
      try {
        const [channelsRes, tagsRes] = await Promise.all([
          fetch('/api/channels').then(res => res.json()),
          fetch('/api/tags').then(res => res.json())
        ]);
        setChannels(channelsRes.items || []);
        setTags(tagsRes.items || []);
      } catch (e: any) {
        setError('Failed to load dependencies: ' + e.message);
      }
    };
    loadDependencies();
  }, []);

  const handlePreview = async () => {
    if (selectedTags.length === 0) {
      setAudienceCount(0);
      return;
    }
    
    setPreviewing(true);
    setError(null);
    try {
      const res = await campaignsApi.previewAudience({
        audience_config: { tags: selectedTags }
      });
      setAudienceCount(res.total_contacts);
    } catch (e: any) {
      setError(e.message);
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

    setSubmitting(true);
    setError(null);
    try {
      await campaignsApi.create({
        name,
        channel_connection_id: channelId,
        text_content: textContent,
        audience_config: { tags: selectedTags }
      });
      router.push('/campaigns');
    } catch (e: any) {
      setError(e.message);
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
          <label className="block text-sm font-medium text-slate-700 mb-1">Campaign Name</label>
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
            onChange={(e) => setChannelId(e.target.value)}
            className="w-full text-sm border-slate-300 rounded-lg shadow-sm"
          >
            <option value="">Select a channel</option>
            {channels.map(c => (
              <option key={c.id} value={c.id}>{c.name} ({c.channel_type})</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Message Content (Text Only)</label>
          <textarea
            rows={4}
            value={textContent}
            onChange={(e) => setTextContent(e.target.value)}
            className="w-full text-sm border-slate-300 rounded-lg shadow-sm"
            placeholder="Write your message here..."
          />
          <p className="text-xs text-slate-500 mt-1">Note: Template selection is deferred for Phase 1. Text is used for preview.</p>
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
