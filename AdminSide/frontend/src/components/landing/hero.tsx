"use client";

import React from "react";
import Link from "next/link";
import { DashboardPreview } from "./dashboard-preview";

export function Hero() {
  return (
    <section className="relative pt-10 sm:pt-14 pb-16 sm:pb-24 overflow-hidden bg-gradient-to-b from-[#FAFBFF] via-white to-[#FAFBFF]">
      {/* Decorative gradient glow background */}
      <div className="absolute top-0 right-1/4 -z-10 w-[600px] h-[500px] bg-indigo-100/40 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-20 left-10 -z-10 w-[450px] h-[450px] bg-purple-100/30 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
          {/* Left Content Column */}
          <div className="lg:col-span-5 flex flex-col items-start text-left">
            {/* Pill Badge */}
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#ECEBFF] border border-[#DDD9FF] text-[#4B43FF] text-xs font-semibold mb-6">
              <span>All your conversations. In one place.</span>
            </div>

            {/* Giant Title */}
            <h1 className="text-4xl sm:text-5xl lg:text-[56px] xl:text-[60px] font-extrabold text-[#11172F] tracking-tight leading-[1.08] mb-5">
              Omnichannel <br />
              Messaging <br />
              <span className="bg-gradient-to-r from-[#4B43FF] via-[#635BFF] to-[#867DFF] bg-clip-text text-transparent">
                Made Simple.
              </span>
            </h1>

            {/* Subtitle */}
            <p className="text-[15.5px] sm:text-[16px] text-[#475569] leading-relaxed max-w-lg mb-8">
              Omni helps businesses manage customer conversations, automate workflows, and grow sales across WhatsApp, Instagram, Facebook, Telegram and more — all from one powerful platform.
            </p>

            {/* Action Buttons */}
            <div className="flex flex-wrap items-center gap-3.5 mb-8 w-full sm:w-auto">
              <Link
                href="/login"
                className="inline-flex items-center justify-center gap-2 px-6 sm:px-7 py-3 rounded-lg bg-[#4B43FF] hover:bg-[#3D35E6] text-white text-[14.5px] font-semibold shadow-lg shadow-[#4B43FF]/25 hover:shadow-xl hover:shadow-[#4B43FF]/30 transition-all"
              >
                <span>Get Started Free</span>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
              </Link>
              <button
                type="button"
                className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-white hover:bg-slate-50 text-[#11172F] text-[14.5px] font-semibold border border-slate-200 shadow-sm transition-all"
              >
                <div className="w-5 h-5 rounded-full border border-slate-300 flex items-center justify-center text-slate-700">
                  <svg className="w-2.5 h-2.5 fill-current ml-0.5" viewBox="0 0 24 24">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                </div>
                <span>Watch Demo</span>
              </button>
            </div>

            {/* Trust points */}
            <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-[12.5px] font-medium text-[#475569]">
              <div className="flex items-center gap-1.5">
                <svg className="w-4 h-4 text-[#4B43FF]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
                <span>No Credit Card</span>
              </div>
              <div className="flex items-center gap-1.5">
                <svg className="w-4 h-4 text-[#4B43FF]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
                <span>Easy Setup</span>
              </div>
              <div className="flex items-center gap-1.5">
                <svg className="w-4 h-4 text-[#4B43FF]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
                <span>Trusted by Businesses</span>
              </div>
            </div>
          </div>

          {/* Right Column: Dashboard Preview */}
          <div className="lg:col-span-7 flex justify-center lg:justify-end">
            <DashboardPreview />
          </div>
        </div>
      </div>
    </section>
  );
}
