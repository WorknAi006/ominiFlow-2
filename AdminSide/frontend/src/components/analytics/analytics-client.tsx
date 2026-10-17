"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

// Icons
const ZapIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>);
const SettingsIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" /><circle cx="12" cy="12" r="3" /></svg>);
const MegaphoneIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" /><path d="M15.54 8.46a5 5 0 0 1 0 7.07" /><path d="M19.07 4.93a10 10 0 0 1 0 14.14" /></svg>);
const PlusIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>);
const UsersIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>);
const MessageSquareIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>);
const LinkIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" /></svg>);
const ClockIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>);
const CheckCircleIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" /></svg>);
const BotIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><rect x="3" y="11" width="18" height="10" rx="2" /><circle cx="12" cy="5" r="2" /><path d="M12 7v4" /><line x1="8" y1="16" x2="8" y2="16" /><line x1="16" y1="16" x2="16" y2="16" /></svg>);
const LoaderIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="animate-spin" {...props}><line x1="12" y1="2" x2="12" y2="6" /><line x1="12" y1="18" x2="12" y2="22" /><line x1="4.93" y1="4.93" x2="7.76" y2="7.76" /><line x1="16.24" y1="16.24" x2="19.07" y2="19.07" /><line x1="2" y1="12" x2="6" y2="12" /><line x1="18" y1="12" x2="22" y2="12" /><line x1="4.93" y1="19.07" x2="7.76" y2="16.24" /><line x1="16.24" y1="7.76" x2="19.07" y2="4.93" /></svg>);

// Channel Icons
const WhatsAppIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" /></svg>);
const FacebookIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="currentColor" {...props}><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.469h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.469h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>);
const InstagramIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><rect x="2" y="2" width="20" height="20" rx="5" ry="5" /><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" /><line x1="17.5" y1="6.5" x2="17.51" y2="6.5" /></svg>);

interface AnalyticsOverview {
  total_contacts: number;
  total_chats: number;
  open_chats: number;
  pending_chats: number;
  resolved_chats: number;
  closed_chats: number;
  active_flows: number;
}

interface Channel {
  id: string;
  name: string;
  channel_type: string;
  status: string;
  external_account_id: string;
}

interface TimeSeries {
  date: string;
  inbound: number;
  outbound: number;
}

interface AutomationsStats {
  total_executions: number;
  completed: number;
  failed: number;
  success_rate: number;
}

