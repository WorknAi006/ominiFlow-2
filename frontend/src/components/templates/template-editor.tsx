"use client";

import { useState } from "react";
import Link from "next/link";

const ChevronLeftIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polyline points="15 18 9 12 15 6" /></svg>);
const SparklesIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M9 3v1m0 4v1m0-1a2 2 0 0 0 2-2 2 2 0 0 0-2-2 2 2 0 0 0-2 2 2 2 0 0 0 2 2zm7 5v1m0 4v1m0-1a2 2 0 0 0 2-2 2 2 0 0 0-2-2 2 2 0 0 0-2 2 2 2 0 0 0 2 2zM4 15v1m0 4v1m0-1a2 2 0 0 0 2-2 2 2 0 0 0-2-2 2 2 0 0 0-2 2 2 2 0 0 0 2 2zm16-4v1m0 4v1m0-1a2 2 0 0 0 2-2 2 2 0 0 0-2-2 2 2 0 0 0-2 2 2 2 0 0 0 2 2z" /></svg>);
const SaveIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" /><polyline points="17 21 17 13 7 13 7 21" /><polyline points="7 3 7 8 15 8" /></svg>);
const LockIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>);

// Rich Text Icons
const BoldIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M6 4h8a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z" /><path d="M6 12h9a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z" /></svg>);
const ItalicIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><line x1="19" y1="4" x2="10" y2="4" /><line x1="14" y1="20" x2="5" y2="20" /><line x1="15" y1="4" x2="9" y2="20" /></svg>);
const StrikeIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><line x1="5" y1="12" x2="19" y2="12" /><path d="M16 6C16 6 14.5 4 12 4C9.5 4 8 6 8 8C8 10 9.5 12 12 12C14.5 12 16 14 16 16C16 18 14.5 20 12 20C9.5 20 8 18 8 18" /></svg>);
const SmileIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="12" cy="12" r="10" /><path d="M8 14s1.5 2 4 2 4-2 4-2" /><line x1="9" y1="9" x2="9.01" y2="9" /><line x1="15" y1="9" x2="15.01" y2="9" /></svg>);
const LayoutIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="9" y1="21" x2="9" y2="9" /></svg>);
const TimerIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>);
const ShieldCheckIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /><path d="M9 12l2 2 4-4" /></svg>);


