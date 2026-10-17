"use client";

import React, { useState } from "react";
import {
  WhatsAppIcon,
  InstagramIcon,
  MessengerIcon,
  TelegramIcon,
  ShopifyIcon,
  WooCommerceIcon,
  GoogleSheetsIcon,
  ZapierIcon,
} from "./icons";

const integrationItems = [
  { name: "WhatsApp", icon: WhatsAppIcon },
  { name: "Instagram", icon: InstagramIcon },
  { name: "Messenger", icon: MessengerIcon },
  { name: "Telegram", icon: TelegramIcon },
  { name: "Shopify", icon: ShopifyIcon },
  { name: "WooCommerce", icon: WooCommerceIcon },
  { name: "Google Sheets", icon: GoogleSheetsIcon },
  { name: "Zapier", icon: ZapierIcon },
];

export function Integrations() {
  const [isHovered, setIsHovered] = useState(false);

  // Repeat items so marquee loops seamlessly on all screen sizes (50% translation = 2 complete cycles)
  const repeatedItems = [
    ...integrationItems,
    ...integrationItems,
    ...integrationItems,
    ...integrationItems,
  ];

  return (
    <section id="integrations" className="py-20 sm:py-24 bg-[#FAFBFF] border-t border-slate-100 overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center mb-12">
        {/* Badge */}
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#ECEBFF] border border-[#DDD9FF] text-[#4B43FF] text-xs font-semibold mb-4">
          <span>INTEGRATIONS</span>
        </div>

        {/* Heading */}
        <h2 className="text-3xl sm:text-4xl font-extrabold text-[#11172F] tracking-tight mb-3">
          Connect with your favourite tools
        </h2>

        {/* Subtitle */}
        <p className="text-[15px] text-[#475569] max-w-xl mx-auto">
          Omni integrates with the tools you already use, so you can keep everything in sync.
        </p>
      </div>

      {/* Slider Carousel Container - No boxes, pauses on hover */}
      <div
        className="relative w-full overflow-hidden py-4 slider-container group"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        {/* Soft edge fade masks */}
        <div className="pointer-events-none absolute left-0 top-0 bottom-0 w-24 sm:w-44 bg-gradient-to-r from-[#FAFBFF] via-[#FAFBFF]/80 to-transparent z-10" />
        <div className="pointer-events-none absolute right-0 top-0 bottom-0 w-24 sm:w-44 bg-gradient-to-l from-[#FAFBFF] via-[#FAFBFF]/80 to-transparent z-10" />

        {/* Marquee Track */}
        <div
          className="flex items-center gap-10 sm:gap-16 w-max animate-marquee-scroll transition-all"
          style={{
            animationPlayState: isHovered ? "paused" : "running",
          }}
        >
          {repeatedItems.map((item, idx) => {
            const Icon = item.icon;
            return (
              <div
                key={idx}
                className="flex flex-col items-center justify-center gap-3 cursor-pointer shrink-0 transition-transform duration-200 hover:scale-115 select-none"
              >
                {/* Official Logo without card box */}
                <div className="w-14 h-14 sm:w-16 sm:h-16 flex items-center justify-center transition-transform duration-200">
                  <Icon className="w-full h-full object-contain drop-shadow-sm hover:drop-shadow-md transition-all" />
                </div>
                <span className="text-[13px] sm:text-sm font-semibold text-slate-700 whitespace-nowrap">
                  {item.name}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
