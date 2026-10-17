"use client";

import React from "react";
import Image from "next/image";
import { OmniLogo, WhatsAppIcon, InstagramIcon, MessengerIcon } from "./icons";

export function DashboardPreview() {
  return (
    <div className="relative mx-auto w-full max-w-[690px] rounded-2xl bg-white border border-slate-200/90 shadow-2xl shadow-indigo-950/15 overflow-hidden text-[11px] select-none font-sans">
      {/* Top Bar for Desktop window simulation */}
      <div className="flex h-[420px] sm:h-[450px]">
        {/* Dark Navy Sidebar */}
        <aside className="w-[125px] sm:w-[135px] bg-[#0c1229] p-3 text-slate-400 flex flex-col justify-between shrink-0 border-r border-slate-800/60">
          <div>
            {/* Logo */}
            <div className="flex items-center gap-2 mb-4 px-1">
              <Image
                src="/images/omniflow-symbol.png"
                alt="Omniflow"
                width={18}
                height={18}
                className="w-4.5 h-4.5 object-contain"
                unoptimized
              />
              <span className="text-white font-bold text-xs tracking-tight">Omniflow</span>
            </div>

            {/* Menu items */}
            <nav className="space-y-1 text-[10.5px]">
              <div className="flex items-center justify-between px-2 py-1.5 rounded-md bg-[#252a54] text-white font-medium shadow-sm">
                <div className="flex items-center gap-2">
                  <svg className="w-3.5 h-3.5 text-[#736bff]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                  </svg>
                  <span>Inbox</span>
                </div>
                <span className="bg-[#4B43FF] text-[9px] px-1.5 py-0.2 rounded-full font-bold">12</span>
              </div>

              <div className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:text-slate-200 cursor-pointer">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                <span>Customers</span>
              </div>

              <div className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:text-slate-200 cursor-pointer">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z" />
                </svg>
                <span>Broadcast</span>
              </div>

              <div className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:text-slate-200 cursor-pointer">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <span>Automation</span>
              </div>

              <div className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:text-slate-200 cursor-pointer">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                <span>Analytics</span>
              </div>

              <div className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:text-slate-200 cursor-pointer">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
                <span>Team</span>
              </div>

              <div className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:text-slate-200 cursor-pointer">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                </svg>
                <span>Integrations</span>
              </div>
            </nav>
          </div>

          <div className="pt-2 border-t border-slate-800/80">
            <div className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:text-slate-200 cursor-pointer">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <span>Settings</span>
            </div>
          </div>
        </aside>

        {/* Main Work Area */}
        <div className="flex-1 flex flex-col bg-[#fafbfe] min-w-0">
          {/* Top Header Bar */}
          <header className="h-10 border-b border-slate-200/80 px-3 bg-white flex items-center justify-between gap-3 shrink-0">
            <div className="flex-1 max-w-[240px] relative">
              <svg className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                type="text"
                readOnly
                placeholder="Search conversations..."
                className="w-full pl-8 pr-2 py-1 rounded-md bg-slate-100 text-[10px] text-slate-600 placeholder-slate-400 border-none outline-none"
              />
            </div>

            <div className="flex items-center gap-3">
              <div className="relative cursor-pointer text-slate-500">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                </svg>
                <span className="w-1.5 h-1.5 rounded-full bg-rose-500 absolute -top-0.5 -right-0.5" />
              </div>
              <div className="flex items-center gap-1.5 cursor-pointer">
                <div className="w-5 h-5 rounded-full bg-gradient-to-tr from-amber-400 to-amber-600 text-white font-bold text-[9px] flex items-center justify-center">
                  A
                </div>
                <span className="text-[10.5px] font-medium text-slate-700 hidden sm:inline">Aditi</span>
                <svg className="w-2.5 h-2.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </div>
          </header>

          {/* Two-Column Chat App Layout */}
          <div className="flex-1 flex min-h-0 overflow-hidden">
            {/* Conversation List Column */}
            <div className="w-[185px] sm:w-[210px] border-r border-slate-200/80 bg-white flex flex-col shrink-0">
              {/* Channel Filter Pills */}
              <div className="p-2 border-b border-slate-100 flex items-center gap-1 overflow-x-auto no-scrollbar">
                <span className="px-2 py-0.5 rounded-full bg-[#4B43FF] text-white text-[9.5px] font-semibold shrink-0 cursor-pointer">
                  All 44
                </span>
                <span className="px-2 py-0.5 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-600 text-[9.5px] flex items-center gap-1 shrink-0 cursor-pointer">
                  <WhatsAppIcon className="!w-2.5 !h-2.5" /> 6
                </span>
                <span className="px-2 py-0.5 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-600 text-[9.5px] flex items-center gap-1 shrink-0 cursor-pointer">
                  <InstagramIcon className="!w-2.5 !h-2.5" /> 3
                </span>
                <span className="px-2 py-0.5 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-600 text-[9.5px] flex items-center gap-1 shrink-0 cursor-pointer">
                  <MessengerIcon className="!w-2.5 !h-2.5" /> 2
                </span>
              </div>

              {/* Chat Thread List */}
              <div className="flex-1 overflow-y-auto divide-y divide-slate-100/70">
                {/* 1. Active: Rohit Sharma */}
                <div className="p-2 sm:p-2.5 bg-[#f3f4ff] border-l-2 border-[#4B43FF] cursor-pointer">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-1.5">
                      <div className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-800 font-bold text-[9px] flex items-center justify-center shrink-0">
                        RS
                      </div>
                      <div className="truncate">
                        <div className="flex items-center gap-1">
                          <span className="font-semibold text-slate-800 text-[10.5px]">Rohit Sharma</span>
                          <WhatsAppIcon className="!w-2.5 !h-2.5" />
                        </div>
                        <p className="text-[9.5px] text-slate-600 truncate font-medium">Hi, is this product available?</p>
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <span className="text-[8.5px] text-slate-400 block">10:24 AM</span>
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block mt-1" />
                    </div>
                  </div>
                </div>

                {/* 2. Priya Mehta */}
                <div className="p-2 sm:p-2.5 hover:bg-slate-50 cursor-pointer">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-1.5 truncate">
                      <div className="w-6 h-6 rounded-full bg-pink-100 text-pink-700 font-bold text-[9px] flex items-center justify-center shrink-0">
                        PM
                      </div>
                      <div className="truncate">
                        <div className="flex items-center gap-1">
                          <span className="font-medium text-slate-800 text-[10.5px]">Priya Mehta</span>
                          <InstagramIcon className="!w-2.5 !h-2.5" />
                        </div>
                        <p className="text-[9.5px] text-slate-500 truncate">Can you share the price?</p>
                      </div>
                    </div>
                    <span className="text-[8.5px] text-slate-400 shrink-0">10:14 AM</span>
                  </div>
                </div>

                {/* 3. Sneha Patil */}
                <div className="p-2 sm:p-2.5 hover:bg-slate-50 cursor-pointer">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-1.5 truncate">
                      <div className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 font-bold text-[9px] flex items-center justify-center shrink-0">
                        SP
                      </div>
                      <div className="truncate">
                        <div className="flex items-center gap-1">
                          <span className="font-medium text-slate-800 text-[10.5px]">Sneha Patil</span>
                          <WhatsAppIcon className="!w-2.5 !h-2.5" />
                        </div>
                        <p className="text-[9.5px] text-slate-500 truncate">Thanks! Order placed 🎉</p>
                      </div>
                    </div>
                    <span className="text-[8.5px] text-slate-400 shrink-0">Yesterday</span>
                  </div>
                </div>

                {/* 4. Aman Verma */}
                <div className="p-2 sm:p-2.5 hover:bg-slate-50 cursor-pointer">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-1.5 truncate">
                      <div className="w-6 h-6 rounded-full bg-sky-100 text-sky-700 font-bold text-[9px] flex items-center justify-center shrink-0">
                        AV
                      </div>
                      <div className="truncate">
                        <div className="flex items-center gap-1">
                          <span className="font-medium text-slate-800 text-[10.5px]">Aman Verma</span>
                          <MessengerIcon className="!w-2.5 !h-2.5" />
                        </div>
                        <p className="text-[9.5px] text-slate-500 truncate">I need bulk quantity.</p>
                      </div>
                    </div>
                    <span className="text-[8.5px] text-slate-400 shrink-0">Yesterday</span>
                  </div>
                </div>

                {/* 5. Karan Desai */}
                <div className="p-2 sm:p-2.5 hover:bg-slate-50 cursor-pointer">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-1.5 truncate">
                      <div className="w-6 h-6 rounded-full bg-amber-100 text-amber-700 font-bold text-[9px] flex items-center justify-center shrink-0">
                        KD
                      </div>
                      <div className="truncate">
                        <div className="flex items-center gap-1">
                          <span className="font-medium text-slate-800 text-[10.5px]">Karan Desai</span>
                          <InstagramIcon className="!w-2.5 !h-2.5" />
                        </div>
                        <p className="text-[9.5px] text-slate-500 truncate">When will it be delivered?</p>
                      </div>
                    </div>
                    <span className="text-[8.5px] text-slate-400 shrink-0">Oct 5</span>
                  </div>
                </div>

                {/* 6. Neha Gupta */}
                <div className="p-2 sm:p-2.5 hover:bg-slate-50 cursor-pointer">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-1.5 truncate">
                      <div className="w-6 h-6 rounded-full bg-purple-100 text-purple-700 font-bold text-[9px] flex items-center justify-center shrink-0">
                        NG
                      </div>
                      <div className="truncate">
                        <div className="flex items-center gap-1">
                          <span className="font-medium text-slate-800 text-[10.5px]">Neha Gupta</span>
                          <WhatsAppIcon className="!w-2.5 !h-2.5" />
                        </div>
                        <p className="text-[9.5px] text-slate-500 truncate">Can you share catalog?</p>
                      </div>
                    </div>
                    <span className="text-[8.5px] text-slate-400 shrink-0">Oct 4</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Active Conversation Detail Pane */}
            <div className="flex-1 flex flex-col bg-[#f8f9fd] min-w-0">
              {/* Chat Thread Header */}
              <div className="h-10 border-b border-slate-200/80 bg-white px-3 flex items-center justify-between shrink-0">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-800 font-bold text-[9px] flex items-center justify-center">
                    RS
                  </div>
                  <div>
                    <div className="flex items-center gap-1">
                      <span className="font-semibold text-slate-800 text-[10.5px]">Rohit Sharma</span>
                      <WhatsAppIcon className="!w-2.5 !h-2.5" />
                    </div>
                    <span className="text-[8.5px] text-emerald-600 font-medium block -mt-0.5">Online</span>
                  </div>
                </div>

                <div className="flex items-center gap-2.5 text-slate-500">
                  <svg className="w-3.5 h-3.5 cursor-pointer hover:text-slate-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                  </svg>
                  <svg className="w-3.5 h-3.5 cursor-pointer hover:text-slate-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                  </svg>
                </div>
              </div>

              {/* Chat Messages */}
              <div className="flex-1 p-3 space-y-2.5 overflow-y-auto">
                {/* Incoming Message */}
                <div className="flex flex-col items-start max-w-[82%]">
                  <div className="bg-white text-slate-800 px-2.5 py-1.5 rounded-xl rounded-tl-sm shadow-sm border border-slate-100 text-[10px]">
                    Hi, is this product available?
                  </div>
                  <span className="text-[8.5px] text-slate-400 mt-0.5 ml-1">10:20 AM</span>
                </div>

                {/* Outgoing Message */}
                <div className="flex flex-col items-end max-w-[85%] ml-auto">
                  <div className="bg-[#4B43FF] text-white px-2.5 py-1.5 rounded-xl rounded-tr-sm shadow-sm text-[10px]">
                    Yes! It's available. Would you like to see the details?
                  </div>
                  <div className="flex items-center gap-1 text-[8.5px] text-slate-400 mt-0.5 mr-1">
                    <span>10:21 AM</span>
                    <span className="text-indigo-600 font-bold">✓✓</span>
                  </div>
                </div>

                {/* In-chat Product Card */}
                <div className="max-w-[210px] ml-auto bg-white rounded-xl border border-slate-200/90 shadow-sm p-2">
                  <div className="relative w-full h-16 bg-slate-50 rounded-lg overflow-hidden flex items-center justify-center mb-1.5">
                    <Image
                      src="/images/sneaker.jpg"
                      alt="Nike Air Max 270"
                      width={120}
                      height={70}
                      className="object-contain"
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-semibold text-slate-900 text-[10px] leading-tight">Nike Air Max 270</h4>
                      <p className="text-[10px] font-bold text-[#4B43FF]">₹12,495</p>
                    </div>
                    <button className="px-2 py-0.5 rounded bg-indigo-50 text-[#4B43FF] hover:bg-indigo-100 font-semibold text-[9px] transition-colors">
                      View Product
                    </button>
                  </div>
                </div>

                {/* Incoming Message */}
                <div className="flex flex-col items-start max-w-[82%]">
                  <div className="bg-white text-slate-800 px-2.5 py-1.5 rounded-xl rounded-tl-sm shadow-sm border border-slate-100 text-[10px]">
                    Great! How long will delivery take?
                  </div>
                  <span className="text-[8.5px] text-slate-400 mt-0.5 ml-1">10:24 AM</span>
                </div>
              </div>

              {/* Composer Input Bar */}
              <div className="p-2 bg-white border-t border-slate-200/80 flex items-center gap-2 shrink-0">
                <input
                  type="text"
                  readOnly
                  placeholder="Type a message..."
                  className="flex-1 bg-slate-100/80 px-2.5 py-1 rounded-full text-[10px] text-slate-700 placeholder-slate-400 outline-none"
                />
                <button className="text-slate-400 hover:text-slate-600 p-1">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                  </svg>
                </button>
                <button className="text-slate-400 hover:text-slate-600 p-1">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </button>
                <button className="w-6 h-6 rounded-full bg-[#4B43FF] text-white flex items-center justify-center shrink-0 shadow-sm hover:bg-[#3D35E6]">
                  <svg className="w-3 h-3 fill-current rotate-90" viewBox="0 0 20 20">
                    <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
