import React from "react";

export function BrandRow() {
  return (
    <section className="py-10 border-y border-slate-100 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <p className="text-xs sm:text-[13px] font-semibold text-slate-500 uppercase tracking-wider mb-7">
          Trusted by 500+ growing businesses
        </p>

        <div className="flex flex-wrap items-center justify-center gap-8 sm:gap-14 lg:gap-20 opacity-90 grayscale-[25%] hover:grayscale-0 transition-all">
          {/* boAt */}
          <div className="flex items-center gap-1 font-black text-xl tracking-tighter text-[#11172F]">
            <span>bo</span>
            <span className="text-[#E31837] text-2xl font-black">A</span>
            <span>t</span>
          </div>

          {/* mamaearth */}
          <div className="flex items-center font-bold text-lg tracking-tight text-[#009270]">
            <span>mama</span>
            <span className="text-[#7CB342]">earth</span>
          </div>

          {/* zepto */}
          <div className="font-extrabold text-xl tracking-tighter text-[#E91E63]">
            zepto
          </div>

          {/* blinkit */}
          <div className="px-3 py-1 rounded-md bg-[#F8CB46] text-[#11172F] font-black text-sm tracking-tight shadow-xs">
            blink<span className="text-[#0C831F]">it</span>
          </div>

          {/* Sugar Cosmetics */}
          <div className="flex items-center gap-1.5 font-bold text-xs tracking-wider uppercase text-slate-800">
            <span className="w-5 h-5 rounded-full border border-slate-900 flex items-center justify-center font-black text-[10px]">S</span>
            <span>SUGAR</span>
          </div>

          {/* CRED */}
          <div className="flex items-center gap-1.5 font-extrabold text-base tracking-widest text-[#11172F]">
            <div className="w-4 h-4 border-2 border-[#11172F] rounded-xs" />
            <span>CRED</span>
          </div>
        </div>
      </div>
    </section>
  );
}
