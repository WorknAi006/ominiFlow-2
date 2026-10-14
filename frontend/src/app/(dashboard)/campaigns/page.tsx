import { CampaignList } from '@/components/campaigns/campaign-list';

export const metadata = {
  title: 'Campaigns - Omniflow',
};

export default function CampaignsPage() {
  return (
    <div className="flex flex-col h-full bg-slate-50">
      <div className="flex-1 p-6 max-w-7xl mx-auto w-full">
        <CampaignList />
      </div>
    </div>
  );
}
