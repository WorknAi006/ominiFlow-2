"use client";

import React, { useState } from "react";
import Link from "next/link";
import Image from "next/image";

export function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full bg-white/95 backdrop-blur-md border-b border-slate-100/80 transition-all">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
        {/* Brand */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <Image
            src="/images/omniflow-logo.png"
            alt="Omniflow"
            width={145}
            height={36}
            className="h-8 sm:h-9 w-auto object-contain"
            priority
            unoptimized
          />
        </Link>

        {/* Desktop Nav Links */}
        <nav className="hidden md:flex items-center gap-8 text-[14.5px] font-medium text-[#475569]">
          <Link href="#features" className="hover:text-[#4B43FF] transition-colors">
            Features
          </Link>
          <Link href="#channels" className="hover:text-[#4B43FF] transition-colors">
            Channels
          </Link>
          <Link href="#pricing" className="hover:text-[#4B43FF] transition-colors">
            Pricing
          </Link>
          <Link href="#integrations" className="hover:text-[#4B43FF] transition-colors">
            Integrations
          </Link>
          <div className="relative group cursor-pointer flex items-center gap-1 hover:text-[#4B43FF] transition-colors">
            <span>Resources</span>
            <svg className="w-3.5 h-3.5 transition-transform group-hover:rotate-180 text-slate-400 group-hover:text-[#4B43FF]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </nav>

        {/* Right Actions */}
        <div className="hidden md:flex items-center gap-6">
          <Link
            href="/login"
            className="text-[14.5px] font-semibold text-[#11172F] hover:text-[#4B43FF] transition-colors"
          >
            Login
          </Link>
          <Link
            href="/login"
            className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-lg bg-[#4B43FF] hover:bg-[#3D35E6] text-white text-[14px] font-semibold shadow-md shadow-[#4B43FF]/25 hover:shadow-lg hover:shadow-[#4B43FF]/30 transition-all"
          >
            <span>Get Started Free</span>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </Link>
        </div>

        {/* Mobile menu toggle */}
        <div className="flex md:hidden items-center">
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              {mobileMenuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b border-slate-200 bg-white px-4 pt-3 pb-6 space-y-3">
          <Link href="#features" onClick={() => setMobileMenuOpen(false)} className="block py-2 text-sm font-medium text-slate-700">Features</Link>
          <Link href="#channels" onClick={() => setMobileMenuOpen(false)} className="block py-2 text-sm font-medium text-slate-700">Channels</Link>
          <Link href="#pricing" onClick={() => setMobileMenuOpen(false)} className="block py-2 text-sm font-medium text-slate-700">Pricing</Link>
          <Link href="#integrations" onClick={() => setMobileMenuOpen(false)} className="block py-2 text-sm font-medium text-slate-700">Integrations</Link>
          <div className="pt-4 border-t border-slate-100 flex flex-col gap-3">
            <Link href="/login" className="text-center py-2 text-sm font-semibold text-slate-800">Login</Link>
            <Link href="/login" className="text-center py-2.5 rounded-lg bg-[#4B43FF] text-white text-sm font-semibold">Get Started Free →</Link>
          </div>
        </div>
      )}
    </header>
  );
}
