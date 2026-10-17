import React from "react";
import Link from "next/link";

export function CtaBanner() {
  return (
    <section className="w-full relative py-20 sm:py-24 lg:py-28 bg-[#FAFBFF] text-[#101633] overflow-hidden border-t border-[#ECE8FB]/60">
      {/* Abstract organic background shapes */}
      {/* 1. Large translucent lavender/blue organic shape on bottom-left */}
      <div className="pointer-events-none absolute -left-20 -bottom-20 w-[440px] h-[440px] rounded-full bg-gradient-to-tr from-[#E6DEFF]/75 via-[#EAF1FF]/60 to-transparent blur-3xl opacity-80" />
      <div className="pointer-events-none absolute -left-10 bottom-0 w-[360px] h-[360px] rounded-full border border-[#D9D3FA]/40 opacity-50 hidden sm:block" />

      {/* 2. Soft translucent wave shape entering from right edge */}
      <div className="pointer-events-none absolute -right-20 top-1/2 -translate-y-1/2 w-[380px] h-[380px] rounded-full bg-gradient-to-bl from-[#E3EDFF]/70 via-[#EAE5FF]/55 to-transparent blur-3xl opacity-80" />


      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
        {/* Heading */}
        <h2 className="text-3xl sm:text-4xl lg:text-[42px] font-extrabold text-[#101633] tracking-tight mb-4 leading-[1.18]">
          Ready to simplify{" "}
          <span className="bg-gradient-to-r from-[#2875FF] to-[#5B43FF] bg-clip-text text-transparent">
            customer conversations?
          </span>
        </h2>

        {/* Supporting description */}
        <p className="text-[15px] sm:text-[15.5px] text-[#586887] max-w-xl mx-auto mb-8 leading-relaxed font-normal">
          Join Omni today and see how easy it is to manage, automate and grow your business.
        </p>

        {/* Primary and Secondary CTA Buttons */}
        <div className="flex flex-wrap items-center justify-center gap-3.5">
          <Link
            href="/login"
            className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl bg-gradient-to-r from-[#2875FF] to-[#5B43FF] hover:opacity-95 text-white text-[14.5px] font-semibold shadow-lg shadow-[#5B43FF]/25 hover:shadow-xl hover:shadow-[#5B43FF]/30 transition-all cursor-pointer"
          >
            <span>Get Started Free</span>
            <span className="text-base leading-none">→</span>
          </Link>

          <button
            type="button"
            className="px-7 py-3.5 rounded-xl bg-white hover:bg-slate-50 text-[#101633] text-[14.5px] font-semibold border border-[#E2DEF8] shadow-sm hover:shadow transition-all cursor-pointer"
          >
            Contact Sales
          </button>
        </div>
      </div>
    </section>
  );
}
