"use client";

import React, { useState, useEffect, Suspense, FormEvent } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useAdminAuth } from "../../lib/auth/context";
import { ShieldCheck } from "lucide-react";

// Official WhatsApp Vector Icon
function WhatsAppIcon({ className = "w-3.5 h-3.5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 256 258" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="wa-green-bg" x1="50%" x2="50%" y1="100%" y2="0%">
          <stop offset="0%" stopColor="#1faf38" />
          <stop offset="100%" stopColor="#60d669" />
        </linearGradient>
        <linearGradient id="wa-white-bg" x1="50%" x2="50%" y1="100%" y2="0%">
          <stop offset="0%" stopColor="#f9f9f9" />
          <stop offset="100%" stopColor="#ffffff" />
        </linearGradient>
      </defs>
      <path
        fill="url(#wa-green-bg)"
        d="M5.463 127.456c-.006 21.677 5.658 42.843 16.428 61.499L4.433 252.697l65.232-17.104a123 123 0 0 0 58.8 14.97h.054c67.815 0 123.018-55.183 123.047-123.01c.013-32.867-12.775-63.773-36.009-87.025c-23.23-23.25-54.125-36.061-87.043-36.076c-67.823 0-123.022 55.18-123.05 123.004"
      />
      <path
        fill="url(#wa-white-bg)"
        d="M1.07 127.416c-.007 22.457 5.86 44.38 17.014 63.704L0 257.147l67.571-17.717c18.618 10.151 39.58 15.503 60.91 15.511h.055c70.248 0 127.434-57.168 127.464-127.423c.012-34.048-13.236-66.065-37.3-90.15C194.633 13.286 162.633.014 128.536 0C58.276 0 1.099 57.16 1.071 127.416m40.24 60.376l-2.523-4.005c-10.606-16.864-16.204-36.352-16.196-56.363C22.614 69.029 70.138 21.52 128.576 21.52c28.3.012 54.896 11.044 74.9 31.06c20.003 20.018 31.01 46.628 31.003 74.93c-.026 58.395-47.551 105.91-105.943 105.91h-.042c-19.013-.01-37.66-5.116-53.922-14.765l-3.87-2.295l-40.098 10.513z"
      />
      <path
        fill="#ffffff"
        d="M96.678 74.148c-2.386-5.303-4.897-5.41-7.166-5.503c-1.858-.08-3.982-.074-6.104-.074c-2.124 0-5.575.799-8.492 3.984c-2.92 3.188-11.148 10.892-11.148 26.561s11.413 30.813 13.004 32.94c1.593 2.123 22.033 35.307 54.405 48.073c26.904 10.609 32.379 8.499 38.218 7.967c5.84-.53 18.844-7.702 21.497-15.139c2.655-7.436 2.655-13.81 1.859-15.142c-.796-1.327-2.92-2.124-6.105-3.716s-18.844-9.298-21.763-10.361c-2.92-1.062-5.043-1.592-7.167 1.597c-2.124 3.184-8.223 10.356-10.082 12.48c-1.857 2.129-3.716 2.394-6.9.801c-3.187-1.598-13.444-4.957-25.613-15.806c-9.468-8.442-15.86-18.867-17.718-22.056c-1.858-3.184-.199-4.91 1.398-6.497c1.431-1.427 3.186-3.719 4.78-5.578c1.588-1.86 2.118-3.187 3.18-5.311c1.063-2.126.531-3.986-.264-5.579c-.798-1.593-6.987-17.343-9.819-23.64"
      />
    </svg>
  );
}

