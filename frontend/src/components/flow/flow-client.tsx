"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { archiveAutomation, listAutomations, type Automation } from "@/lib/automations/browser";

const ZapIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>);
const SettingsIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" /><circle cx="12" cy="12" r="3" /></svg>);
const PlusIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>);
const SearchIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>);
const WorkflowIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><rect x="3" y="3" width="6" height="6" rx="1" /><rect x="15" y="15" width="6" height="6" rx="1" /><path d="M6 9v3a2 2 0 0 0 2 2h4a2 2 0 0 1 2 2v1" /></svg>);
const EditIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M12 20h9" /><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" /></svg>);
const CopyIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><rect x="9" y="9" width="13" height="13" rx="2" ry="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" /></svg>);
const TrashIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>);


export function FlowClient() {
  const [items, setItems] = useState<Automation[]>([]);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    try {
      const result = await listAutomations();
      setItems(result.items);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load flows.");
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  const filtered = useMemo(() => 
    items
      .filter(item => item.status !== "archived") // hide archived to act like deleted
      .filter(item => item.name.toLowerCase().includes(search.toLowerCase())), 
    [items, search]
  );

  async function archive(item: Automation) {
    if (!window.confirm(`Delete “${item.name}”?`)) return;
    try {
      setBusy(true);
      await archiveAutomation(item.id);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete flow.");
    } finally {
      setBusy(false);
    }
  }

  function formatDate(dateStr: string) {
    const d = new Date(dateStr);
    const day = d.getDate();
    const month = d.toLocaleString('en-US', { month: 'short' });
    const year = d.getFullYear();
    const time = d.toLocaleString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
    
    // e.g. "8 Oct 2026, 04:20 pm"
    return (
      <div className="text-sm text-slate-700">
        <div>{`${day} ${month} ${year}, ${time.split(' ')[0]}`}</div>
        <div className="lowercase">{time.split(' ')[1]}</div>
      </div>
    );
  }

  return (
    <div className="bg-[#f8f9fa] min-h-screen">
      <div className="p-8 mx-auto max-w-7xl">
        {/* Header */}
        <div className="flex justify-between items-start mb-8">
          <div>
            <h1 className="text-[28px] font-bold text-slate-800 leading-tight">Flow</h1>
            <p className="text-sm text-slate-500 font-medium mt-1">Chat flow automation</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 bg-[#e8f5e9] text-[#2e7d32] px-4 py-2 rounded-full font-semibold text-sm border border-[#c8e6c9]">
              <ZapIcon className="w-4 h-4 fill-current" />
              <span>461.12 AI Credits</span>
            </div>
            <button className="p-2.5 bg-white border border-slate-200 rounded-md text-slate-500 hover:bg-slate-50 shadow-sm">
              <SettingsIcon className="w-5 h-5" />
            </button>
            <Link href="/automations/new" className="flex items-center gap-2 bg-[#00b050] hover:bg-[#009040] text-white px-5 py-2.5 rounded-md font-semibold text-sm transition-colors shadow-sm">
              <PlusIcon className="w-4 h-4" />
              <span>Create Flow</span>
            </Link>
          </div>
        </div>

        {error && <p role="alert" className="rounded-xl bg-rose-50 p-4 text-rose-800 mb-6">{error}</p>}

        {/* Table Card */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          {/* Search Bar */}
          <div className="p-5 border-b border-slate-100 flex items-center justify-between">
            <div className="relative w-80">
              <SearchIcon className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search flows..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-white border border-slate-200 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
              />
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100 bg-[#fbfcfd]">
                  <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider w-16">#</th>
                  <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider">Flow Name</th>
                  <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider w-32">Status</th>
                  <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider w-40">
                    <div className="flex items-center gap-1">
                      CREATED <span className="text-emerald-500 font-black">↓</span>
                    </div>
                  </th>
                  <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider w-40">Last Updated</th>
                  <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider text-right pr-12 w-80">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-slate-500 text-sm">
                      {items.length === 0 ? "No flows created yet." : "No flows match your search."}
                    </td>
                  </tr>
                ) : (
                  filtered.map((item, idx) => (
                    <tr key={item.id} className="hover:bg-slate-50/50 transition-colors">
                      <td className="py-4 px-6 text-sm font-semibold text-slate-700">
                        {String(idx + 1).padStart(2, '0')}
                      </td>
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 rounded-lg bg-[#fff9c4] flex items-center justify-center flex-shrink-0 text-[#f57f17]">
                            <WorkflowIcon className="w-5 h-5" />
                          </div>
                          <div>
                            <div className="font-bold text-slate-800">{item.name}</div>
                            <div className="text-xs text-slate-500 mt-0.5">Chat Flow Configuration</div>
                          </div>
                        </div>
                      </td>
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${item.status === 'active' ? 'bg-[#00b050]' : 'bg-slate-400'}`} />
                          <span className={`text-sm font-bold ${item.status === 'active' ? 'text-[#00b050]' : 'text-slate-600 capitalize'}`}>
                            {item.status}
                          </span>
                        </div>
                      </td>
                      <td className="py-4 px-6">
                        {formatDate(item.created_at)}
                      </td>
                      <td className="py-4 px-6">
                        {formatDate(item.updated_at)}
                      </td>
                      <td className="py-4 px-6">
                        <div className="flex items-center justify-end gap-2">
                          <Link href={`/automations/${item.id}`} className="flex items-center gap-1.5 px-3 py-1.5 border border-slate-200 rounded-md text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors">
                            <EditIcon className="w-3.5 h-3.5" />
                            Edit
                          </Link>
                          <button disabled={busy} className="flex items-center gap-1.5 px-3 py-1.5 border border-slate-200 rounded-md text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors">
                            <CopyIcon className="w-3.5 h-3.5" />
                            Copy
                          </button>
                          <button 
                            disabled={busy} 
                            onClick={() => archive(item)}
                            className="flex items-center gap-1.5 px-3 py-1.5 border border-red-200 rounded-md text-sm font-semibold text-red-500 hover:bg-red-50 transition-colors"
                          >
                            <TrashIcon className="w-3.5 h-3.5" />
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
