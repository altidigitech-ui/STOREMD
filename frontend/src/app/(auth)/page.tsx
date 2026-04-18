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
    "StoreMD — One app. Five killed. Zero regrets.",
  description:
    "Stop paying 5 Shopify apps $150/month to send you reports you never read. StoreMD replaces your SEO, speed, accessibility, broken link and audit apps with one AI agent that actually fixes problems.",
  alternates: {
    canonical: "https://storemd.vercel.app",
  },
  openGraph: {
    title: "StoreMD — One app. Five killed. Zero regrets.",
    description:
      "The only Shopify app that uninstalls the others. Replace 5 apps with one agent that actually fixes what's broken. Save $600/year. Faster store. No more PDFs.",
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
    title: "StoreMD — One app. Five killed. Zero regrets.",
    description:
      "The only Shopify app that uninstalls the others. Replace 5 with one agent that actually fixes what's broken.",
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