// Official Instagram Vector Icon
function InstagramIcon({ className = "w-3.5 h-3.5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient
          id="ig-sunset-1-adm"
          cx="0"
          cy="0"
          r="1"
          gradientTransform="matrix(0 -253.715 235.975 0 68 275.717)"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#fd5" />
          <stop offset=".1" stopColor="#fd5" />
          <stop offset=".5" stopColor="#ff543e" />
          <stop offset="1" stopColor="#c837ab" />
        </radialGradient>
        <radialGradient
          id="ig-sunset-2-adm"
          cx="0"
          cy="0"
          r="1"
          gradientTransform="rotate(78.68 -32.69 -16.937)scale(113.412 467.488)"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#3771c8" />
          <stop offset=".128" stopColor="#3771c8" />
          <stop offset="1" stopColor="#60f" stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect width="256" height="256" rx="60" fill="url(#ig-sunset-1-adm)" />
      <rect width="256" height="256" rx="60" fill="url(#ig-sunset-2-adm)" />
      <path
        fill="#ffffff"
        d="M128.009 28c-27.158 0-30.567.119-41.233.604c-10.646.488-17.913 2.173-24.271 4.646c-6.578 2.554-12.157 5.971-17.715 11.531c-5.563 5.559-8.98 11.138-11.542 17.713c-2.48 6.36-4.167 13.63-4.646 24.271c-.477 10.667-.602 14.077-.602 41.236s.12 30.557.604 41.223c.49 10.646 2.175 17.913 4.646 24.271c2.556 6.578 5.973 12.157 11.533 17.715c5.557 5.563 11.136 8.988 17.709 11.542c6.363 2.473 13.631 4.158 24.275 4.646c10.667.485 14.073.604 41.23.604c27.161 0 30.559-.119 41.225-.604c10.646-.488 17.921-2.173 24.284-4.646c6.575-2.554 12.146-5.979 17.702-11.542c5.563-5.558 8.979-11.137 11.542-17.712c2.458-6.361 4.146-13.63 4.646-24.272c.479-10.666.604-14.066.604-41.225s-.125-30.567-.604-41.234c-.5-10.646-2.188-17.912-4.646-24.27c-2.563-6.578-5.979-12.157-11.542-17.716c-5.562-5.562-11.125-8.979-17.708-11.53c-6.375-2.474-13.646-4.16-24.292-4.647c-10.667-.485-14.063-.604-41.23-.604zm-8.971 18.021c2.663-.004 5.634 0 8.971 0c26.701 0 29.865.096 40.409.575c9.75.446 15.042 2.075 18.567 3.444c4.667 1.812 7.994 3.979 11.492 7.48c3.5 3.5 5.666 6.833 7.483 11.5c1.369 3.52 3 8.812 3.444 18.562c.479 10.542.583 13.708.583 40.396s-.104 29.855-.583 40.396c-.446 9.75-2.075 15.042-3.444 18.563c-1.812 4.667-3.983 7.99-7.483 11.488c-3.5 3.5-6.823 5.666-11.492 7.479c-3.521 1.375-8.817 3-18.567 3.446c-10.542.479-13.708.583-40.409.583c-26.702 0-29.867-.104-40.408-.583c-9.75-.45-15.042-2.079-18.57-3.448c-4.666-1.813-8-3.979-11.5-7.479s-5.666-6.825-7.483-11.494c-1.369-3.521-3-8.813-3.444-18.563c-.479-10.542-.575-13.708-.575-40.413s.096-29.854.575-40.396c.446-9.75 2.075-15.042 3.444-18.567c1.813-4.667 3.983-8 7.484-11.5s6.833-5.667 11.5-7.483c3.525-1.375 8.819-3 18.569-3.448c9.225-.417 12.8-.542 31.437-.563zm62.351 16.604c-6.625 0-12 5.37-12 11.996c0 6.625 5.375 12 12 12s12-5.375 12-12s-5.375-12-12-12zm-53.38 14.021c-28.36 0-51.354 22.994-51.354 51.355s22.994 51.344 51.354 51.344c28.361 0 51.347-22.983 51.347-51.344c0-28.36-22.988-51.355-51.349-51.355zm0 18.021c18.409 0 33.334 14.923 33.334 33.334c0 18.409-14.925 33.334-33.334 33.334s-33.333-14.925-33.333-33.334c0-18.411 14.923-33.334 33.333-33.334"
      />
    </svg>
  );
}

