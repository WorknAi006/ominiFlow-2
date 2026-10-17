"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { deleteForm, listForms, type WhatsAppForm } from "@/lib/whatsapp-forms/browser";
import { useCreditBalance } from "@/lib/credits/use-credit-balance";

const ZapIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>);
const SettingsIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" /><circle cx="12" cy="12" r="3" /></svg>);
const PlusIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>);
const SearchIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>);
const RefreshIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" /></svg>);
const EditIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M12 20h9" /><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" /></svg>);
const CopyIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><rect x="9" y="9" width="13" height="13" rx="2" ry="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" /></svg>);
const TrashIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>);

export function FormsClient() {
  const creditBalance = useCreditBalance();
  const [items, setItems] = useState<WhatsAppForm[]>([]);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    try {
      setBusy(true);
      const result = await listForms();
      setItems(result.items);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load forms.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  const filtered = useMemo(() => 
    items.filter(item => item.name.toLowerCase().includes(search.toLowerCase())), 
    [items, search]
  );

  async function handleDelete(item: WhatsAppForm) {
    if (!window.confirm(`Delete “${item.name}”?`)) return;
    try {
      setBusy(true);
      await deleteForm(item.id);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete form.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="bg-[#f8f9fa] min-h-screen">
      <div className="p-8 mx-auto max-w-7xl">
        {/* Header */}
        <div className="flex justify-between items-start mb-8">
          <div>
            <h1 className="text-[24px] font-bold text-slate-800 leading-tight">WhatsApp Forms</h1>
            <p className="text-sm text-slate-500 font-medium mt-1">List existing forms and create new WhatsApp Forms</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 bg-[#e8f5e9] text-[#2e7d32] px-4 py-2 rounded-full font-semibold text-sm border border-[#c8e6c9]">
              <ZapIcon className="w-4 h-4 fill-current" />
              <span>{creditBalance === null ? "…" : creditBalance.toFixed(2)} AI Credits</span>
            </div>
            <button className="p-2.5 bg-white border border-slate-200 rounded-md text-slate-500 hover:bg-slate-50 shadow-sm">
              <SettingsIcon className="w-5 h-5" />
            </button>
          </div>
        </div>

        {error && <p role="alert" className="rounded-xl bg-rose-50 p-4 text-rose-800 mb-6">{error}</p>}

        {/* Toolbar */}
        <div className="flex items-center justify-between mb-6">
          <div className="relative w-96">
            <SearchIcon className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search WhatsApp Forms..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 bg-white border border-slate-200 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
            />
          </div>
          <div className="flex items-center gap-3">
            <button onClick={refresh} disabled={busy} className="p-2.5 bg-white border border-slate-200 rounded-md text-slate-600 hover:bg-slate-50">
              <RefreshIcon className={`w-4 h-4 ${busy ? 'animate-spin' : ''}`} />
            </button>
            <Link href="/whatsapp-forms/new" className="flex items-center gap-2 bg-[#00b050] hover:bg-[#009040] text-white px-5 py-2.5 rounded-md font-semibold text-sm transition-colors shadow-sm">
              <PlusIcon className="w-4 h-4" />
              <span>Create Form</span>
            </Link>
          </div>
        </div>

        {/* Table Card */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100 bg-[#fbfcfd]">
                  <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider">Form ID</th>
                  <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider">Name</th>
                  <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
                  <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider">Categories</th>
                  <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider text-right pr-6">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-16 text-center text-slate-500 text-sm">
                      No WhatsApp Forms found. Click 'Create Form' to get started.
                    </td>
                  </tr>
                ) : (
                  filtered.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50/50 transition-colors">
                      <td className="py-4 px-6 text-sm font-semibold text-slate-700">
                        {item.id.slice(0, 8)}...
                      </td>
                      <td className="py-4 px-6">
                        <div className="font-bold text-slate-800">{item.name}</div>
                      </td>
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${item.status === 'active' ? 'bg-[#00b050]' : 'bg-slate-400'}`} />
                          <span className={`text-sm font-bold ${item.status === 'active' ? 'text-[#00b050]' : 'text-slate-600 capitalize'}`}>
                            {item.status}
                          </span>
                        </div>
                      </td>
                      <td className="py-4 px-6 text-sm text-slate-700">
                        {item.category || "-"}
                      </td>
                      <td className="py-4 px-6">
                        <div className="flex items-center justify-end gap-2">
                          <Link href={`/whatsapp-forms/${item.id}`} className="flex items-center gap-1.5 px-3 py-1.5 border border-slate-200 rounded-md text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors">
                            <EditIcon className="w-3.5 h-3.5" />
                            Edit
                          </Link>
                          <button disabled={busy} className="flex items-center gap-1.5 px-3 py-1.5 border border-slate-200 rounded-md text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors">
                            <CopyIcon className="w-3.5 h-3.5" />
                            Copy
                          </button>
                          <button 
                            disabled={busy} 
                            onClick={() => handleDelete(item)}
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
