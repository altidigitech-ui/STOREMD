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
    "StoreMD — Find out how much your Shopify store is losing. Free audit in 60s.",
  description:
    "StoreMD scans your Shopify store in 60 seconds — slow apps, broken tracking, ghost charges, AI readiness. Free plan available. No credit card required.",
  alternates: {
    canonical: "https://storemd.vercel.app",
  },
  openGraph: {
    title:
      "StoreMD — Your Shopify store is losing money. Find out how much.",
    description:
      "StoreMD scans your Shopify store in 60 seconds — speed, apps, SEO, security. Free plan available.",
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
    title: "StoreMD — Your Shopify store is losing money.",
    description:
      "Free health score in 60 seconds. Speed, apps, SEO, security.",
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
