"use client";

import React, { useState } from "react";
import Image from "next/image";

export function Testimonials() {
  const [activeSlide, setActiveSlide] = useState(0);

  const testimonials = [
    {
      quote:
        "Omni has completely transformed how we handle customer conversations. Our response time is faster, our team is more productive and our sales have significantly increased.",
      name: "Rahul Sharma",
      role: "Founder, NextGen Store",
      avatar: "/images/rahul.jpg",
    },
    {
      quote:
        "Switching our WhatsApp and Instagram support to Omni was the best decision we made. We closed 40% more inbound leads in the first month alone.",
      name: "Pooja Verma",
      role: "Head of Growth, Urban Aura",
      avatar: "/images/rahul.jpg",
    },
    {
      quote:
        "The automated workflows and multi-agent assignment cut our response time from hours to seconds. Omni gives us enterprise-grade communication at startup speed.",
      name: "Karan Singhania",
      role: "COO, Zenith Logistics",
      avatar: "/images/rahul.jpg",
    },
  ];

  const current = testimonials[activeSlide];

  return (
    <section className="w-full py-20 sm:py-24 lg:py-28 bg-[#FAFBFF] text-[#101633] relative overflow-hidden border-t border-[#ECE8FB]/60">
      {/* Abstract organic background shapes */}
      {/* 1. Large translucent lavender/blue organic shape on the left */}
      <div className="pointer-events-none absolute -left-28 top-1/2 -translate-y-1/2 w-[460px] h-[460px] lg:w-[540px] lg:h-[540px] rounded-full bg-gradient-to-br from-[#E6DEFF]/75 via-[#EAF1FF]/65 to-transparent blur-3xl opacity-80" />
      {/* Subtle organic contour ring on left */}
      <div className="pointer-events-none absolute -left-16 top-1/2 -translate-y-1/2 w-[400px] h-[400px] rounded-full border border-[#D9D3FA]/50 opacity-60 hidden sm:block" />

      {/* 2. Soft translucent wave shape entering from right edge */}
      <div className="pointer-events-none absolute -right-24 top-10 w-[420px] h-[420px] rounded-full bg-gradient-to-bl from-[#E3EDFF]/70 via-[#EAE5FF]/55 to-transparent blur-3xl opacity-80" />


      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-10 items-center">
          {/* Left Column: Results copy & metrics */}
          <div className="lg:col-span-6 flex flex-col items-start text-left">
            {/* Badge */}
            <div className="inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full bg-[#ECEBFF] border border-[#DDD9FF] text-[#5B43FF] text-[11px] font-bold tracking-wider uppercase mb-5">
              <span>REAL RESULTS</span>
            </div>

            {/* Heading */}
            <h2 className="text-3xl sm:text-4xl lg:text-[45px] font-extrabold text-[#101633] tracking-tight leading-[1.14] mb-5">
              Businesses grow <br />
              faster{" "}
              <span className="bg-gradient-to-r from-[#2875FF] to-[#5B43FF] bg-clip-text text-transparent">
                with Omni
              </span>
            </h2>

            {/* Supporting description */}
            <p className="text-[15px] sm:text-[15.5px] text-[#586887] leading-relaxed mb-7 max-w-lg font-normal">
              Join hundreds of businesses that are saving time, reducing manual work, and creating better customer experiences with Omni.
            </p>

            {/* Thin Pale Lavender Divider */}
            <div className="w-full max-w-lg border-t border-[#E8E6FA] mb-7" />

            {/* Three Statistics in one horizontal row */}
            <div className="grid grid-cols-3 gap-6 sm:gap-8 w-full max-w-lg">
              <div>
                <div className="text-2xl sm:text-3xl lg:text-[34px] font-extrabold text-[#101633] tracking-tight">500+</div>
                <div className="text-xs sm:text-[13px] text-[#586887] font-medium mt-1">Active Businesses</div>
              </div>
              <div>
                <div className="text-2xl sm:text-3xl lg:text-[34px] font-extrabold text-[#101633] tracking-tight">1M+</div>
                <div className="text-xs sm:text-[13px] text-[#586887] font-medium mt-1">Conversations</div>
              </div>
              <div>
                <div className="text-2xl sm:text-3xl lg:text-[34px] font-extrabold text-[#101633] tracking-tight">99.9%</div>
                <div className="text-xs sm:text-[13px] text-[#586887] font-medium mt-1">Uptime</div>
              </div>
            </div>
          </div>

          {/* Right Column: Testimonial Card with flanking Carousel Arrows */}
          <div className="lg:col-span-6 flex items-center justify-center lg:justify-end">
            <div className="flex items-center gap-3 sm:gap-4 w-full max-w-[540px]">
              {/* Left Carousel Arrow Button */}
              <button
                type="button"
                onClick={() => setActiveSlide((prev) => (prev > 0 ? prev - 1 : testimonials.length - 1))}
                aria-label="Previous testimonial"
                className="w-10 h-10 sm:w-11 sm:h-11 rounded-full bg-white/95 hover:bg-white text-[#5B43FF] flex items-center justify-center shadow-md shadow-indigo-950/6 border border-[#E8E4FB] transition-all shrink-0 cursor-pointer hover:scale-105 active:scale-95"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
                </svg>
              </button>

              {/* Main White Testimonial Card */}
              <div className="flex-1 bg-white text-[#101633] rounded-[24px] p-7 sm:p-9 shadow-xl shadow-indigo-950/6 border border-[#ECE8FB] relative select-none">
                <p className="text-[14.5px] sm:text-[15.5px] text-[#1E2540] font-normal leading-[1.65] mb-5">
                  &ldquo;{current.quote}&rdquo;
                </p>

                {/* 5 Gold Stars */}
                <div className="flex items-center gap-1 text-amber-400 mb-6">
                  {[...Array(5)].map((_, i) => (
                    <svg key={i} className="w-4 h-4 fill-current" viewBox="0 0 20 20">
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                    </svg>
                  ))}
                </div>

                {/* Customer Info */}
                <div className="flex items-center gap-3.5 mb-6">
                  <div className="relative w-11 h-11 rounded-full overflow-hidden border border-slate-100 shrink-0">
                    <Image
                      src={current.avatar}
                      alt={current.name}
                      fill
                      className="object-cover"
                    />
                  </div>
                  <div>
                    <h4 className="font-bold text-[#101633] text-[15px] leading-tight">{current.name}</h4>
                    <p className="text-xs text-[#586887] font-normal mt-0.5">{current.role}</p>
                  </div>
                </div>

                {/* Pagination Indicators */}
                <div className="flex justify-center items-center gap-1.5">
                  {testimonials.map((_, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => setActiveSlide(i)}
                      aria-label={`Go to slide ${i + 1}`}
                      className={`h-1.5 rounded-full transition-all cursor-pointer ${
                        activeSlide === i ? "w-6 bg-[#5B43FF]" : "w-1.5 bg-[#DEDBF5] hover:bg-[#C8C4EE]"
                      }`}
                    />
                  ))}
                </div>
              </div>

              {/* Right Carousel Arrow Button */}
              <button
                type="button"
                onClick={() => setActiveSlide((prev) => (prev < testimonials.length - 1 ? prev + 1 : 0))}
                aria-label="Next testimonial"
                className="w-10 h-10 sm:w-11 sm:h-11 rounded-full bg-white/95 hover:bg-white text-[#5B43FF] flex items-center justify-center shadow-md shadow-indigo-950/6 border border-[#E8E4FB] transition-all shrink-0 cursor-pointer hover:scale-105 active:scale-95"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
