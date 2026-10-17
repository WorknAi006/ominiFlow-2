export interface Campaign {
  id: string;
  name: string;
  channel_connection_id: string;
  message_template_id?: string;
  text_content?: string;
  audience_config?: any;
  status: 'draft' | 'scheduled' | 'sending' | 'completed' | 'failed' | 'paused';
  scheduled_at?: string;
  total_recipients: number;
  delivered_count: number;
  failed_count: number;
  created_at: string;
  updated_at: string;
}

export interface CampaignListResponse {
  items: Campaign[];
  total: number;
}

export interface AudiencePreviewRequest {
  audience_config: any;
}

export interface AudiencePreviewResponse {
  total_contacts: number;
}

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, options);
  if (!res.ok) {
    let msg = 'API error';
    try {
      const data = await res.json();
      msg = data.error || data.detail || msg;
    } catch (e) {}
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

export const campaignsApi = {
  list: async (skip: number = 0, limit: number = 100, search?: string) => {
    const params = new URLSearchParams({ skip: skip.toString(), limit: limit.toString() });
    if (search) params.append('search', search);
    return fetchApi<CampaignListResponse>(`/api/campaigns?${params.toString()}`);
  },

  get: async (id: string) => {
    return fetchApi<Campaign>(`/api/campaigns/${id}`);
  },

  create: async (data: Partial<Campaign>) => {
    return fetchApi<Campaign>('/api/campaigns', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  },

  update: async (id: string, data: Partial<Campaign>) => {
    return fetchApi<Campaign>(`/api/campaigns/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  },

  start: async (id: string) => {
    return fetchApi<Campaign>(`/api/campaigns/${id}/start`, {
      method: 'POST'
    });
  },

  previewAudience: async (data: AudiencePreviewRequest) => {
    return fetchApi<AudiencePreviewResponse>('/api/campaigns/preview-audience', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  }
};
