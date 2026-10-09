"use client";

import { useState } from "react";

const NavigationIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polygon points="3 11 22 2 13 21 11 13 3 11" /></svg>);
const CalendarIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" /></svg>);
const UsersIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>);
const FileTextIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /><polyline points="10 9 9 9 8 9" /></svg>);
const MoreHorizontalIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="12" cy="12" r="1" /><circle cx="19" cy="12" r="1" /><circle cx="5" cy="12" r="1" /></svg>);
const ImageIconIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><circle cx="8.5" cy="8.5" r="1.5" /><polyline points="21 15 16 10 5 21" /></svg>);
const SmileIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="12" cy="12" r="10" /><path d="M8 14s1.5 2 4 2 4-2 4-2" /><line x1="9" y1="9" x2="9.01" y2="9" /><line x1="15" y1="9" x2="15.01" y2="9" /></svg>);
const LinkIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" /></svg>);
const HashIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><line x1="4" y1="9" x2="20" y2="9" /><line x1="4" y1="15" x2="20" y2="15" /><line x1="10" y1="3" x2="8" y2="21" /><line x1="16" y1="3" x2="14" y2="21" /></svg>);
const SparklesIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M9 3v1m0 4v1m0-1a2 2 0 0 0 2-2 2 2 0 0 0-2-2 2 2 0 0 0-2 2 2 2 0 0 0 2 2zm7 5v1m0 4v1m0-1a2 2 0 0 0 2-2 2 2 0 0 0-2-2 2 2 0 0 0-2 2 2 2 0 0 0 2 2zM4 15v1m0 4v1m0-1a2 2 0 0 0 2-2 2 2 0 0 0-2-2 2 2 0 0 0-2 2 2 2 0 0 0 2 2zm16-4v1m0 4v1m0-1a2 2 0 0 0 2-2 2 2 0 0 0-2-2 2 2 0 0 0-2 2 2 2 0 0 0 2 2z" /></svg>);
const ChevronRightIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polyline points="9 18 15 12 9 6" /></svg>);

