import { Hero } from "@/components/landing/Hero";
import { LandingNavbar } from "@/components/landing/LandingNavbar";
import { LogosBar } from "@/components/landing/LogosBar";
import { PainPoints } from "@/components/landing/PainPoints";
import { Solution } from "@/components/landing/Solution";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { FeaturesGrid } from "@/components/landing/FeaturesGrid";
import { PricingPreview } from "@/components/landing/PricingPreview";
import { Testimonials } from "@/components/landing/Testimonials";
import { FAQ } from "@/components/landing/FAQ";
import { FooterCTA } from "@/components/landing/FooterCTA";
import { Footer } from "@/components/landing/Footer";

export const metadata = {
  title:
    "StoreMD — One Shopify app replaces 5. Save $140/mo. Faster store.",
  description:
    "StoreMD replaces Analyzify, SEO King, PageSpeed, Accessibly & broken link checkers. One dashboard, one script, one bill. Free audit in 60s.",
  alternates: {
    canonical: "https://storemd.vercel.app",
  },
  openGraph: {
    title: "StoreMD — Uninstall 5 Shopify apps. Install one.",
    description:
      "Replace your SEO, speed, audit, accessibility & link checker apps with one. Save $140/mo. Load 1s faster.",
    url: "https://storemd.vercel.app",
    siteName: "StoreMD",
    type: "website",
    images: [
      {
        url: "https://storemd.vercel.app/og-image.png",
        width: 1200,
        height: 630,
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "StoreMD — Uninstall 5 apps. Install one.",
    description:
      "One Shopify app replaces Analyzify, SEO King, PageSpeed, Accessibly & more. Save $140/mo.",
    images: ["https://storemd.vercel.app/og-image.png"],
  },
};

export default function LandingPage() {
  const installHref = process.env.NEXT_PUBLIC_BACKEND_URL
    ? `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/auth/install`
    : "/api/v1/auth/install";

  return (
    <div className="relative min-h-screen bg-[#0a0a0f] font-sans text-slate-100 antialiased">
      <LandingNavbar installHref={installHref} />
      <Hero installHref={installHref} />
      <LogosBar />
      <PainPoints />
      <Solution />
      <HowItWorks />
      <FeaturesGrid />
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
  );
}
