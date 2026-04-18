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
    "StoreMD — While you sleep, your store fixes itself.",
  description:
    "Other apps give you reports. StoreMD fixes the problem. An AI agent tests your store every night, finds what's losing you sales, and fixes it before you wake up.",
  alternates: {
    canonical: "https://storemd.vercel.app",
  },
  openGraph: {
    title: "StoreMD — Your store is losing $2,400/month. You have no idea.",
    description:
      "An AI agent that fixes your Shopify store while you sleep. Stop paying for 5 audit apps that do nothing. Start waking up to a store that made you more money overnight.",
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
    title: "StoreMD — While you sleep, your store fixes itself.",
    description:
      "The AI agent that actually uses your Shopify store at night and fixes what's losing you sales.",
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
      <section className="relative border-y border-white/5 bg-[#0a0a0f] py-14">
        <div className="mx-auto max-w-7xl px-6 text-center">
          <h2 className="font-display text-3xl font-extrabold tracking-tight text-white sm:text-4xl lg:text-5xl">
            1 agent.{" "}
            <span className="text-gradient-cyan">5 apps replaced.</span>{" "}
            $600/year saved.
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