// Official Messenger Vector Icon
function MessengerIcon({ className = "w-3.5 h-3.5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient
          id="msg-official-grad-adm"
          cx="19.247%"
          cy="99.465%"
          r="108.96%"
          fx="19.247%"
          fy="99.465%"
        >
          <stop offset="0%" stopColor="#09f" />
          <stop offset="60.975%" stopColor="#a033ff" />
          <stop offset="93.482%" stopColor="#ff5280" />
          <stop offset="100%" stopColor="#ff7061" />
        </radialGradient>
      </defs>
      <circle cx="128" cy="128" r="128" fill="url(#msg-official-grad-adm)" />
      <path
        fill="#ffffff"
        d="m64.887 167.973l32.842-52.036c5.203-8.246 16.518-10.428 24.372-4.708l26.046 18.99a7.65 7.65 0 0 0 9.475-.306l34.999-26.634c4.664-3.551 10.669 1.942 7.683 6.666l-32.841 52.036c-5.204 8.246-16.518 10.428-24.373 4.708l-26.046-18.99a7.65 7.65 0 0 0-9.475.306l-34.998 26.634c-4.665 3.55-10.67-1.942-7.684-6.665"
      />
    </svg>
  );
}

// Official Telegram Vector Icon
function TelegramIcon({ className = "w-3.5 h-3.5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 240 240" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="tg-grad-adm" x1="50%" x2="50%" y1="0%" y2="100%">
          <stop offset="0%" stopColor="#2AABEE" />
          <stop offset="100%" stopColor="#229ED9" />
        </linearGradient>
      </defs>
      <circle cx="120" cy="120" r="120" fill="url(#tg-grad-adm)" />
      <path
        fill="#ffffff"
        d="M54.7 118.5c34.8-15.2 58.1-25.2 69.8-30.1 33.3-13.9 40.2-16.3 44.7-16.4 1 0 3.2.2 4.7 1.4 1.2 1 1.6 2.4 1.7 3.4.2 1 0 2.4-.1 3.4-3.5 36.8-18.8 126.9-26.6 168.4-3.3 17.6-9.8 23.5-16.1 24.1-13.7 1.3-24.1-9.1-37.4-17.8-20.8-13.7-32.6-22.2-52.7-35.5-23.3-15.4-8.2-23.8 5.1-37.6 3.5-3.6 63.9-58.6 65.1-63.6.1-.6.3-3-.9-4.1-1.2-1-2.9-.7-4.1-.4-1.8.4-30.2 19.2-85.3 56.4-8.1 5.5-15.4 8.3-22 8.1-7.2-.2-21.1-4.1-31.5-7.5-12.7-4.1-22.8-6.3-21.9-13.3.5-3.6 5.4-7.3 14.8-11.2z"
      />
    </svg>
  );
}

