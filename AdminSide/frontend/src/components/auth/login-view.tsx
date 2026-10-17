"use client";

import React, { useState, useEffect, FormEvent } from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { validateLogin } from "@/lib/auth/validation";
import {
  WhatsAppIcon,
  InstagramIcon,
  MessengerIcon,
  TelegramIcon,
} from "@/components/landing/icons";

export function OmniflowSymbol({ className = "w-8 h-8" }: { className?: string }) {
  return (
    <Image
      src="/images/omniflow-symbol.png"
      alt="Omniflow"
      width={36}
      height={36}
      className={`${className} object-contain`}
      unoptimized
    />
  );
}

export function OmniflowLogo({
  className = "h-8",
}: {
  className?: string;
  symbolSize?: string;
  textSize?: string;
}) {
  return (
    <Link href="/" className={`inline-flex items-center gap-2.5 ${className}`}>
      <Image
        src="/images/omniflow-logo.png"
        alt="Omniflow"
        width={140}
        height={35}
        className="h-7 sm:h-8 w-auto object-contain"
        priority
        unoptimized
      />
    </Link>
  );
}

interface LoginViewProps {
  destination: string;
  registered?: boolean;
  sessionExpired?: boolean;
}

export function LoginView({
  destination,
  registered = false,
  sessionExpired = false,
}: LoginViewProps) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [forgotNotice, setForgotNotice] = useState(false);

  useEffect(() => {
    const prevHtmlOverflow = document.documentElement.style.overflow;
    const prevBodyOverflow = document.body.style.overflow;
    document.documentElement.style.overflow = "hidden";
    document.body.style.overflow = "hidden";
    return () => {
      document.documentElement.style.overflow = prevHtmlOverflow;
      document.body.style.overflow = prevBodyOverflow;
    };
  }, []);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setForgotNotice(false);

    const validationError = validateLogin(email, password);
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      const payload = (await response.json().catch(() => ({}))) as {
        error?: string;
        success?: boolean;
      };

      if (!response.ok) {
        setError(payload.error ?? "Invalid email or password. Please try again.");
        return;
      }

      router.replace(destination);
      router.refresh();
    } catch {
      setError("Unable to reach the service. Please check your connection.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen lg:fixed lg:inset-0 lg:h-screen lg:w-screen lg:overflow-hidden w-full bg-[#FAFBFF] text-[#11172F] grid grid-cols-1 lg:grid-cols-12 relative font-sans selection:bg-[#4B43FF] selection:text-white">
      {/* Background Soft Glow Orbs */}
      <div className="pointer-events-none absolute -top-32 -left-32 w-[550px] h-[550px] rounded-full bg-blue-100/40 blur-3xl -z-10" />
      <div className="pointer-events-none absolute top-1/4 left-1/3 w-[450px] h-[450px] rounded-full bg-purple-100/35 blur-3xl -z-10" />
      <div className="pointer-events-none absolute -bottom-24 -right-16 w-[550px] h-[550px] rounded-full bg-indigo-100/35 blur-3xl -z-10" />

      {/* Dotted Accent Grid on right edge */}
      <div className="pointer-events-none absolute right-6 sm:right-10 top-1/2 -translate-y-1/2 w-28 h-36 opacity-35 hidden xl:block -z-10">
        <svg width="100%" height="100%" fill="none">
          <pattern id="dot-grid" x="0" y="0" width="16" height="16" patternUnits="userSpaceOnUse">
            <circle cx="2" cy="2" r="1.5" fill="#818CF8" />
          </pattern>
          <rect width="100%" height="100%" fill="url(#dot-grid)" />
        </svg>
      </div>

      {/* ============================================================== */}
      {/* LEFT PANEL: 7 cols on desktop, Header & Dashboard Preview     */}
      {/* ============================================================== */}
      <section className="lg:col-span-7 flex flex-col justify-between py-6 lg:py-7 xl:py-8 px-6 sm:px-10 lg:px-10 xl:px-14 lg:border-r lg:border-slate-100/90 relative z-0 h-full overflow-hidden">
        {/* Top Text Content */}
        <div>
          {/* Logo */}
          <div className="mb-4 sm:mb-5">
            <OmniflowLogo className="h-7 sm:h-8" />
          </div>

          {/* Badge */}
          <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-[#ECEBFF] border border-[#DDD9FF] text-[#5B43FF] text-[10.5px] font-bold tracking-wider uppercase mb-3">
            <span>CUSTOMER CONVERSATIONS, IN SYNC</span>
          </div>

          {/* Heading */}
          <h1 className="text-2xl sm:text-3xl lg:text-[34px] xl:text-[38px] font-extrabold text-[#11172F] tracking-tight leading-[1.14] mb-2.5">
            Welcome back to <br />
            your{" "}
            <span className="bg-gradient-to-r from-[#2875FF] via-[#4F46E5] to-[#7B73FF] bg-clip-text text-transparent">
              workspace.
            </span>
            {/* 3 purple ray accents doodle */}
            <span className="inline-block align-top text-[#5B43FF] opacity-80 select-none ml-2 mt-1">
              <svg className="w-4 h-4 sm:w-5 sm:h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                <line x1="6" y1="18" x2="2" y2="20" />
                <line x1="9" y1="11" x2="4" y2="8" />
                <line x1="16" y1="7" x2="14" y2="2" />
              </svg>
            </span>
          </h1>

          {/* Supporting Copy */}
          <p className="text-xs sm:text-[13px] lg:text-[13.5px] text-[#586887] max-w-lg leading-relaxed mb-4 sm:mb-5 font-normal">
            Manage WhatsApp, Instagram, Facebook Messenger and more — all your customer conversations, team collaboration and tools in one place.
          </p>
        </div>

        {/* Dashboard Preview Window (Scales responsively, fits viewport perfectly) */}
        <div className="w-full max-w-[640px] flex-1 min-h-[310px] max-h-[350px] xl:max-h-[390px] rounded-2xl bg-white border border-slate-200/90 shadow-2xl shadow-indigo-950/10 overflow-hidden flex flex-col select-none text-[11px] font-sans">
          <div className="flex flex-1 min-h-0">
            {/* 1. Dark Navy Sidebar */}
            <aside className="w-[125px] sm:w-[135px] bg-[#0c1229] p-3 text-slate-400 flex flex-col justify-between shrink-0 border-r border-slate-800/60">
              <div>
                {/* Brand Logo in Sidebar */}
                <div className="flex items-center gap-2 mb-3 px-1">
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

                {/* Nav items */}
                <nav className="space-y-0.5 text-[10px]">
                  <div className="flex items-center justify-between px-2 py-1.5 rounded-md bg-[#252a54] text-white font-medium shadow-sm">
                    <div className="flex items-center gap-2">
                      <svg className="w-3.5 h-3.5 text-[#736bff]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                      </svg>
                      <span>Inbox</span>
                    </div>
                    <span className="bg-[#4B43FF] text-[8.5px] px-1.5 py-0.2 rounded-full font-bold">12</span>
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
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z" />
                    </svg>
                    <span>Integrations</span>
                  </div>

                  <div className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:text-slate-200 cursor-pointer">
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                    <span>Settings</span>
                  </div>
                </nav>
              </div>
            </aside>

            {/* 2. Middle Conversation List Column */}
            <div className="w-[170px] sm:w-[190px] border-r border-slate-200/80 bg-white flex flex-col shrink-0">
              {/* Header: Title + Search */}
              <div className="p-2 border-b border-slate-100 flex items-center justify-between">
                <span className="font-bold text-[11px] text-slate-800">Conversations</span>
                <svg className="w-3 h-3 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                </svg>
              </div>

              {/* Channel Filter Pills */}
              <div className="px-2 py-1.5 border-b border-slate-100 flex items-center gap-1 overflow-x-auto no-scrollbar">
                <span className="px-1.5 py-0.5 rounded-full bg-[#4B43FF] text-white text-[8.5px] font-semibold shrink-0 cursor-pointer">
                  All
                </span>
                <span className="px-1.5 py-0.5 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-600 text-[8.5px] flex items-center gap-1 shrink-0 cursor-pointer">
                  <WhatsAppIcon className="!w-2.5 !h-2.5" /> WhatsApp
                </span>
                <span className="px-1.5 py-0.5 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-600 text-[8.5px] flex items-center gap-1 shrink-0 cursor-pointer">
                  <InstagramIcon className="!w-2.5 !h-2.5" /> Instagram
                </span>
                <span className="px-1.5 py-0.5 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-600 text-[8.5px] flex items-center gap-1 shrink-0 cursor-pointer">
                  <MessengerIcon className="!w-2.5 !h-2.5" /> Messenger
                </span>
                <span className="px-1.5 py-0.5 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-600 text-[8.5px] flex items-center gap-1 shrink-0 cursor-pointer">
                  <TelegramIcon className="!w-2.5 !h-2.5" /> Telegram
                </span>
              </div>

              {/* Chat Thread List */}
              <div className="flex-1 overflow-y-auto divide-y divide-slate-100/70 text-[9.5px]">
                {/* 1. Rohit Sharma (Active) */}
                <div className="p-2 bg-[#f3f4ff] border-l-2 border-[#4B43FF] cursor-pointer">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-1.5 truncate">
                      <div className="relative w-6 h-6 rounded-full overflow-hidden shrink-0">
                        <Image src="/images/rahul.jpg" alt="Rohit" fill className="object-cover" />
                      </div>
                      <div className="truncate">
                        <div className="flex items-center gap-1">
                          <span className="font-semibold text-slate-800 text-[10px]">Rohit Sharma</span>
                          <WhatsAppIcon className="!w-2.5 !h-2.5" />
                        </div>
                        <p className="text-[8.5px] text-slate-600 truncate">Hi, is this product available?</p>
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <span className="text-[7.5px] text-slate-400 block">10:24 AM</span>
                      <span className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full bg-emerald-500 text-white text-[7.5px] font-bold">2</span>
                    </div>
                  </div>
                </div>

                {/* 2. Priya Mehta */}
                <div className="p-2 hover:bg-slate-50 cursor-pointer">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-1.5 truncate">
                      <div className="w-6 h-6 rounded-full bg-purple-100 text-purple-700 font-bold text-[8.5px] flex items-center justify-center shrink-0">
                        PM
                      </div>
                      <div className="truncate">
                        <div className="flex items-center gap-1">
                          <span className="font-medium text-slate-700 text-[10px]">Priya Mehta</span>
                          <InstagramIcon className="!w-2.5 !h-2.5" />
                        </div>
                        <p className="text-[8.5px] text-slate-400 truncate">Can you share the price?</p>
                      </div>
                    </div>
                    <span className="text-[7.5px] text-slate-400 shrink-0">10:08 AM</span>
                  </div>
                </div>

                {/* 3. Sneha Patil */}
                <div className="p-2 hover:bg-slate-50 cursor-pointer">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-1.5 truncate">
                      <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 font-bold text-[8.5px] flex items-center justify-center shrink-0">
                        SP
                      </div>
                      <div className="truncate">
                        <div className="flex items-center gap-1">
                          <span className="font-medium text-slate-700 text-[10px]">Sneha Patil</span>
                          <WhatsAppIcon className="!w-2.5 !h-2.5" />
                        </div>
                        <p className="text-[8.5px] text-slate-400 truncate">Thank! Order placed ✓</p>
                      </div>
                    </div>
                    <span className="text-[7.5px] text-slate-400 shrink-0">Yesterday</span>
                  </div>
                </div>

                {/* 4. Aman Verma */}
                <div className="p-2 hover:bg-slate-50 cursor-pointer">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-1.5 truncate">
                      <div className="w-6 h-6 rounded-full bg-amber-100 text-amber-700 font-bold text-[8.5px] flex items-center justify-center shrink-0">
                        AV
                      </div>
                      <div className="truncate">
                        <div className="flex items-center gap-1">
                          <span className="font-medium text-slate-700 text-[10px]">Aman Verma</span>
                          <TelegramIcon className="!w-2.5 !h-2.5" />
                        </div>
                        <p className="text-[8.5px] text-slate-400 truncate">I need bulk quantity.</p>
                      </div>
                    </div>
                    <span className="text-[7.5px] text-slate-400 shrink-0">Yesterday</span>
                  </div>
                </div>

                {/* 5. Karan Desai */}
                <div className="p-2 hover:bg-slate-50 cursor-pointer">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-1.5 truncate">
                      <div className="w-6 h-6 rounded-full bg-rose-100 text-rose-700 font-bold text-[8.5px] flex items-center justify-center shrink-0">
                        KD
                      </div>
                      <div className="truncate">
                        <div className="flex items-center gap-1">
                          <span className="font-medium text-slate-700 text-[10px]">Karan Desai</span>
                          <InstagramIcon className="!w-2.5 !h-2.5" />
                        </div>
                        <p className="text-[8.5px] text-slate-400 truncate">When will it be delivered?</p>
                      </div>
                    </div>
                    <span className="text-[7.5px] text-slate-400 shrink-0">Oct 5</span>
                  </div>
                </div>

                {/* 6. Neha Gupta */}
                <div className="p-2 hover:bg-slate-50 cursor-pointer">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-1.5 truncate">
                      <div className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 font-bold text-[8.5px] flex items-center justify-center shrink-0">
                        NG
                      </div>
                      <div className="truncate">
                        <div className="flex items-center gap-1">
                          <span className="font-medium text-slate-700 text-[10px]">Neha Gupta</span>
                          <WhatsAppIcon className="!w-2.5 !h-2.5" />
                        </div>
                        <p className="text-[8.5px] text-slate-400 truncate">Can you share catalog?</p>
                      </div>
                    </div>
                    <span className="text-[7.5px] text-slate-400 shrink-0">Oct 4</span>
                  </div>
                </div>
              </div>
            </div>

            {/* 3. Right Active Chat Area */}
            <div className="flex-1 bg-white flex flex-col min-w-0">
              {/* Chat Header */}
              <div className="p-2 border-b border-slate-100 flex items-center justify-between bg-white shrink-0">
                <div className="flex items-center gap-1.5">
                  <div className="relative w-6 h-6 rounded-full overflow-hidden shrink-0">
                    <Image src="/images/rahul.jpg" alt="Rohit" fill className="object-cover" />
                  </div>
                  <div>
                    <span className="font-semibold text-slate-800 text-[10.5px] block leading-none">Rohit Sharma</span>
                    <span className="text-[7.5px] text-emerald-600 font-medium flex items-center gap-0.5 mt-0.5">
                      <span className="w-1 h-1 rounded-full bg-emerald-500 inline-block" /> Online
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-slate-400">
                  <svg className="w-3.5 h-3.5 hover:text-slate-600 cursor-pointer" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                  </svg>
                  <svg className="w-3.5 h-3.5 hover:text-slate-600 cursor-pointer" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                  </svg>
                </div>
              </div>

              {/* Chat Message Stream */}
              <div className="flex-1 p-2.5 overflow-y-auto space-y-1.5 text-[9px] bg-[#FAFBFF]">
                {/* 1. Incoming Rohit */}
                <div className="flex items-end gap-1 max-w-[85%]">
                  <div className="bg-white border border-slate-100 rounded-2xl rounded-bl-sm p-2 shadow-xs text-slate-800">
                    <p>Hi, is this product available?</p>
                    <span className="text-[7px] text-slate-400 block text-right mt-0.5">10:24 AM</span>
                  </div>
                </div>

                {/* 2. Outgoing Purple Agent Bubble */}
                <div className="flex items-end justify-end gap-1">
                  <div className="bg-[#4B43FF] text-white rounded-2xl rounded-br-sm p-2 shadow-xs max-w-[85%]">
                    <p>Yes! It&apos;s available. Would you like to see the details?</p>
                    <div className="flex items-center justify-end gap-1 mt-0.5">
                      <span className="text-[7px] text-indigo-200">10:25 AM</span>
                      <span className="text-[7px] text-indigo-200">✓✓</span>
                    </div>
                  </div>
                </div>

                {/* 3. Product Card */}
                <div className="flex justify-end">
                  <div className="w-[165px] bg-white border border-slate-200/80 rounded-xl p-1.5 shadow-xs">
                    <div className="relative w-full h-14 rounded-lg overflow-hidden bg-slate-50 flex items-center justify-center mb-1">
                      <Image
                        src="/images/sneaker.jpg"
                        alt="Nike Air Max 270"
                        fill
                        className="object-contain p-1"
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-bold text-[8.5px] text-slate-900 leading-none">Nike Air Max 270</p>
                        <span className="text-[8px] text-slate-500 font-semibold">₹8,099</span>
                      </div>
                      <button
                        type="button"
                        className="px-2 py-0.5 rounded-md border border-[#4B43FF] text-[#4B43FF] text-[7.5px] font-bold hover:bg-[#4B43FF] hover:text-white transition-colors"
                      >
                        View Product
                      </button>
                    </div>
                  </div>
                </div>

                {/* 4. Incoming Rohit */}
                <div className="flex items-end gap-1 max-w-[85%]">
                  <div className="bg-white border border-slate-100 rounded-2xl rounded-bl-sm p-2 shadow-xs text-slate-800">
                    <p>Great! How long will delivery take?</p>
                    <span className="text-[7px] text-slate-400 block text-right mt-0.5">10:28 AM</span>
                  </div>
                </div>
              </div>

              {/* Chat Input Bar */}
              <div className="p-1.5 border-t border-slate-100 bg-white flex items-center gap-1.5 shrink-0">
                <button type="button" className="text-slate-400 hover:text-slate-600">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                  </svg>
                </button>
                <input
                  type="text"
                  placeholder="Type a message..."
                  className="flex-1 text-[9.5px] text-slate-700 bg-transparent border-none outline-none placeholder:text-slate-400"
                />
                <button type="button" className="text-slate-400 hover:text-slate-600">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </button>
                <button type="button" className="w-5 h-5 rounded-md bg-[#4B43FF] text-white flex items-center justify-center shrink-0">
                  <svg className="w-2.5 h-2.5 rotate-45 -mr-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ============================================================== */}
      {/* RIGHT PANEL: 5 cols on desktop, Centered Clean Login Card      */}
      {/* ============================================================== */}
      <section className="lg:col-span-5 flex items-center justify-center p-6 sm:p-8 lg:p-8 xl:p-12 relative z-10 h-full">
        {/* Login Card */}
        <div className="w-full max-w-[420px] bg-white rounded-[26px] p-7 sm:p-8 shadow-xl shadow-slate-200/60 border border-slate-100/90">
          {/* Centered Omniflow Logo Symbol */}
          <div className="flex justify-center mb-3">
            <OmniflowSymbol className="w-12 h-12" />
          </div>

          {/* Heading */}
          <h2 className="text-2xl sm:text-[25px] font-extrabold text-[#11172F] tracking-tight text-center">
            Sign in to Omniflow
          </h2>

          {/* Subtitle */}
          <p className="mt-1 text-xs sm:text-[13px] text-[#586887] text-center mb-6">
            Pick up where your team left off.
          </p>

          {/* Status notices */}
          {registered && (
            <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-3.5 py-2 text-xs text-emerald-800">
              Your workspace is ready. Sign in with the account you just created.
            </div>
          )}

          {sessionExpired && (
            <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-3.5 py-2 text-xs text-amber-800">
              Your session has expired. Please sign in again to continue.
            </div>
          )}

          {error && (
            <div role="alert" className="mb-4 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2 text-xs text-rose-800">
              {error}
            </div>
          )}

          {forgotNotice && (
            <div className="mb-4 rounded-xl border border-indigo-200 bg-indigo-50 px-3.5 py-2 text-xs text-indigo-800">
              To reset your password, contact your workspace administrator or email support@omniflow.com.
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            {/* Work email field */}
            <div>
              <label htmlFor="login-email" className="block text-xs font-semibold text-slate-700 mb-1">
                Work email
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
                <input
                  id="login-email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  className="w-full bg-[#EEF2FC]/70 hover:bg-[#EEF2FC] border border-slate-200/70 rounded-xl pl-10 pr-3.5 py-2.5 sm:py-2.8 text-sm text-slate-900 placeholder:text-slate-400 outline-none transition-all focus:border-[#4B43FF] focus:bg-white focus:ring-4 focus:ring-[#4B43FF]/10"
                />
              </div>
            </div>

            {/* Password field */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label htmlFor="login-password" className="block text-xs font-semibold text-slate-700">
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => setForgotNotice(true)}
                  className="text-xs font-semibold text-[#4B43FF] hover:underline transition-colors"
                >
                  Forgot your password?
                </button>
              </div>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </div>
                <input
                  id="login-password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="w-full bg-[#EEF2FC]/70 hover:bg-[#EEF2FC] border border-slate-200/70 rounded-xl pl-10 pr-10 py-2.5 sm:py-2.8 text-sm text-slate-900 placeholder:text-slate-400 outline-none transition-all focus:border-[#4B43FF] focus:bg-white focus:ring-4 focus:ring-[#4B43FF]/10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
                >
                  {showPassword ? (
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            {/* Remember me checkbox */}
            <div className="flex items-center pt-0.5">
              <input
                id="remember-me"
                name="remember-me"
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="w-4 h-4 rounded border-slate-300 text-[#4B43FF] focus:ring-[#4B43FF] accent-[#4B43FF] cursor-pointer"
              />
              <label htmlFor="remember-me" className="ml-2 block text-xs font-medium text-slate-600 cursor-pointer select-none">
                Remember me
              </label>
            </div>

            {/* Sign in button */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full min-h-[44px] sm:min-h-[46px] rounded-xl bg-gradient-to-r from-[#2875FF] to-[#5B43FF] hover:opacity-95 text-white font-semibold text-sm shadow-md shadow-indigo-500/25 flex items-center justify-center gap-2 transition-all disabled:opacity-60 disabled:cursor-not-allowed pt-0.5 cursor-pointer"
            >
              {isSubmitting ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <span>Signing in…</span>
                </span>
              ) : (
                <>
                  <span>Sign in</span>
                  <span className="text-base leading-none">&rarr;</span>
                </>
              )}
            </button>
          </form>

          {/* Footer Text */}
          <p className="mt-5 text-center text-xs text-slate-500">
            New to Omniflow?{" "}
            <Link href="/register" className="font-semibold text-[#4B43FF] hover:underline">
              Create an account
            </Link>
          </p>
        </div>
      </section>
    </div>
  );
}