export function TemplateEditor() {
  const [templateType, setTemplateType] = useState("Standard");
  const [category, setCategory] = useState("Marketing");
  const [language, setLanguage] = useState("English");
  const [name, setName] = useState("");
  const [headerType, setHeaderType] = useState("None");
  const [bodyText, setBodyText] = useState("");
  const [footerText, setFooterText] = useState("");
  const [buttons, setButtons] = useState<string[]>([]);

  return (
    <div className="bg-[#f8f9fa] min-h-screen text-slate-800 font-sans">
      {/* Top Navigation */}
      <div className="bg-white border-b border-slate-200">
        <div className="px-6 py-4 flex items-center justify-between mx-auto max-w-7xl">
          <div className="flex items-center gap-4">
            <Link href="/templates" className="p-2 border border-slate-200 rounded-full hover:bg-slate-50 transition-colors">
              <ChevronLeftIcon className="w-5 h-5 text-slate-500" />
            </Link>
            <h1 className="text-xl font-bold text-slate-800">Create Template</h1>
          </div>
          <button className="px-5 py-2.5 bg-[#00b050] hover:bg-[#009040] text-white rounded-lg font-bold text-sm shadow-sm flex items-center gap-2">
            <SaveIcon className="w-4 h-4" /> Save Template
          </button>
        </div>
      </div>

      <div className="p-6 mx-auto max-w-7xl flex gap-8">
        
        {/* Left Column (Form) */}
        <div className="flex-1 space-y-6 max-w-3xl">
          
          {/* Template Type Selector */}
          <div className="grid grid-cols-4 gap-4">
            <button 
              onClick={() => setTemplateType("Standard")}
              className={`p-4 text-left border rounded-xl bg-white transition-all ${
                templateType === "Standard" ? "border-[#00b050] shadow-sm ring-1 ring-[#00b050]/20" : "border-slate-200 hover:border-slate-300"
              }`}
            >
              <LayoutIcon className={`w-5 h-5 mb-3 ${templateType === "Standard" ? "text-[#00b050]" : "text-slate-400"}`} />
              <div className="font-bold text-slate-900 mb-1">Standard</div>
              <div className="text-xs text-slate-500 leading-tight">Text or media header, body, footer & buttons</div>
            </button>
            <button 
              onClick={() => setTemplateType("Carousel")}
              className={`p-4 text-left border rounded-xl bg-white transition-all ${
                templateType === "Carousel" ? "border-[#00b050] shadow-sm ring-1 ring-[#00b050]/20" : "border-slate-200 hover:border-slate-300"
              }`}
            >
              <LayoutIcon className={`w-5 h-5 mb-3 ${templateType === "Carousel" ? "text-[#00b050]" : "text-slate-400"}`} />
              <div className="font-bold text-slate-900 mb-1">Carousel</div>
              <div className="text-xs text-slate-500 leading-tight">Up to 10 swipeable media cards</div>
            </button>
            <button 
              onClick={() => setTemplateType("Offer")}
              className={`p-4 text-left border rounded-xl bg-white transition-all ${
                templateType === "Offer" ? "border-[#00b050] shadow-sm ring-1 ring-[#00b050]/20" : "border-slate-200 hover:border-slate-300"
              }`}
            >
              <TimerIcon className={`w-5 h-5 mb-3 ${templateType === "Offer" ? "text-[#00b050]" : "text-slate-400"}`} />
              <div className="font-bold text-slate-900 mb-1">Limited-Time Offer</div>
              <div className="text-xs text-slate-500 leading-tight">Coupon code with a countdown</div>
            </button>
            <button 
              onClick={() => setTemplateType("OTP")}
              className={`p-4 text-left border rounded-xl bg-white transition-all ${
                templateType === "OTP" ? "border-[#00b050] shadow-sm ring-1 ring-[#00b050]/20" : "border-slate-200 hover:border-slate-300"
              }`}
            >
              <ShieldCheckIcon className={`w-5 h-5 mb-3 ${templateType === "OTP" ? "text-[#00b050]" : "text-slate-400"}`} />
              <div className="font-bold text-slate-900 mb-1">Authentication (OTP)</div>
              <div className="text-xs text-slate-500 leading-tight">Verification code with autofill / copy</div>
            </button>
          </div>

          {/* Basic Info */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-bold text-slate-900">Basic Info</h2>
              <button className="flex items-center gap-2 px-4 py-2 bg-purple-50 text-purple-700 rounded-lg font-bold text-sm border border-purple-100 hover:bg-purple-100">
                <SparklesIcon className="w-4 h-4" /> Generate with AI
              </button>
            </div>
            
            <div className="grid grid-cols-2 gap-6 mb-6">
              <div>
                <label className="block text-sm font-bold text-slate-700 mb-2">Category <span className="text-rose-500">*</span></label>
                <select 
                  value={category} 
                  onChange={e => setCategory(e.target.value)}
                  className="w-full px-4 py-2.5 bg-white border border-slate-200 rounded-lg text-sm text-slate-800 outline-none focus:border-[#00b050] focus:ring-1 focus:ring-[#00b050]"
                >
                  <option>Marketing</option>
                  <option>Utility</option>
                  <option>Authentication</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-bold text-slate-700 mb-2">Language</label>
                <select 
                  value={language} 
                  onChange={e => setLanguage(e.target.value)}
                  className="w-full px-4 py-2.5 bg-white border border-slate-200 rounded-lg text-sm text-slate-800 outline-none focus:border-[#00b050] focus:ring-1 focus:ring-[#00b050]"
                >
                  <option>English</option>
                  <option>Spanish</option>
                  <option>Hindi</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-bold text-slate-700 mb-2">Template Name <span className="text-rose-500">*</span></label>
              <div className="relative">
                <input 
                  type="text" 
                  value={name} 
                  onChange={e => setName(e.target.value)}
                  placeholder="e.g. my_template_name"
                  maxLength={512}
                  className="w-full px-4 py-2.5 bg-white border border-slate-200 rounded-lg text-sm text-slate-800 outline-none focus:border-[#00b050] focus:ring-1 focus:ring-[#00b050]"
                />
                <span className="absolute right-4 top-2.5 text-xs font-semibold text-slate-400">
                  {name.length}/512
                </span>
              </div>
            </div>
          </div>

          {/* Header section */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
            <h2 className="text-lg font-bold text-slate-900 mb-6">Header</h2>
            <div className="flex gap-6">
              {["None", "Text", "Image", "Video", "Document"].map(opt => (
                <label key={opt} className="flex items-center gap-2 cursor-pointer">
                  <input 
                    type="radio" 
                    name="headerType" 
                    value={opt} 
                    checked={headerType === opt} 
                    onChange={() => setHeaderType(opt)} 
                    className="w-4 h-4 text-[#00b050] focus:ring-[#00b050]"
                  />
                  <span className="text-sm font-semibold text-slate-700">{opt}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Body Section */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold text-slate-900">Body</h2>
              <button className="flex items-center gap-2 px-4 py-1.5 bg-white text-[#00b050] rounded-lg font-bold text-sm border border-[#00b050] hover:bg-emerald-50">
                + Add Variable
              </button>
            </div>
            
            <p className="text-sm text-slate-600 mb-6 leading-relaxed">
              Make your messages personal using variables like <code className="text-[#00b050] font-bold bg-[#e8f5e9] px-1 rounded">{`{{1}}`}</code>, <code className="text-[#00b050] font-bold bg-[#e8f5e9] px-1 rounded">{`{{2}}`}</code> etc. Variables will be automatically numbered and sent to Meta API!
            </p>

            <div className="border border-slate-200 rounded-xl overflow-hidden focus-within:border-[#00b050] focus-within:ring-1 focus-within:ring-[#00b050] transition-all">
              <div className="flex justify-between items-center px-4 py-3 bg-slate-50/50 border-b border-slate-100">
                <div className="flex gap-4 text-slate-500">
                  <button className="hover:text-slate-800"><SmileIcon className="w-4 h-4" /></button>
                  <button className="hover:text-slate-800"><BoldIcon className="w-4 h-4" /></button>
                  <button className="hover:text-slate-800"><ItalicIcon className="w-4 h-4" /></button>
                  <button className="hover:text-slate-800"><StrikeIcon className="w-4 h-4" /></button>
                </div>
                <div className="text-xs font-semibold text-slate-400">
                  {bodyText.length}/1024
                </div>
              </div>
              <textarea 
                className="w-full min-h-[160px] p-4 text-[15px] resize-none outline-none text-slate-800 placeholder:text-slate-400"
                placeholder="Template Message (e.g., Shop now through {{1}} and use code {{2}} to get {{3}} off!)"
                value={bodyText}
                maxLength={1024}
                onChange={e => setBodyText(e.target.value)}
              />
            </div>
          </div>

          {/* Footer Section */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
            <h2 className="text-lg font-bold text-slate-900 mb-1">Footer <span className="text-slate-400 font-normal text-sm">(Optional)</span></h2>
            <p className="text-sm text-slate-600 mb-4">Footers are great to add any disclaimers or to add a thoughtful PS</p>
            <div className="relative">
              <textarea 
                className="w-full min-h-[80px] p-4 bg-white border border-slate-200 rounded-xl text-sm text-slate-800 outline-none focus:border-[#00b050] focus:ring-1 focus:ring-[#00b050] resize-none placeholder:text-slate-400"
                placeholder="Add footer text (optional)"
                maxLength={60}
                value={footerText}
                onChange={e => setFooterText(e.target.value)}
              />
              <div className="absolute bottom-4 left-4 text-xs font-semibold text-slate-400">
                {footerText.length}/60
              </div>
            </div>
          </div>

          {/* Buttons Section */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm mb-10">
            <h2 className="text-lg font-bold text-slate-900 mb-1">Buttons <span className="text-slate-400 font-normal text-sm">(Optional)</span></h2>
            <p className="text-sm text-slate-600 mb-6">Create up to 11 buttons that let customers respond to your message or take action.</p>
            
            <div className="flex gap-3">
              <button className="flex items-center justify-between px-4 py-2.5 bg-white border border-slate-200 rounded-lg text-sm font-bold text-slate-700 w-48 hover:bg-slate-50">
                <span>+ Add button</span>
                <span className="text-slate-400 text-xs">▼</span>
              </button>
            </div>
          </div>
          
          <div className="h-20"></div>

        </div>

        {/* Right Column (Mobile Preview) */}
        <div className="w-[360px] sticky top-8 self-start pt-8">
          
          <div className="border-[6px] border-slate-200 rounded-[3rem] overflow-hidden bg-[#efeae2] h-[720px] flex flex-col relative shadow-xl">
            {/* Phone Notch/Top bar */}
            <div className="bg-white text-slate-900 px-6 pt-4 pb-3 flex justify-between items-center text-xs font-bold border-b border-slate-100 z-10">
              <div className="w-10">9:41</div>
              <div className="w-24 h-6 bg-black rounded-full" /> {/* Dynamic Island mockup */}
              <div className="w-10 flex justify-end gap-1">
                <div className="w-4 h-3 bg-slate-900 rounded-sm"></div>
              </div>
            </div>
            
            {/* WhatsApp Header Mock */}
            <div className="bg-[#005c4b] text-white px-4 py-3 flex items-center gap-3 z-10">
              <ChevronLeftIcon className="w-5 h-5 text-white/80" />
              <div className="w-10 h-10 rounded-full bg-white/20" />
              <div className="flex-1">
                <div className="w-24 h-4 bg-white/30 rounded mb-1.5" />
                <div className="w-16 h-2.5 bg-white/20 rounded" />
              </div>
            </div>
            
            {/* Post Content */}
            <div className="flex-1 p-4 flex flex-col gap-3 relative z-10 overflow-y-auto">
              
              <div className="bg-[#fcedb3] text-slate-700 text-[11px] p-3 rounded-lg mx-auto max-w-[90%] text-center shadow-sm flex items-center gap-2">
                <LockIcon className="w-4 h-4 shrink-0" />
                This business uses a secure service from Meta to manage this chat. <span className="text-[#008069]">Tap to learn more</span>
              </div>
              
              <div className="bg-white p-3 rounded-2xl rounded-tl-none shadow-sm self-start max-w-[90%] relative mt-2 text-[15px] leading-relaxed text-slate-800 font-sans">
                {headerType !== "None" && (
                  <div className="mb-2 w-full h-32 bg-slate-100 rounded-lg flex items-center justify-center text-slate-400 text-sm font-semibold border border-slate-200">
                    {headerType} Header
                  </div>
                )}
                
                <div className="whitespace-pre-wrap">
                  {bodyText || "Your message preview will appear here"}
                </div>
                
                {footerText && (
                  <div className="text-xs text-slate-500 mt-2">
                    {footerText}
                  </div>
                )}

                <div className="text-[10px] text-slate-400 text-right mt-1">11:27 AM</div>
              </div>

            </div>
            
            {/* BG pattern overlay */}
            <div className="absolute inset-0 opacity-40 mix-blend-multiply pointer-events-none" style={{ backgroundImage: 'radial-gradient(#cfd8dc 1px, transparent 1px)', backgroundSize: '24px 24px' }} />

            {/* Phone Bottom bar */}
            <div className="h-10 bg-[#f0f0f0] w-full mt-auto relative z-10 flex justify-center pb-2">
              <div className="w-32 h-1.5 bg-slate-400 rounded-full mt-auto" />
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
