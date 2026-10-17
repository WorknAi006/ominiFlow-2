import React from "react";
import Link from "next/link";

export function Features() {
  return (
    <section id="features" className="py-20 sm:py-28 bg-[#FAFBFF] relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
          {/* Left Column */}
          <div className="lg:col-span-5 flex flex-col items-start text-left">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#ECEBFF] border border-[#DDD9FF] text-[#4B43FF] text-xs font-semibold mb-5">
              <span>WHY OMNI</span>
            </div>

            <h2 className="text-3xl sm:text-4xl lg:text-[42px] font-extrabold text-[#11172F] tracking-tight leading-[1.15] mb-5">
              Everything you need <br />
              to manage customer <br />
              conversations.
            </h2>

            <p className="text-[15.5px] text-[#475569] leading-relaxed mb-8 max-w-md">
              From sales and support to marketing, Omni brings all your channels, tools, and team together so you can focus on what really matters — your customers.
            </p>

            <Link
              href="/login"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-[#4B43FF] hover:bg-[#3D35E6] text-white text-[14px] font-semibold shadow-md shadow-[#4B43FF]/20 transition-all"
            >
              <span>Explore Features</span>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </Link>
          </div>

          {/* Right Column: 2x2 Grid */}
          <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-5">
            {/* Card 1: Unified Inbox */}
            <div className="bg-white rounded-2xl p-6 sm:p-7 border border-slate-100 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between">
              <div>
                <div className="w-11 h-11 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center mb-5">
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </div>
                <h3 className="text-base font-bold text-[#11172F] mb-2">Unified Inbox</h3>
                <p className="text-[13.5px] text-slate-500 leading-relaxed">
                  Manage WhatsApp, Instagram, Facebook, Telegram and more from a single inbox.
                </p>
              </div>
            </div>

            {/* Card 2: Automation */}
            <div className="bg-white rounded-2xl p-6 sm:p-7 border border-slate-100 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between">
              <div>
                <div className="w-11 h-11 rounded-xl bg-indigo-50 text-[#4B43FF] flex items-center justify-center mb-5">
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <h3 className="text-base font-bold text-[#11172F] mb-2">Automation</h3>
                <p className="text-[13.5px] text-slate-500 leading-relaxed">
                  Automate replies, assign chats, and streamline workflows.
                </p>
              </div>
            </div>

            {/* Card 3: Team Collaboration */}
            <div className="bg-white rounded-2xl p-6 sm:p-7 border border-slate-100 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between">
              <div>
                <div className="w-11 h-11 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center mb-5">
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                </div>
                <h3 className="text-base font-bold text-[#11172F] mb-2">Team Collaboration</h3>
                <p className="text-[13.5px] text-slate-500 leading-relaxed">
                  Work together, assign conversations and track performance.
                </p>
              </div>
            </div>

            {/* Card 4: Powerful Analytics */}
            <div className="bg-white rounded-2xl p-6 sm:p-7 border border-slate-100 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between">
              <div>
                <div className="w-11 h-11 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center mb-5">
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <h3 className="text-base font-bold text-[#11172F] mb-2">Powerful Analytics</h3>
                <p className="text-[13.5px] text-slate-500 leading-relaxed">
                  Get insights on response time, customer engagement and revenue growth.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
