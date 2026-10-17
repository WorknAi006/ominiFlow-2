import React from "react";
import Image from "next/image";
import Link from "next/link";
import { WhatsAppIcon, InstagramIcon, MessengerIcon } from "./icons";

export function Workflow() {
  return (
    <section id="channels" className="py-20 sm:py-28 bg-white relative overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-16 lg:gap-12 items-center">
          {/* Left Visual Composition */}
          <div className="lg:col-span-6 relative flex justify-center">
            {/* Background subtle glow */}
            <div className="absolute inset-0 bg-indigo-50/40 rounded-full blur-3xl -z-10 scale-95" />

            <div className="relative w-full max-w-[530px] aspect-[1024/938] flex items-center justify-center">
              <Image
                src="/images/girl-channels.png"
                alt="Manage all channels in one place"
                fill
                unoptimized
                priority
                className="object-contain select-none"
              />
            </div>
          </div>

          {/* Right Text Column */}
          <div className="lg:col-span-6 flex flex-col items-start text-left lg:pl-6">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#ECEBFF] border border-[#DDD9FF] text-[#4B43FF] text-xs font-semibold mb-5">
              <span>WORK SMARTER</span>
            </div>

            <h2 className="text-3xl sm:text-4xl lg:text-[42px] font-extrabold text-[#11172F] tracking-tight leading-[1.15] mb-5">
              Turn Conversations <br />
              into Customers.
            </h2>

            <p className="text-[15.5px] text-[#475569] leading-relaxed mb-8 max-w-lg">
              Respond faster, automate repetitive tasks, and never miss a customer. Omni helps you deliver better support and drive more sales across every channel.
            </p>

            {/* Checklist */}
            <div className="space-y-3.5 mb-9">
              <div className="flex items-center gap-3">
                <div className="w-5 h-5 rounded-full bg-indigo-50 border border-indigo-200 text-[#4B43FF] flex items-center justify-center shrink-0">
                  <svg className="w-3 h-3 stroke-[3]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <span className="text-sm font-semibold text-[#11172F]">Faster response time</span>
              </div>

              <div className="flex items-center gap-3">
                <div className="w-5 h-5 rounded-full bg-indigo-50 border border-indigo-200 text-[#4B43FF] flex items-center justify-center shrink-0">
                  <svg className="w-3 h-3 stroke-[3]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <span className="text-sm font-semibold text-[#11172F]">Improve customer satisfaction</span>
              </div>

              <div className="flex items-center gap-3">
                <div className="w-5 h-5 rounded-full bg-indigo-50 border border-indigo-200 text-[#4B43FF] flex items-center justify-center shrink-0">
                  <svg className="w-3 h-3 stroke-[3]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <span className="text-sm font-semibold text-[#11172F]">Increase sales & conversions</span>
              </div>

              <div className="flex items-center gap-3">
                <div className="w-5 h-5 rounded-full bg-indigo-50 border border-indigo-200 text-[#4B43FF] flex items-center justify-center shrink-0">
                  <svg className="w-3 h-3 stroke-[3]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <span className="text-sm font-semibold text-[#11172F]">Scale with automation</span>
              </div>
            </div>

            <Link
              href="/login"
              className="inline-flex items-center gap-2 px-7 py-3 rounded-lg bg-[#4B43FF] hover:bg-[#3D35E6] text-white text-[14.5px] font-semibold shadow-lg shadow-[#4B43FF]/25 transition-all"
            >
              <span>Get Started Free</span>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