export function AnalyticsClient() {
  const [dateRange, setDateRange] = useState({
    start: new Date(new Date().setDate(new Date().getDate() - 30)).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0]
  });

  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [timeSeries, setTimeSeries] = useState<TimeSeries[]>([]);
  const [automations, setAutomations] = useState<AutomationsStats | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const queryParams = `?start_date=${dateRange.start}T00:00:00Z&end_date=${dateRange.end}T23:59:59Z`;
        
        const [overviewRes, channelsRes, tsRes, autoRes] = await Promise.all([
          fetch(`/api/analytics/overview${queryParams}`),
          fetch(`/api/analytics/channels`),
          fetch(`/api/analytics/time-series${queryParams}`),
          fetch(`/api/analytics/automations${queryParams}`)
        ]);

        if (!overviewRes.ok || !channelsRes.ok || !tsRes.ok || !autoRes.ok) {
          throw new Error("Failed to load analytics data.");
        }

        const [ovData, chData, tsData, auData] = await Promise.all([
          overviewRes.json(),
          channelsRes.json(),
          tsRes.json(),
          autoRes.json()
        ]);

        setOverview(ovData);
        setChannels(chData);
        setTimeSeries(tsData);
        setAutomations(auData);
      } catch (e: any) {
        setError(e.message || "An error occurred.");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [dateRange]);

  const metrics = overview ? [
    { label: "Total Contacts", value: overview.total_contacts, icon: UsersIcon, iconColor: "text-emerald-500", iconBg: "bg-emerald-50" },
    { label: "Total Chats", value: overview.total_chats, icon: MessageSquareIcon, iconColor: "text-purple-500", iconBg: "bg-purple-50" },
    { label: "Active Flows", value: overview.active_flows, icon: LinkIcon, iconColor: "text-amber-500", iconBg: "bg-amber-50" },
    { label: "Total Executions", value: automations?.total_executions || 0, icon: BotIcon, iconColor: "text-blue-500", iconBg: "bg-blue-50" },
  ] : [];

  const handleDateChange = (type: 'start' | 'end', val: string) => {
    setDateRange(prev => ({ ...prev, [type]: val }));
  };

  const getChannelIcon = (type: string) => {
    if (type === "whatsapp") return <WhatsAppIcon className="w-6 h-6" />;
    if (type === "facebook") return <FacebookIcon className="w-6 h-6" />;
    if (type === "instagram") return <InstagramIcon className="w-6 h-6" />;
    return <MessageSquareIcon className="w-6 h-6 fill-current" />;
  };

  const getChannelColors = (type: string) => {
    if (type === "whatsapp") return { bg: "bg-[#e8f5e9]", text: "text-[#00b050]" };
    if (type === "facebook") return { bg: "bg-[#e3f2fd]", text: "text-blue-600" };
    if (type === "instagram") return { bg: "bg-[#fce4ec]", text: "text-pink-500" };
    return { bg: "bg-[#e0f2f1]", text: "text-teal-600" };
  };

  // Prepare chart data
  const maxMessages = timeSeries.length > 0 ? Math.max(...timeSeries.map(t => Math.max(t.inbound, t.outbound))) : 1;

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-[#f8f9fa] text-slate-500 p-8">
        <div className="bg-red-50 text-red-500 p-6 rounded-2xl max-w-lg text-center shadow-sm border border-red-100">
          <SettingsIcon className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <h2 className="text-xl font-bold mb-2">Error loading analytics</h2>
          <p>{error}</p>
          <button 
            onClick={() => setDateRange({...dateRange})}
            className="mt-6 px-4 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg font-semibold transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[#f8f9fa] min-h-screen text-slate-800 font-sans">
      <div className="p-8 mx-auto max-w-7xl">
        
        {/* Header */}
        <div className="flex justify-between items-start mb-8 border-b border-slate-200 pb-6">
          <div>
            <h1 className="text-[26px] font-bold text-slate-900 leading-tight">Analytics</h1>
            <p className="text-[15px] text-slate-500 mt-0.5">Dashboard overview</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 bg-white px-4 py-2 rounded-lg border border-slate-200 shadow-sm">
              <span className="text-sm font-semibold text-slate-500">From</span>
              <input 
                type="date" 
                value={dateRange.start}
                onChange={(e) => handleDateChange('start', e.target.value)}
                className="bg-transparent border-none outline-none text-sm font-bold text-slate-700 cursor-pointer"
              />
              <span className="text-sm font-semibold text-slate-500 mx-2">To</span>
              <input 
                type="date" 
                value={dateRange.end}
                onChange={(e) => handleDateChange('end', e.target.value)}
                className="bg-transparent border-none outline-none text-sm font-bold text-slate-700 cursor-pointer"
              />
            </div>
            <button className="p-2.5 bg-white border border-slate-200 rounded-md text-slate-500 hover:bg-slate-50 shadow-sm transition-colors">
              <SettingsIcon className="w-5 h-5" />
            </button>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <LoaderIcon className="w-8 h-8 text-slate-400" />
          </div>
        ) : (
          <>
            {/* Channels Row */}
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">CONNECTED CHANNELS</h3>
            {channels.length === 0 ? (
              <div className="bg-white border border-slate-200 rounded-2xl p-10 text-center shadow-sm mb-10">
                <p className="text-slate-500 mb-4">No channels connected yet.</p>
                <Link href="/channels" className="px-4 py-2 bg-[#00b050] text-white rounded-lg font-bold text-sm">
                  Connect a Channel
                </Link>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
                {channels.map(c => {
                  const colors = getChannelColors(c.channel_type);
                  return (
                    <div key={c.id} className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm transition-all hover:shadow-md">
                      <div className="flex items-start gap-4 mb-5">
                        <div className={`w-12 h-12 ${colors.bg} ${colors.text} rounded-2xl flex items-center justify-center`}>
                          {getChannelIcon(c.channel_type)}
                        </div>
                        <div className="flex-1">
                          <div className="flex justify-between items-start">
                            <div className="text-sm font-semibold text-slate-500 mb-0.5 capitalize">{c.channel_type}</div>
                            <div className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${c.status === 'connected' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                              {c.status}
                            </div>
                          </div>
                          <div className="font-bold text-slate-900 text-lg truncate" title={c.name}>{c.name}</div>
                          {c.external_account_id && <div className="text-sm text-slate-500 truncate">{c.external_account_id}</div>}
                        </div>
                      </div>
                      <Link href={`/channels`} className="block w-full py-2 bg-white border border-slate-200 rounded-lg text-sm font-bold text-slate-700 hover:bg-slate-50 text-center transition-colors">
                        Manage
                      </Link>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Metrics Grid */}
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">OVERVIEW</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-10">
              {metrics.map((m, i) => {
                const Icon = m.icon;
                return (
                  <div key={i} className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm transition-all hover:shadow-md">
                    <div className={`w-10 h-10 ${m.iconBg} rounded-xl flex items-center justify-center mb-4`}>
                      <Icon className={`w-5 h-5 ${m.iconColor}`} />
                    </div>
                    <div className="text-3xl font-black text-slate-900 mb-1">
                      {m.value}
                    </div>
                    <div className="text-sm font-semibold text-slate-500">{m.label}</div>
                  </div>
                );
              })}
            </div>

            {/* Chat & Message Statistics Section */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-10">
              
              <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm lg:col-span-1 flex flex-col">
                <h4 className="font-bold text-slate-900 mb-1">Conversation status</h4>
                <p className="text-xs text-slate-500 mb-6">Open · Pending · Resolved breakdown</p>
                
                <div className="flex-1 flex flex-col justify-center gap-8">
                  <div className="relative w-32 h-32 mx-auto">
                    {/* SVG Doughnut Chart */}
                    <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
                      <path
                        className="text-slate-100"
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      {overview && overview.total_chats > 0 && (
                        <>
                          {/* Resolved (Blue) */}
                          <path
                            className="text-blue-500"
                            strokeDasharray={`${(overview.resolved_chats / overview.total_chats) * 100}, 100`}
                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="4"
                          />
                          {/* Open (Green) */}
                          <path
                            className="text-[#00b050]"
                            strokeDasharray={`${(overview.open_chats / overview.total_chats) * 100}, 100`}
                            strokeDashoffset={`-${(overview.resolved_chats / overview.total_chats) * 100}`}
                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="4"
                          />
                          {/* Pending (Amber) */}
                          <path
                            className="text-amber-400"
                            strokeDasharray={`${(overview.pending_chats / overview.total_chats) * 100}, 100`}
                            strokeDashoffset={`-${((overview.resolved_chats + overview.open_chats) / overview.total_chats) * 100}`}
                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="4"
                          />
                        </>
                      )}
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                      <div className="text-2xl font-black text-slate-900 leading-none">{overview?.total_chats || 0}</div>
                      <div className="text-[10px] font-semibold text-slate-500 uppercase mt-1">Total chats</div>
                    </div>
                  </div>
                  
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2 font-semibold text-slate-700">
                        <div className="w-2.5 h-2.5 rounded-full bg-[#00b050]" /> Open
                      </div>
                      <div className="flex gap-2 w-16 justify-end">
                        <span className="font-bold">{overview?.open_chats || 0}</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2 font-semibold text-slate-700">
                        <div className="w-2.5 h-2.5 rounded-full bg-amber-400" /> Pending
                      </div>
                      <div className="flex gap-2 w-16 justify-end">
                        <span className="font-bold">{overview?.pending_chats || 0}</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2 font-semibold text-slate-700">
                        <div className="w-2.5 h-2.5 rounded-full bg-blue-500" /> Resolved
                      </div>
                      <div className="flex gap-2 w-16 justify-end">
                        <span className="font-bold">{overview?.resolved_chats || 0}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Time Series Chart */}
              <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm lg:col-span-2 flex flex-col min-h-[350px]">
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <h4 className="font-bold text-slate-900 mb-1">Message Volume</h4>
                    <p className="text-xs text-slate-500">Inbound vs Outbound messages</p>
                  </div>
                  <div className="flex gap-4 text-xs font-semibold">
                    <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded bg-[#00b050]"></div>Inbound</div>
                    <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded bg-blue-500"></div>Outbound</div>
                  </div>
                </div>

                <div className="flex-1 relative flex items-end justify-between pt-6">
                  {timeSeries.length === 0 ? (
                    <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-sm font-semibold">
                      No message data for this period
                    </div>
                  ) : (
                    timeSeries.map((day, i) => (
                      <div key={i} className="flex flex-col items-center flex-1 group">
                        <div className="flex gap-1 items-end h-40 w-full justify-center opacity-80 group-hover:opacity-100 transition-opacity">
                          <div 
                            className="w-full max-w-[12px] bg-[#00b050] rounded-t-sm relative group"
                            style={{ height: `${Math.max((day.inbound / maxMessages) * 100, 2)}%` }}
                          >
                            <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-slate-800 text-white text-xs px-2 py-1 rounded hidden group-hover:block z-10 whitespace-nowrap">
                              In: {day.inbound}
                            </div>
                          </div>
                          <div 
                            className="w-full max-w-[12px] bg-blue-500 rounded-t-sm relative group"
                            style={{ height: `${Math.max((day.outbound / maxMessages) * 100, 2)}%` }}
                          >
                            <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-slate-800 text-white text-xs px-2 py-1 rounded hidden group-hover:block z-10 whitespace-nowrap">
                              Out: {day.outbound}
                            </div>
                          </div>
                        </div>
                        {/* Only show dates for first, middle, last to avoid crowding */}
                        <div className="text-[10px] text-slate-400 mt-2 font-medium truncate w-full text-center px-1">
                          {i === 0 || i === timeSeries.length - 1 || i === Math.floor(timeSeries.length / 2) 
                            ? new Date(day.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
                            : ''}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

            </div>

            {/* Automation Statistics Section */}
            {automations && (
              <>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">AUTOMATION PERFORMANCE</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-10">
                  <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
                    <div className="w-10 h-10 bg-slate-100 rounded-xl flex items-center justify-center mb-4 text-slate-500">
                      <BotIcon className="w-5 h-5" />
                    </div>
                    <div className="text-3xl font-black text-slate-900 mb-1">{automations.total_executions}</div>
                    <div className="text-sm font-semibold text-slate-500">Total Runs</div>
                  </div>
                  <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
                    <div className="w-10 h-10 bg-[#e8f5e9] rounded-xl flex items-center justify-center mb-4 text-[#00b050]">
                      <CheckCircleIcon className="w-5 h-5" />
                    </div>
                    <div className="text-3xl font-black text-slate-900 mb-1">{automations.completed}</div>
                    <div className="text-sm font-semibold text-slate-500">Completed</div>
                  </div>
                  <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
                    <div className="w-10 h-10 bg-red-50 rounded-xl flex items-center justify-center mb-4 text-red-500">
                      <SettingsIcon className="w-5 h-5" />
                    </div>
                    <div className="text-3xl font-black text-slate-900 mb-1">{automations.failed}</div>
                    <div className="text-sm font-semibold text-slate-500">Failed</div>
                  </div>
                  <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
                    <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center mb-4 text-blue-500">
                      <ZapIcon className="w-5 h-5" />
                    </div>
                    <div className="text-3xl font-black text-slate-900 mb-1">{automations.success_rate}%</div>
                    <div className="text-sm font-semibold text-slate-500">Success Rate</div>
                  </div>
                </div>
              </>
            )}

          </>
        )}
      </div>
    </div>
  );
}