export function PostingsClient() {
  const [activeTab, setActiveTab] = useState("Overview");
  const [caption, setCaption] = useState("");
  const [captionInstruction, setCaptionInstruction] = useState("");

  const tabs = ["Overview", "Posts", "Create post", "Social accounts", "Media", "Calendar"];

  return (
    <div className="bg-white min-h-screen text-slate-800 flex flex-col font-sans">
      <div className="p-8 mx-auto max-w-6xl w-full flex-1">
        
        {/* Header */}
        <div className="flex justify-between items-start mb-6">
          <div>
            <div className="text-xs font-bold tracking-widest text-slate-500 uppercase mb-2">Manage</div>
            <h1 className="text-[28px] font-bold text-slate-800 leading-tight mb-1">Postings</h1>
            <p className="text-[15px] text-slate-500">Plan, publish and measure your social media content.</p>
          </div>
          <button 
            onClick={() => setActiveTab("Create post")}
            className="bg-[#00b050] hover:bg-[#009040] text-white px-5 py-2.5 rounded-md font-bold text-sm shadow-sm"
          >
            + Create post
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b border-slate-200 mb-8 flex gap-8">
          {tabs.map(tab => (
            <button 
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-3 text-[15px] font-bold border-b-2 transition-colors ${
                activeTab === tab 
                  ? "border-[#00b050] text-[#00b050]" 
                  : "border-transparent text-slate-500 hover:text-slate-700"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === "Overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Connected account card */}
            <div className="bg-[#e0f2df] rounded-2xl p-6 border border-[#c8e6c9] flex flex-col">
              <div className="flex justify-between items-start mb-6">
                <div className="text-xs font-bold text-slate-700 uppercase tracking-widest">Connected Account</div>
                <button className="flex items-center gap-1 text-xs font-bold text-slate-600 bg-white/50 px-2 py-1 rounded">
                  <RefreshCwIcon className="w-3 h-3" /> Switch
                </button>
              </div>
              <div className="flex-1 flex flex-col items-center justify-center text-center">
                <div className="w-20 h-20 rounded-full bg-blue-600 text-white flex items-center justify-center text-3xl font-bold mb-4 shadow-sm">
                  C
                </div>
                <h2 className="text-xl font-bold text-slate-900 mb-2">Connected account</h2>
                <p className="text-sm text-slate-600 mb-6">Connect an account to start posting</p>
                
                <div className="flex w-full gap-3">
                  <button className="flex-1 py-2.5 bg-white text-slate-800 font-bold text-sm rounded-lg border border-slate-200">
                    View account
                  </button>
                  <button 
                    onClick={() => setActiveTab("Create post")}
                    className="flex-1 py-2.5 bg-slate-900 text-white font-bold text-sm rounded-lg"
                  >
                    Create post
                  </button>
                </div>
              </div>
              <div className="mt-6 flex justify-between items-center pt-4 border-t border-[#c8e6c9]/50 text-xs font-semibold text-slate-600">
                <span>Accounts</span>
                <span>0 connected</span>
              </div>
            </div>

            {/* Publishing analytics */}
            <div className="bg-white rounded-2xl p-6 border border-slate-200 flex flex-col shadow-sm">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h3 className="font-bold text-lg text-slate-900">Publishing analytics</h3>
                  <p className="text-xs text-slate-500 mt-1">Current overview for this month</p>
                </div>
                <button className="p-1.5 border border-slate-200 rounded-lg text-slate-400 hover:bg-slate-50">
                  <MoreHorizontalIcon className="w-4 h-4" />
                </button>
              </div>

              <div className="grid grid-cols-4 gap-3 mb-8">
                <div className="bg-[#f1f8e9] rounded-xl p-3 flex flex-col">
                  <NavigationIcon className="w-4 h-4 text-slate-700 mb-3" />
                  <div className="text-2xl font-black text-slate-900 mb-1">0</div>
                  <div className="text-[11px] leading-tight text-slate-600 font-medium">Published this month</div>
                </div>
                <div className="bg-[#fff3e0] rounded-xl p-3 flex flex-col">
                  <CalendarIcon className="w-4 h-4 text-slate-700 mb-3" />
                  <div className="text-2xl font-black text-slate-900 mb-1">0</div>
                  <div className="text-[11px] leading-tight text-slate-600 font-medium">Scheduled</div>
                </div>
                <div className="bg-[#e0f2f1] rounded-xl p-3 flex flex-col">
                  <UsersIcon className="w-4 h-4 text-slate-700 mb-3" />
                  <div className="text-2xl font-black text-slate-900 mb-1">0</div>
                  <div className="text-[11px] leading-tight text-slate-600 font-medium">Connected accounts</div>
                </div>
                <div className="bg-[#f5f5f5] rounded-xl p-3 flex flex-col">
                  <FileTextIcon className="w-4 h-4 text-slate-700 mb-3" />
                  <div className="text-2xl font-black text-slate-900 mb-1">0</div>
                  <div className="text-[11px] leading-tight text-slate-600 font-medium">Draft posts</div>
                </div>
              </div>

              <div className="mt-auto">
                <div className="flex gap-1 mb-2">
                  {[...Array(9)].map((_, i) => (
                    <div key={i} className={`h-1.5 rounded-full flex-1 ${i === 8 ? 'bg-[#00b050]' : 'bg-[#00b050]'}`} />
                  ))}
                </div>
                <div className="flex justify-between items-center text-xs font-semibold text-slate-600">
                  <span>Unable to load activity</span>
                  <span className="text-slate-900">0 successful posts</span>
                </div>
              </div>
            </div>

            {/* Last posts */}
            <div className="bg-[#f5f7f5] rounded-2xl p-6 border border-slate-200 flex flex-col shadow-sm">
              <div className="flex justify-between items-start mb-12">
                <div>
                  <h3 className="font-bold text-lg text-slate-900">Last posts</h3>
                  <p className="text-xs text-slate-500 mt-1">Most recent publishing activity</p>
                </div>
                <button className="p-1.5 border border-slate-200 bg-white rounded-lg text-slate-400 hover:bg-slate-50">
                  <MoreHorizontalIcon className="w-4 h-4" />
                </button>
              </div>

              <div className="flex-1 flex flex-col items-center justify-center">
                <p className="text-sm font-semibold text-slate-500 mb-6">No published posts yet.</p>
                <button 
                  onClick={() => setActiveTab("Posts")}
                  className="w-full py-2.5 bg-white text-slate-800 font-bold text-sm rounded-lg border border-slate-200 shadow-sm"
                >
                  View all posts &gt;
                </button>
              </div>
            </div>

          </div>
        )}

        {activeTab === "Create post" && (
          <div className="space-y-6">
            
            {/* Choose an account bar */}
            <div className="bg-[#a8e6cf]/30 border border-[#a8e6cf] rounded-2xl p-4 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-[#a8e6cf] text-emerald-800 font-bold flex items-center justify-center text-lg">
                  A
                </div>
                <div>
                  <div className="font-bold text-slate-900">Choose an account</div>
                  <div className="text-sm text-slate-600">Select an account to choose platforms</div>
                </div>
              </div>
              <button className="bg-[#0f766e] hover:bg-[#0d645d] text-white px-5 py-2.5 rounded-lg font-bold text-sm flex items-center gap-2">
                Choose account <ChevronRightIcon className="w-4 h-4" />
              </button>
            </div>

            <div className="flex flex-col lg:flex-row gap-6">
              
              {/* Left Column (Create Post Form) */}
              <div className="flex-1 space-y-6">
                
                {/* Text Editor Box */}
                <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
                  <div className="flex justify-between items-start mb-6">
                    <div>
                      <h2 className="text-lg font-bold text-slate-900">Create post</h2>
                      <p className="text-xs text-slate-500 mt-1">One focused workspace for content, media and publishing.</p>
                    </div>
                    <button className="px-4 py-2 bg-white border border-slate-200 rounded-lg font-bold text-sm text-slate-600 flex items-center gap-2">
                      <span className="text-slate-400">👁</span> Preview
                    </button>
                  </div>

                  <div className="border border-slate-200 rounded-xl overflow-hidden focus-within:border-emerald-500 focus-within:ring-1 focus-within:ring-emerald-500 transition-all">
                    <div className="flex justify-between items-center px-4 py-3 bg-slate-50/50 border-b border-slate-100">
                      <span className="text-sm font-bold text-slate-700">Caption</span>
                      <span className="text-xs font-semibold text-slate-500">Balanced tone</span>
                    </div>
                    <textarea 
                      className="w-full min-h-[120px] p-4 text-[15px] resize-none outline-none text-slate-800 placeholder:text-slate-400"
                      placeholder="What would you like to share?"
                      value={caption}
                      onChange={e => setCaption(e.target.value)}
                    />
                    <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100 bg-slate-50/50">
                      <div className="flex gap-4 text-slate-500">
                        <button className="hover:text-slate-800"><ImageIconIcon className="w-5 h-5" /></button>
                        <button className="hover:text-slate-800"><SmileIcon className="w-5 h-5" /></button>
                        <button className="hover:text-slate-800"><LinkIcon className="w-5 h-5" /></button>
                        <button className="hover:text-slate-800"><HashIcon className="w-5 h-5" /></button>
                      </div>
                      <div className="text-xs font-semibold text-slate-400">
                        {caption.length}/2,200
                      </div>
                    </div>
                  </div>

                  {/* AI Section */}
                  <div className="mt-6 border border-slate-200 rounded-xl p-4 bg-slate-50/30">
                    <div className="flex gap-3 mb-3">
                      <input 
                        type="text" 
                        placeholder="Optional AI instruction, e.g. friendly festive caption" 
                        className="flex-1 px-4 py-2 border border-slate-200 rounded-lg text-sm outline-none focus:border-purple-300 focus:ring-1 focus:ring-purple-300"
                        value={captionInstruction}
                        onChange={e => setCaptionInstruction(e.target.value)}
                      />
                      <button className="flex items-center gap-2 px-4 py-2 bg-white border border-purple-200 text-purple-700 font-bold text-sm rounded-lg hover:bg-purple-50">
                        <SparklesIcon className="w-4 h-4" /> Generate captions
                      </button>
                    </div>
                    <div className="flex gap-2">
                      {["Concise", "Warm", "Add CTA", "Hashtags"].map(pill => (
                        <button key={pill} className="px-3 py-1 bg-white border border-purple-200 text-purple-700 text-xs font-bold rounded-full hover:bg-purple-50">
                          {pill}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Format & Tags */}
                  <div className="mt-6 grid grid-cols-2 gap-6">
                    <div>
                      <div className="text-sm font-bold text-slate-700 mb-2">Format</div>
                      <div className="flex bg-slate-100 rounded-lg p-1">
                        <button className="flex-1 py-1.5 bg-white shadow-sm border border-slate-200 rounded-md text-sm font-bold text-[#00b050] flex items-center justify-center gap-1.5">
                          <ImageIconIcon className="w-4 h-4" /> Post
                        </button>
                        <button className="flex-1 py-1.5 text-sm font-bold text-slate-500 hover:text-slate-700 flex items-center justify-center gap-1.5">
                          Reel
                        </button>
                        <button className="flex-1 py-1.5 text-sm font-bold text-slate-500 hover:text-slate-700 flex items-center justify-center gap-1.5">
                          Story
                        </button>
                      </div>
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-700 mb-2">Tags</div>
                      <input 
                        type="text" 
                        placeholder="Add a tag and press Enter" 
                        className="w-full px-4 py-2 border border-slate-200 rounded-lg text-sm outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                      />
                    </div>
                  </div>

                  {/* Media Upload */}
                  <div className="mt-6 border-2 border-dashed border-[#f6e58d] bg-[#fffde7] rounded-xl p-8 flex flex-col items-center justify-center text-center">
                    <ImageIconIcon className="w-8 h-8 text-slate-400 mb-3" />
                    <h3 className="font-bold text-slate-800 text-base mb-1">Add visual content</h3>
                    <p className="text-sm text-slate-500 mb-4">Upload from your device or choose from Media.</p>
                    <div className="flex gap-3">
                      <button className="px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm font-bold text-slate-700 hover:bg-slate-50 shadow-sm">
                        Upload
                      </button>
                      <button className="px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm font-bold text-slate-700 hover:bg-slate-50 shadow-sm">
                        Media library
                      </button>
                    </div>
                  </div>

                  {/* Footer Actions */}
                  <div className="mt-6 pt-6 border-t border-slate-100 flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm font-bold text-[#00b050]">
                      <div className="w-2 h-2 rounded-full bg-[#00b050]" />
                      All changes saved
                    </div>
                    <div className="flex items-center gap-3">
                      <button className="px-6 py-2.5 bg-white border border-slate-200 rounded-lg font-bold text-sm text-slate-700 hover:bg-slate-50 shadow-sm">
                        Save draft
                      </button>
                      <button className="px-6 py-2.5 bg-[#4e9c81] hover:bg-[#3d7a65] text-white rounded-lg font-bold text-sm shadow-sm">
                        Publish now
                      </button>
                      <button className="px-6 py-2.5 bg-white border border-slate-200 rounded-lg font-bold text-sm text-slate-700 hover:bg-slate-50 shadow-sm flex items-center gap-2">
                        <CalendarIcon className="w-4 h-4" /> Schedule
                      </button>
                    </div>
                  </div>

                </div>
              </div>

              {/* Right Column (Timing & Preview) */}
              <div className="w-[380px] space-y-6">
                
                {/* Publish Timing */}
                <div className="bg-[#f0f9f5] border border-[#a8e6cf] rounded-2xl p-5">
                  <div className="flex justify-between items-center mb-4">
                    <div className="flex items-center gap-2 font-bold text-slate-900">
                      <div className="w-2 h-2 rounded-full bg-[#00b050]" />
                      Publish timing
                    </div>
                    <span className="text-xs font-semibold text-slate-500">Optional</span>
                  </div>
                  <div className="flex bg-[#d1f2e6] rounded-lg p-1">
                    <button className="flex-1 py-2 bg-[#0f766e] rounded-md text-sm font-bold text-white shadow-sm">
                      Now
                    </button>
                    <button className="flex-1 py-2 text-sm font-bold text-[#0f766e]">
                      Schedule
                    </button>
                  </div>
                </div>

                {/* Readiness */}
                <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                  <div className="flex justify-between items-center mb-5">
                    <div className="flex items-center gap-2 font-bold text-slate-900">
                      <div className="w-2 h-2 rounded-full bg-amber-400" />
                      Readiness
                    </div>
                    <span className="text-xs font-semibold text-slate-500">Needs attention</span>
                  </div>
                  
                  <div className="flex items-center gap-4 mb-6">
                    <div className="w-12 h-12 rounded-full border-4 border-amber-400 flex items-center justify-center font-black text-slate-800 text-lg">
                      25
                    </div>
                    <div>
                      <div className="font-bold text-slate-900">Finish the essentials</div>
                      <div className="text-xs font-semibold text-slate-500 mt-0.5">Action needed: account selected.</div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-start gap-3">
                      <div className="w-4 h-4 rounded-full bg-slate-100 flex items-center justify-center mt-0.5">
                        <svg className="w-2.5 h-2.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3"><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/></svg>
                      </div>
                      <span className="text-sm font-semibold text-slate-500">Account selected</span>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="w-4 h-4 rounded-full bg-[#e8f5e9] flex items-center justify-center mt-0.5">
                        <svg className="w-2.5 h-2.5 text-[#00b050]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3"><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/></svg>
                      </div>
                      <span className="text-sm font-semibold text-slate-700">Caption is within platform limits</span>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="w-4 h-4 rounded-full bg-[#e8f5e9] flex items-center justify-center mt-0.5">
                        <svg className="w-2.5 h-2.5 text-[#00b050]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3"><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/></svg>
                      </div>
                      <span className="text-sm font-semibold text-slate-700">Format is supported by selected accounts</span>
                    </div>
                  </div>
                </div>

                {/* Mobile Preview */}
                <div className="border-[8px] border-slate-900 rounded-[2.5rem] overflow-hidden bg-white shadow-xl h-[600px] flex flex-col relative">
                  {/* Phone Notch/Top bar */}
                  <div className="bg-[#0f2e27] text-white px-5 py-3 flex justify-between items-center text-xs font-bold">
                    <div className="flex items-center gap-1"><div className="w-1.5 h-1.5 rounded-full bg-emerald-400"/> Live glance</div>
                    <div>MBG Postings</div>
                  </div>
                  
                  {/* Post Content */}
                  <div className="flex-1 p-4 flex flex-col">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-10 h-10 rounded-full bg-[#a8e6cf] flex items-center justify-center text-emerald-800 font-bold text-lg">M</div>
                      <div>
                        <div className="font-bold text-sm text-slate-900">MBG Postings</div>
                        <div className="text-xs text-slate-500">Just now</div>
                      </div>
                    </div>
                    
                    <div className="text-[15px] text-slate-800 mb-4 whitespace-pre-wrap font-sans">
                      {caption || "Your caption will appear here as you type."}
                    </div>

                    <div className="flex-1 bg-[#f0f9f5] rounded-xl flex items-center justify-center text-sm font-semibold text-[#4e9c81] p-4 text-center">
                      Selected image or video will appear here.
                    </div>
                  </div>

                  {/* Phone Bottom bar */}
                  <div className="h-12 border-t border-slate-100 flex items-center justify-around text-slate-400">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/></svg>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/></svg>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"/></svg>
                  </div>
                </div>

              </div>
            </div>

          </div>
        )}

        {/* Other tabs dummy content */}
        {!["Overview", "Create post"].includes(activeTab) && (
          <div className="py-20 text-center text-slate-500 font-semibold">
            {activeTab} content will appear here.
          </div>
        )}

      </div>
    </div>
  );
}

function RefreshCwIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
      <path d="M3 3v5h5" />
      <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" />
      <path d="M16 21v-5h5" />
    </svg>
  );
}
