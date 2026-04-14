import { Hero } from "@/components/landing/Hero";
import { LandingNavbar } from "@/components/landing/LandingNavbar";
import { PainPoints } from "@/components/landing/PainPoints";
import { Solution } from "@/components/landing/Solution";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { AntiBloat } from "@/components/landing/AntiBloat";
import { PricingPreview } from "@/components/landing/PricingPreview";
import { FAQ } from "@/components/landing/FAQ";
import { FooterCTA } from "@/components/landing/FooterCTA";

export const metadata = {
  title:
    "StoreMD — Find out how much your Shopify store is losing. Free audit in 60s.",
  description:
    "StoreMD scans your Shopify store in 60 seconds — slow apps, broken tracking, ghost charges, AI readiness. Free plan available. No credit card required.",
};

export default function LandingPage() {
  const installHref = process.env.NEXT_PUBLIC_BACKEND_URL
    ? `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/auth/install`
    : "/api/v1/auth/install";

  return (
    <div className="min-h-screen bg-white text-gray-900">
      <LandingNavbar />
      <Hero installHref={installHref} />
      <PainPoints />
      <Solution />
      <HowItWorks />
      <AntiBloat />
      <PricingPreview installHref={installHref} />
      <section id="faq" className="border-t border-gray-100 bg-gray-50">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold text-gray-900 sm:text-4xl">
              Frequently asked questions
            </h2>
            <p className="mt-3 text-base text-gray-600">
              Everything you need to know before installing.
            </p>
          </div>
          <div className="mt-10">
            <FAQ />
          </div>
        </div>
      </section>
      <FooterCTA installHref={installHref} />
    </div>
  );
}
