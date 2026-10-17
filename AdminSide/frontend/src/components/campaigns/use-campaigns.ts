'use client';

import { useState, useEffect } from 'react';
import { Campaign, campaignsApi } from '@/lib/campaigns/browser';

export function useCampaigns() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCampaigns = async () => {
    try {
      setLoading(true);
      const res = await campaignsApi.list();
      setCampaigns(res.items);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCampaigns();
  }, []);

  return { campaigns, loading, error, loadCampaigns };
}
