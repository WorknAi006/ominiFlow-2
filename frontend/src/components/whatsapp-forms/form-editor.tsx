"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createForm, getForm, updateForm, type WhatsAppForm } from "@/lib/whatsapp-forms/browser";

const ZapIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>);
const SettingsIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" /><circle cx="12" cy="12" r="3" /></svg>);
const ChevronLeftIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polyline points="15 18 9 12 15 6" /></svg>);

export function FormEditor({ id }: { id?: string }) {
  const router = useRouter();
  const [form, setForm] = useState<Partial<WhatsAppForm>>({ name: "", category: "Other", status: "draft" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (id) {
      setBusy(true);
      getForm(id).then(res => setForm(res)).catch(e => setError(e.message)).finally(() => setBusy(false));
    }
  }, [id]);

  async function handleSave(status: "draft" | "active") {
    if (!form.name?.trim()) {
      setError("Please provide a name for your form.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      if (id) {
        await updateForm(id, { name: form.name, category: form.category || "Other", status });
      } else {
        const created = await createForm({ name: form.name, category: form.category || "Other" });
        if (status === "active") {
          await updateForm(created.id, { status: "active" });
        }
      }
      router.push("/whatsapp-forms");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save form.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="bg-[#f8f9fa] min-h-screen">
      {/* Top Navigation */}
      <div className="bg-white border-b border-slate-200">
        <div className="px-6 py-4 flex items-center justify-between mx-auto max-w-7xl">
          <div className="flex items-center gap-4">
            <Link href="/whatsapp-forms" className="p-2 border border-slate-200 rounded-full hover:bg-slate-50 transition-colors">
              <ChevronLeftIcon className="w-5 h-5 text-slate-500" />
            </Link>
            <div>
              <h1 className="text-[20px] font-bold text-slate-800 leading-tight">WhatsApp Form Builder</h1>
              <p className="text-sm text-slate-500 mt-0.5">Design WhatsApp Forms visually without writing JSON</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 bg-[#e8f5e9] text-[#2e7d32] px-4 py-2 rounded-full font-semibold text-sm border border-[#c8e6c9]">
              <ZapIcon className="w-4 h-4 fill-current" />
              <span>461.12 AI Credits</span>
            </div>
            <button className="p-2.5 bg-white border border-slate-200 rounded-md text-slate-500 hover:bg-slate-50 shadow-sm">
              <SettingsIcon className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      <div className="p-6 mx-auto max-w-7xl">
        {error && <p className="mb-4 p-3 bg-rose-50 text-rose-700 rounded-lg text-sm font-semibold">{error}</p>}
        
        {/* Builder Header */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <h2 className="text-[22px] font-bold text-slate-800">Create form</h2>
            <p className="text-slate-500 text-sm mt-1">1. Name your form &rarr; 2. Add screens & components &rarr; 3. Save as draft, or Publish to go live</p>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/whatsapp-forms" className="px-5 py-2.5 bg-white border border-slate-200 rounded-md font-semibold text-slate-700 hover:bg-slate-50 shadow-sm text-sm">
              Cancel
            </Link>
            <button onClick={() => handleSave("draft")} disabled={busy} className="px-5 py-2.5 bg-white border border-slate-200 rounded-md font-semibold text-slate-700 hover:bg-slate-50 shadow-sm text-sm">
              Save draft
            </button>
            <button onClick={() => handleSave("active")} disabled={busy} className="px-5 py-2.5 bg-[#00b050] hover:bg-[#009040] text-white rounded-md font-semibold text-sm shadow-sm flex items-center gap-2">
              Publish &rarr;
            </button>
          </div>
        </div>

        {/* Form Meta details */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 mb-8 shadow-sm flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="font-bold text-slate-700">Flow</span>
            <input 
              type="text" 
              placeholder="Name your form..." 
              value={form.name || ""}
              onChange={e => setForm({ ...form, name: e.target.value })}
              className="w-64 px-4 py-2 bg-white border border-slate-200 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 placeholder:text-slate-400"
            />
            <select 
              value={form.category || "Other"}
              onChange={e => setForm({ ...form, category: e.target.value })}
              className="w-40 px-4 py-2 bg-white border border-slate-200 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
            >
              <option value="Other">Other</option>
              <option value="Sign Up">Sign Up</option>
              <option value="Lead Gen">Lead Gen</option>
              <option value="Support">Support</option>
            </select>
          </div>
          <div className="text-sm">
            <span className="font-bold text-slate-800">Save</span> <span className="text-slate-500">keeps it a Draft.</span> <span className="font-bold text-[#00b050]">Publish</span> <span className="text-slate-500">makes it live.</span>
          </div>
        </div>

        {/* Workspace */}
        <div className="flex gap-8">
          
          {/* Left: Screens */}
          <div className="w-64">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-lg text-slate-800">Screens</h3>
              <button className="w-6 h-6 rounded-full border border-slate-300 flex items-center justify-center text-slate-600 hover:bg-slate-100">
                <span className="text-lg leading-none mb-0.5">+</span>
              </button>
            </div>
            
            <div className="bg-[#e8f5e9] border border-[#c8e6c9] rounded-xl p-4 cursor-pointer">
              <div className="font-semibold text-slate-800">Welcome Screen</div>
              <div className="text-sm text-slate-500 mt-1">0 fields</div>
            </div>
          </div>

          {/* Middle: Canvas */}
          <div className="flex-1 bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm flex flex-col items-center py-10 min-h-[500px]">
            <div className="w-[320px] bg-slate-50 border border-slate-200 rounded-[2rem] p-4 shadow-sm relative h-[480px] flex flex-col">
              <div className="bg-[#00b050] text-white font-bold py-3 px-4 rounded-t-2xl rounded-b-sm mb-4 text-center text-lg">
                Screen
              </div>
              
              <div className="flex-1 bg-white border border-slate-200 border-dashed rounded-lg flex items-center justify-center text-center p-6 text-sm text-slate-500">
                No fields added to this screen yet.
              </div>

              <div className="mt-4 bg-[#a5d6a7] text-white font-bold py-3 px-4 rounded-xl text-center">
                Next / Submit
              </div>
            </div>
          </div>

          {/* Right: Add Components */}
          <div className="w-72">
            <h3 className="font-bold text-lg text-slate-800 mb-4">Add Components</h3>
            <div className="space-y-3">
              {[
                "Heading / Text",
                "Short Text Input",
                "Paragraph (TextArea)",
                "Dropdown Menu",
                "Radio Buttons",
                "Checkboxes",
                "Date Picker"
              ].map(comp => (
                <button key={comp} className="w-full text-left bg-white border border-slate-200 rounded-lg px-4 py-3 text-sm font-semibold text-slate-700 hover:border-emerald-500 hover:text-emerald-700 hover:bg-emerald-50 transition-colors shadow-sm">
                  + {comp}
                </button>
              ))}
            </div>
          </div>
          
        </div>
      </div>
    </div>
  );
}
