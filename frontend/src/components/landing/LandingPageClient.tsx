"use client";

import { useCallback, useState } from "react";
import { InstallModalContext } from "@/lib/install-modal-context";
import { ShopInputModal } from "@/components/landing/ShopInputModal";
import { Hero } from "@/components/landing/Hero";
import { LandingNavbar } from "@/components/landing/LandingNavbar";
import { LogosBar } from "@/components/landing/LogosBar";
import { PainPoints } from "@/components/landing/PainPoints";
import { Solution } from "@/components/landing/Solution";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { FeaturesGrid } from "@/components/landing/FeaturesGrid";
import { UninstallWall } from "@/components/landing/UninstallWall";
import { ComparisonTable } from "@/components/landing/ComparisonTable";
import { PricingPreview } from "@/components/landing/PricingPreview";
import { Testimonials } from "@/components/landing/Testimonials";
import { FAQ } from "@/components/landing/FAQ";
import { FooterCTA } from "@/components/landing/FooterCTA";
import { Footer } from "@/components/landing/Footer";

interface LandingPageClientProps {
  installHref: string;
}

export function LandingPageClient({ installHref }: LandingPageClientProps) {
  const [showModal, setShowModal] = useState(false);

  const openModal = useCallback(() => setShowModal(true), []);
  const closeModal = useCallback(() => setShowModal(false), []);

  return (
    <InstallModalContext.Provider value={{ openModal, installHref }}>
      <div className="relative min-h-screen bg-[#0a0a0f] font-sans text-slate-100 antialiased">
        <LandingNavbar installHref={installHref} />
        <Hero installHref={installHref} />
        <section className="relative border-y border-white/5 bg-[#0a0a0f] py-14">
          <div className="mx-auto max-w-7xl px-6 text-center">
            <h2 className="font-display text-3xl font-extrabold tracking-tight text-white sm:text-4xl lg:text-5xl">
              1 agent.{" "}
              <span className="text-gradient-cyan">5 apps killed.</span>{" "}
              0 bullshit.
            </h2>
            <p className="mx-auto mt-5 max-w-2xl text-base text-slate-400 sm:text-lg">
              SEO app. Speed app. Accessibility app. Broken link checker. Audit tool.
              Kill them all. StoreMD does the work of 5 — for less than any one of them.
            </p>
          </div>
        </section>
        <LogosBar />
        <PainPoints />
        <Solution />
        <HowItWorks />
        <FeaturesGrid />
        <UninstallWall />
        <ComparisonTable />
        <PricingPreview installHref={installHref} />
        <Testimonials />
        <section id="faq" className="relative py-24">
          <div className="mx-auto max-w-7xl px-6">
            <div className="mx-auto max-w-2xl text-center">
              <h2 className="font-display text-4xl font-extrabold tracking-tight text-white sm:text-5xl">
                Frequently asked <span className="text-gradient-cyan">questions</span>
              </h2>
              <p className="mt-4 text-base text-slate-400">
                Everything you need to know before installing.
              </p>
            </div>
            <div className="mt-12">
              <FAQ />
            </div>
          </div>
        </section>
        <FooterCTA installHref={installHref} />
        <Footer />
      </div>

      <ShopInputModal open={showModal} onClose={closeModal} />
    </InstallModalContext.Provider>
  );
}
