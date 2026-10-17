import React from "react";
import Link from "next/link";
import Image from "next/image";

export function Footer() {
  return (
    <footer className="w-full bg-white border-t border-slate-100 pt-16 pb-12 text-[#11172F]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-10 lg:gap-8 pb-12 border-b border-slate-100">
          {/* Brand info (2 columns wide on desktop) */}
          <div className="lg:col-span-2">
            <div className="flex items-center gap-2.5 mb-3">
              <Image
                src="/images/omniflow-logo.png"
                alt="Omniflow"
                width={135}
                height={34}
                className="h-7 sm:h-8 w-auto object-contain"
                unoptimized
              />
            </div>
            <p className="text-xs sm:text-[13px] text-slate-500 leading-relaxed max-w-sm mb-6">
              The all-in-one omnichannel messaging platform for modern businesses.
            </p>

            {/* Social Icons */}
            <div className="flex items-center gap-3 text-slate-400">
              {/* LinkedIn */}
              <a href="#" className="w-8 h-8 rounded-full bg-slate-50 hover:bg-indigo-50 hover:text-[#4B43FF] flex items-center justify-center transition-colors">
                <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
                  <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 8.76a1.44 1.44 0 1 0 0-2.88 1.44 1.44 0 0 0 0 2.88m1.39 9.74v-8.37H5.07v8.37h2.78z" />
                </svg>
              </a>

              {/* Twitter / X */}
              <a href="#" className="w-8 h-8 rounded-full bg-slate-50 hover:bg-indigo-50 hover:text-[#4B43FF] flex items-center justify-center transition-colors">
                <svg className="w-3.5 h-3.5 fill-current" viewBox="0 0 24 24">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                </svg>
              </a>

              {/* YouTube */}
              <a href="#" className="w-8 h-8 rounded-full bg-slate-50 hover:bg-indigo-50 hover:text-[#4B43FF] flex items-center justify-center transition-colors">
                <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
                  <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
                </svg>
              </a>

              {/* Instagram */}
              <a href="#" className="w-8 h-8 rounded-full bg-slate-50 hover:bg-indigo-50 hover:text-[#4B43FF] flex items-center justify-center transition-colors">
                <svg className="w-4 h-4 fill-none stroke-current" strokeWidth="2" viewBox="0 0 24 24">
                  <rect x="2" y="2" width="20" height="20" rx="5" ry="5" />
                  <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
                  <line x1="17.5" y1="6.5" x2="17.51" y2="6.5" />
                </svg>
              </a>
            </div>
          </div>

          {/* Product Column */}
          <div>
            <h4 className="text-xs font-bold text-[#11172F] uppercase tracking-wider mb-4">Product</h4>
            <ul className="space-y-2.5 text-xs text-slate-500">
              <li><Link href="#features" className="hover:text-[#4B43FF] transition-colors">Features</Link></li>
              <li><Link href="#integrations" className="hover:text-[#4B43FF] transition-colors">Integrations</Link></li>
              <li><Link href="#pricing" className="hover:text-[#4B43FF] transition-colors">Pricing</Link></li>
              <li><a href="#" className="hover:text-[#4B43FF] transition-colors">Updates</a></li>
            </ul>
          </div>

          {/* Company Column */}
          <div>
            <h4 className="text-xs font-bold text-[#11172F] uppercase tracking-wider mb-4">Company</h4>
            <ul className="space-y-2.5 text-xs text-slate-500">
              <li><a href="#" className="hover:text-[#4B43FF] transition-colors">About Us</a></li>
              <li><a href="#" className="hover:text-[#4B43FF] transition-colors">Careers</a></li>
              <li><a href="#" className="hover:text-[#4B43FF] transition-colors">Blog</a></li>
              <li><a href="#" className="hover:text-[#4B43FF] transition-colors">Contact</a></li>
            </ul>
          </div>

          {/* Resources Column */}
          <div>
            <h4 className="text-xs font-bold text-[#11172F] uppercase tracking-wider mb-4">Resources</h4>
            <ul className="space-y-2.5 text-xs text-slate-500">
              <li><a href="#" className="hover:text-[#4B43FF] transition-colors">Help Center</a></li>
              <li><a href="#" className="hover:text-[#4B43FF] transition-colors">Documentation</a></li>
              <li><a href="#" className="hover:text-[#4B43FF] transition-colors">Privacy Policy</a></li>
              <li><a href="#" className="hover:text-[#4B43FF] transition-colors">Terms of Service</a></li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-400 gap-4">
          <div>© 2026 Omni. All rights reserved.</div>
          <div className="flex items-center gap-1">
            <span>Made with</span>
            <span className="text-rose-500">❤️</span>
            <span>for growing businesses</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
