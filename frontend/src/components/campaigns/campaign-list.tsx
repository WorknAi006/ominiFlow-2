'use client';

import { useCampaigns } from './use-campaigns';
import { campaignsApi } from '@/lib/campaigns/browser';
import Link from 'next/link';

export function CampaignList() {
  const { campaigns, loading, error, loadCampaigns } = useCampaigns();

  const handleStart = async (id: string) => {
    try {
      await campaignsApi.start(id);
      loadCampaigns();
    } catch (e: any) {
      alert(e.message);
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg text-sm">
        {error}
      </div>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
      <div className="px-6 py-5 border-b border-slate-200 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-medium text-slate-900">Campaigns</h2>
          <p className="mt-1 text-sm text-slate-500">Manage your broadcast campaigns.</p>
        </div>
        <Link
          href="/campaigns/new"
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-lg shadow-sm text-white bg-indigo-600 hover:bg-indigo-700"
        >
          Create Campaign
        </Link>
      </div>

      {campaigns.length === 0 ? (
        <div className="px-6 py-12 text-center text-slate-500 text-sm">
          No campaigns found. Create your first campaign.
        </div>
      ) : (
        <ul className="divide-y divide-slate-200">
          {campaigns.map((campaign) => (
            <li key={campaign.id} className="hover:bg-slate-50">
              <div className="px-6 py-4 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-900">{campaign.name}</p>
                  <p className="text-xs text-slate-500 mt-1">
                    Recipients: {campaign.total_recipients} &bull; Delivered: {campaign.delivered_count}
                  </p>
                </div>
                <div className="flex items-center space-x-4">
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium capitalize 
                    ${campaign.status === 'draft' ? 'bg-slate-100 text-slate-800' : 
                      campaign.status === 'sending' ? 'bg-blue-100 text-blue-800' :
                      campaign.status === 'completed' ? 'bg-green-100 text-green-800' :
                      'bg-indigo-100 text-indigo-800'}`}
                  >
                    {campaign.status}
                  </span>
                  {campaign.status === 'draft' && (
                    <button
                      onClick={() => handleStart(campaign.id)}
                      className="text-indigo-600 hover:text-indigo-900 text-sm font-medium"
                    >
                      Start
                    </button>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
