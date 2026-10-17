import React from "react";
import { Navbar } from "@/components/landing/navbar";
import { Hero } from "@/components/landing/hero";
import { Features } from "@/components/landing/features";
import { Workflow } from "@/components/landing/workflow";
import { Integrations } from "@/components/landing/integrations";
import { Testimonials } from "@/components/landing/testimonials";
import { Pricing } from "@/components/landing/pricing";
import { CtaBanner } from "@/components/landing/cta-banner";
import { Footer } from "@/components/landing/footer";

export default function HomePage() {
  return (
    <main className="min-h-screen w-full overflow-x-clip bg-white text-[#11172F] selection:bg-[#4B43FF] selection:text-white">
      <Navbar />
      <Hero />
      <Features />
      <Workflow />
      <Integrations />
      <Testimonials />
      <Pricing />
      <CtaBanner />
      <Footer />
    </main>
  );
}
