"use client";

import React, { useState } from "react";
import Link from "next/link";

export function Pricing() {
  const [isYearly, setIsYearly] = useState(false);

  return (
    <section id="pricing" className="py-20 sm:py-28 bg-[#FAFBFF] relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        {/* Badge */}
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#ECEBFF] border border-[#DDD9FF] text-[#4B43FF] text-xs font-semibold mb-4">
          <span>SIMPLE PRICING</span>
        </div>

        {/* Heading */}
        <h2 className="text-3xl sm:text-4xl font-extrabold text-[#11172F] tracking-tight mb-3">
          Choose a plan that fits your business
        </h2>

        {/* Subtitle */}
        <p className="text-[15px] text-[#475569] max-w-xl mx-auto mb-9">
          Start free and upgrade anytime. No hidden charges.
        </p>

        {/* Monthly / Yearly Toggle */}
        <div className="inline-flex items-center bg-slate-100 p-1 rounded-xl mb-14 border border-slate-200">
          <button
            onClick={() => setIsYearly(false)}
            className={`px-5 py-2 rounded-lg text-xs font-semibold transition-all ${
              !isYearly ? "bg-[#4B43FF] text-white shadow-sm" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Monthly
          </button>
          <button
            onClick={() => setIsYearly(true)}
            className={`px-5 py-2 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              isYearly ? "bg-[#4B43FF] text-white shadow-sm" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <span>Yearly</span>
            <span className={`text-[10px] px-1.5 py-0.2 rounded font-bold ${isYearly ? "bg-white/20 text-white" : "bg-emerald-100 text-emerald-800"}`}>
              Save 20%
            </span>
          </button>
        </div>

        {/* Pricing Cards Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-stretch max-w-6xl mx-auto">
          {/* Card 1: Starter */}
          <div className="bg-white rounded-3xl p-8 border border-slate-200/90 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between text-left">
            <div>
              <h3 className="text-xl font-bold text-[#11172F]">Starter</h3>
              <p className="text-xs text-slate-500 mt-1 mb-6">For small businesses</p>

              <div className="flex items-baseline gap-1 mb-7">
                <span className="text-4xl font-extrabold text-[#11172F]">₹0</span>
                <span className="text-xs font-medium text-slate-400">/month</span>
              </div>

              <div className="space-y-3.5 mb-8 text-[13.5px] text-slate-700">
                <div className="flex items-center gap-2.5">
                  <div className="w-4 h-4 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
                    <svg className="w-3 h-3 stroke-[2.5]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <span>1 user</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <div className="w-4 h-4 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
                    <svg className="w-3 h-3 stroke-[2.5]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <span>All messaging channels</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <div className="w-4 h-4 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
                    <svg className="w-3 h-3 stroke-[2.5]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <span>Basic automation</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <div className="w-4 h-4 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
                    <svg className="w-3 h-3 stroke-[2.5]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <span>Analytics (basic)</span>
                </div>
              </div>
            </div>

            <Link
              href="/login"
              className="w-full py-3 rounded-xl border border-slate-300 hover:border-slate-400 text-[#11172F] font-semibold text-xs text-center block transition-colors"
            >
              Get Started
            </Link>
          </div>

          {/* Card 2: Growth (Most Popular) */}
          <div className="bg-white rounded-3xl p-8 border-2 border-[#4B43FF] shadow-xl shadow-indigo-950/10 hover:shadow-2xl transition-all relative flex flex-col justify-between text-left lg:-translate-y-2">
            {/* Most Popular Badge */}
            <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-[#4B43FF] text-white text-[10.5px] font-bold tracking-wide uppercase shadow-sm">
              Most Popular
            </div>

            <div>
              <h3 className="text-xl font-bold text-[#11172F]">Growth</h3>
              <p className="text-xs text-slate-500 mt-1 mb-6">For growing teams</p>

              <div className="flex items-baseline gap-1 mb-7">
                <span className="text-4xl font-extrabold text-[#11172F]">
                  {isYearly ? "₹1,599" : "₹1,999"}
                </span>
                <span className="text-xs font-medium text-slate-400">/month</span>
              </div>

              <div className="space-y-3.5 mb-8 text-[13.5px] text-slate-700">
                <div className="flex items-center gap-2.5">
                  <div className="w-4 h-4 rounded-full bg-indigo-50 text-[#4B43FF] flex items-center justify-center shrink-0">
                    <svg className="w-3 h-3 stroke-[2.5]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <span>5 users</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <div className="w-4 h-4 rounded-full bg-indigo-50 text-[#4B43FF] flex items-center justify-center shrink-0">
                    <svg className="w-3 h-3 stroke-[2.5]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <span>Advanced automation</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <div className="w-4 h-4 rounded-full bg-indigo-50 text-[#4B43FF] flex items-center justify-center shrink-0">
                    <svg className="w-3 h-3 stroke-[2.5]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <span>Analytics (advanced)</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <div className="w-4 h-4 rounded-full bg-indigo-50 text-[#4B43FF] flex items-center justify-center shrink-0">
                    <svg className="w-3 h-3 stroke-[2.5]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <span>Priority support</span>
                </div>
              </div>
            </div>

            <Link
              href="/login"
              className="w-full py-3 rounded-xl bg-[#4B43FF] hover:bg-[#3D35E6] text-white font-semibold text-xs text-center block shadow-md shadow-[#4B43FF]/25 transition-all"
            >
              Get Started
            </Link>
          </div>

          {/* Card 3: Business */}
          <div className="bg-white rounded-3xl p-8 border border-slate-200/90 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between text-left">
            <div>
              <h3 className="text-xl font-bold text-[#11172F]">Business</h3>
              <p className="text-xs text-slate-500 mt-1 mb-6">For large teams</p>

              <div className="flex items-baseline gap-1 mb-7">
                <span className="text-3xl sm:text-4xl font-extrabold text-[#11172F]">Custom Pricing</span>
              </div>

              <div className="space-y-3.5 mb-8 text-[13.5px] text-slate-700">
                <div className="flex items-center gap-2.5">
                  <div className="w-4 h-4 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
                    <svg className="w-3 h-3 stroke-[2.5]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <span>Unlimited users</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <div className="w-4 h-4 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
                    <svg className="w-3 h-3 stroke-[2.5]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <span>Custom integrations</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <div className="w-4 h-4 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
                    <svg className="w-3 h-3 stroke-[2.5]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <span>Dedicated account manager</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <div className="w-4 h-4 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
                    <svg className="w-3 h-3 stroke-[2.5]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <span>Enterprise security</span>
                </div>
              </div>
            </div>

            <button
              type="button"
              className="w-full py-3 rounded-xl border border-slate-300 hover:border-slate-400 text-[#11172F] font-semibold text-xs text-center block transition-colors"
            >
              Contact Sales
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
