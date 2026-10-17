import { CampaignForm } from '@/components/campaigns/campaign-form';

export const metadata = {
  title: 'New Campaign - Omniflow',
};

export default function NewCampaignPage() {
  return (
    <div className="flex flex-col h-full bg-slate-50 overflow-y-auto">
      <div className="p-6 max-w-3xl mx-auto w-full">
        <h1 className="text-2xl font-bold text-slate-900 mb-6">Create Campaign</h1>
        <CampaignForm />
      </div>
    </div>
  );
}