function AdminLoginForm() {
  const router = useRouter();
  const { user, loading: authLoading, login } = useAdminAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [forgotNotice, setForgotNotice] = useState(false);

  // Prevent vertical scrollbar ("stick") on desktop viewport
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

  useEffect(() => {
    if (!authLoading && user) {
      router.replace("/dashboard");
    }
  }, [user, authLoading, router]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setForgotNotice(false);

    if (!email.trim() || !password) {
      setError("Please enter both email and password.");
      return;
    }

    setIsSubmitting(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Authentication failed.";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen lg:fixed lg:inset-0 lg:h-screen lg:w-screen lg:overflow-hidden w-full bg-[#FAFBFF] text-[#11172F] grid grid-cols-1 lg:grid-cols-12 relative font-sans selection:bg-[#4B43FF] selection:text-white">
      {/* Background Soft Glow Orbs */}
      <div className="pointer-events-none absolute -top-32 -left-32 w-[550px] h-[550px] rounded-full bg-blue-100/40 blur-3xl -z-10" />
      <div className="pointer-events-none absolute top-1/4 left-1/3 w-[450px] h-[450px] rounded-full bg-purple-100/35 blur-3xl -z-10" />
      <div className="pointer-events-none absolute -bottom-24 -right-16 w-[550px] h-[550px] rounded-full bg-indigo-100/35 blur-3xl -z-10" />

      {/* Dotted Accent Grid on right edge */}
      <div className="pointer-events-none absolute right-6 sm:right-10 top-1/2 -translate-y-1/2 w-28 h-36 opacity-35 hidden xl:block -z-10">
        <svg width="100%" height="100%" fill="none">
          <pattern id="dot-grid-adm" x="0" y="0" width="16" height="16" patternUnits="userSpaceOnUse">
            <circle cx="2" cy="2" r="1.5" fill="#818CF8" />
          </pattern>
          <rect width="100%" height="100%" fill="url(#dot-grid-adm)" />
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
            <div className="inline-flex items-center gap-2.5">
              <Image
                src="/images/omniflow-logo.png"
                alt="Omniflow"
                width={140}
                height={35}
                className="h-7 sm:h-8 w-auto object-contain"
                priority
                unoptimized
              />
            </div>
          </div>

          {/* Badge */}
          <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-[#ECEBFF] border border-[#DDD9FF] text-[#5B43FF] text-[10.5px] font-bold tracking-wider uppercase mb-3">
            <span>SUPER ADMIN CONSOLE</span>
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
            Manage WhatsApp, Instagram, Facebook Messenger and platform infrastructure — all your customer conversations, team collaboration and controls in one place.
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
                    <span>Tenants</span>
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
                    <span>Audit Logs</span>
                  </div>

                  <div className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:text-slate-200 cursor-pointer">
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z" />
                    </svg>
                    <span>Channels</span>
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
                        <Image src="/images/rahul.jpg" alt="Rohit" fill className="object-cover" unoptimized />
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
              </div>
            </div>

            {/* 3. Right Active Chat Pane with Sneaker Card */}
            <div className="flex-1 bg-[#fbfbfe] flex flex-col justify-between min-w-0">
              {/* Chat Header */}
              <div className="px-3 py-2 border-b border-slate-200/70 bg-white flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="relative w-7 h-7 rounded-full overflow-hidden shrink-0">
                    <Image src="/images/rahul.jpg" alt="Rohit" fill className="object-cover" unoptimized />
                  </div>
                  <div>
                    <div className="flex items-center gap-1">
                      <span className="font-bold text-slate-800 text-[11px]">Rohit Sharma</span>
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block" />
                    </div>
                    <span className="text-[8.5px] text-slate-400 flex items-center gap-1">
                      <WhatsAppIcon className="!w-2 !h-2" /> +91 98765 43210
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-1.5 text-slate-400">
                  <span className="px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-600 text-[8.5px] font-bold border border-emerald-200">
                    Active
                  </span>
                </div>
              </div>

              {/* Chat Message Stream */}
              <div className="p-3 space-y-2.5 overflow-y-auto flex-1">
                {/* Customer Message */}
                <div className="flex items-start gap-1.5 max-w-[80%]">
                  <div className="bg-white border border-slate-200/90 rounded-2xl rounded-tl-none p-2 shadow-sm text-slate-700">
                    <p className="text-[9.5px]">Hi! Is the Nike Air Jordan 1 retro high available in UK 9?</p>
                    <span className="text-[7.5px] text-slate-400 mt-1 block text-right">10:23 AM</span>
                  </div>
                </div>

                {/* Omni Bot / Agent Response with Product Card */}
                <div className="flex items-start gap-1.5 max-w-[88%] ml-auto justify-end">
                  <div className="bg-[#4B43FF] text-white rounded-2xl rounded-tr-none p-2 shadow-sm text-left">
                    <p className="text-[9.5px]">Yes Rohit! We have 2 pairs left in UK 9 with same-day dispatch 🚀</p>

                    {/* Rich Product Card inside bubble */}
                    <div className="mt-1.5 bg-white text-slate-900 rounded-xl p-1.5 flex items-center gap-2 shadow-sm">
                      <div className="relative w-12 h-12 rounded-lg overflow-hidden bg-slate-100 shrink-0">
                        <Image src="/images/sneaker.jpg" alt="Sneaker" fill className="object-cover" unoptimized />
                      </div>
                      <div className="flex-1 min-w-0">
                        <span className="font-bold text-[9px] block truncate text-slate-800">Nike Air Jordan 1 Retro</span>
                        <div className="flex items-center gap-1">
                          <span className="text-[9px] font-extrabold text-[#4B43FF]">₹14,995</span>
                          <span className="text-[7.5px] text-slate-400 line-through">₹18,995</span>
                        </div>
                        <span className="text-[7px] text-emerald-600 font-semibold">In Stock (UK 9)</span>
                      </div>
                    </div>

                    <span className="text-[7.5px] text-indigo-200 mt-1 block text-right">10:24 AM ✓✓</span>
                  </div>
                </div>
              </div>

              {/* Chat Composer / Reply Bar */}
              <div className="p-2 border-t border-slate-200/80 bg-white flex items-center gap-1.5">
                <input
                  type="text"
                  placeholder="Type a message or use /quickreply..."
                  disabled
                  className="flex-1 text-[9px] bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 text-slate-600 placeholder:text-slate-400 outline-none"
                />
                <button
                  type="button"
                  disabled
                  className="p-1 rounded-lg bg-[#4B43FF] text-white shrink-0 hover:bg-[#3D35E0]"
                >
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ============================================================== */}
      {/* RIGHT PANEL: 5 cols on desktop, Clean Admin Sign-in Card       */}
      {/* ============================================================== */}
      <section className="lg:col-span-5 flex flex-col items-center justify-center py-8 px-6 sm:px-10 lg:px-10 xl:px-14 relative z-10">
        <div className="w-full max-w-[390px] rounded-3xl bg-white border border-slate-200/80 p-7 sm:p-8 shadow-xl shadow-slate-200/50 relative">
          {/* Logo Symbol at top of card */}
          <div className="mb-4 flex justify-center">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-[#2875FF]/10 via-[#4B43FF]/15 to-[#7B73FF]/10 flex items-center justify-center p-2 border border-[#4B43FF]/20 shadow-sm">
              <Image
                src="/images/omniflow-symbol.png"
                alt="Omniflow"
                width={32}
                height={32}
                className="w-7 h-7 object-contain"
                unoptimized
              />
            </div>
          </div>

          {/* Heading */}
          <h2 className="text-xl sm:text-2xl font-extrabold text-[#11172F] tracking-tight text-center">
            Sign in to Omniflow Admin
          </h2>
          <p className="mt-1 text-xs text-slate-500 text-center mb-6">
            Enter your credentials to access the control plane
          </p>

          {/* Status notices */}
          {error && (
            <div role="alert" className="mb-4 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2 text-xs text-rose-800">
              {error}
            </div>
          )}

          {forgotNotice && (
            <div className="mb-4 rounded-xl border border-indigo-200 bg-indigo-50 px-3.5 py-2 text-xs text-indigo-800">
              Password resets require platform master seed recovery or assistance from the root administrator.
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            {/* Admin email field */}
            <div>
              <label htmlFor="admin-login-email" className="block text-xs font-semibold text-slate-700 mb-1">
                Admin email
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
                <input
                  id="admin-login-email"
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
                <label htmlFor="admin-login-password" className="block text-xs font-semibold text-slate-700">
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
                  id="admin-login-password"
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
                id="admin-remember-me"
                name="remember-me"
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="w-4 h-4 rounded border-slate-300 text-[#4B43FF] focus:ring-[#4B43FF] accent-[#4B43FF] cursor-pointer"
              />
              <label htmlFor="admin-remember-me" className="ml-2 block text-xs font-medium text-slate-600 cursor-pointer select-none">
                Remember this device
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

          {/* Enterprise Security Footnote */}
          <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-center gap-2 text-[11px] text-slate-500">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
            <span>Argon2id Enforced • Strict Audit Trail</span>
          </div>
        </div>
      </section>
    </div>
  );
}

export default function AdminLoginPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-[#FAFBFF] text-slate-400 text-xs">
          Loading Control Plane Login...
        </div>
      }
    >
      <AdminLoginForm />
    </Suspense>
  );
}
