import Link from "next/link";
import {
  Activity,
  Bolt,
  Sparkles,
  FileText,
  MonitorSmartphone,
  Wand2,
  Check,
} from "lucide-react";
import { FAQ } from "@/components/landing/FAQ";

export const metadata = {
  title: "StoreMD — Your Shopify store health score in 60 seconds. Free.",
  description:
    "StoreMD is an AI agent that monitors your store 24/7. Speed, apps, SEO, listings, AI readiness — one dashboard.",
};

const FEATURES = [
  {
    icon: Activity,
    title: "Health Score 24/7",
    body: "Your store gets a score out of 100. Mobile and desktop. Updated daily. Get alerts when it drops.",
  },
  {
    icon: Bolt,
    title: "See which apps slow you down",
    body: 'StoreMD measures the exact impact of each app on your load time. "Privy adds 1.8 seconds." Not guessing — measuring.',
  },
  {
    icon: Sparkles,
    title: "Ready for ChatGPT Shopping?",
    body: "Shopify now sells through AI agents. StoreMD checks if your products are visible to ChatGPT, Copilot, and Gemini.",
  },
  {
    icon: FileText,
    title: "Optimize every product listing",
    body: "Score each product out of 100. Title, description, images, SEO. Fix the weakest ones first — prioritized by revenue.",
  },
  {
    icon: MonitorSmartphone,
    title: "See your store like a customer",
    body: "StoreMD simulates a real purchase path. Homepage → Product → Cart → Checkout. Measures real load times.",
  },
  {
    icon: Wand2,
    title: "Not just diagnosis. Action.",
    body: "Missing alt text? Generated and applied. Broken link? Redirect created. Ghost code? Removed. Preview before applying. Always reversible.",
  },
];

const HOW_IT_WORKS = [
  {
    title: "Install in 1 click",
    body: "Add StoreMD from the Shopify App Store. No signup, no configuration. Just click.",
  },
  {
    title: "Get your score in 60 seconds",
    body: "StoreMD scans your store automatically. Speed, apps, code, listings, AI readiness. Your health score appears in under a minute.",
  },
  {
    title: "Fix issues in 1 click",
    body: "Each issue comes with a clear fix. Alt text missing? Generated and applied in 1 click. Ghost code from old apps? Removed automatically.",
  },
];

export default function LandingPage() {
  const installHref = process.env.NEXT_PUBLIC_BACKEND_URL
    ? `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/auth/install`
    : "/api/v1/auth/install";

  return (
    <div className="min-h-screen bg-white text-gray-900">
      {/* HERO */}
      <section className="border-b border-gray-100 bg-white">
        <div className="mx-auto max-w-5xl px-6 py-20 text-center">
          <h1 className="text-4xl font-bold leading-tight sm:text-5xl">
            Your Shopify store health score in 60 seconds.
            <br />
            <span className="text-blue-600">Free.</span>
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-base text-gray-600 sm:text-lg">
            StoreMD is an AI agent that monitors your store 24/7. Speed, apps,
            SEO, listings, AI readiness — one dashboard.
          </p>
          <div className="mt-8">
            <Link
              href={installHref}
              className="inline-flex items-center justify-center rounded-md bg-blue-600 px-6 py-3 text-base font-medium text-white hover:bg-blue-700"
            >
              Add to Shopify — Free
            </Link>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="border-b border-gray-100 bg-gray-50">
        <div className="mx-auto max-w-5xl px-6 py-16">
          <h2 className="text-center text-2xl font-bold">How it works</h2>
          <div className="mt-10 grid grid-cols-1 gap-8 md:grid-cols-3">
            {HOW_IT_WORKS.map((step, i) => (
              <div key={step.title}>
                <div className="mb-3 inline-flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-sm font-semibold text-blue-700">
                  {i + 1}
                </div>
                <h3 className="text-lg font-semibold">{step.title}</h3>
                <p className="mt-2 text-sm text-gray-600">{step.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FEATURE CARDS */}
      <section className="border-b border-gray-100 bg-white">
        <div className="mx-auto max-w-5xl px-6 py-16">
          <h2 className="text-center text-2xl font-bold">
            Six modules. One app.
          </h2>
          <div className="mt-10 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f) => {
              const Icon = f.icon;
              return (
                <div
                  key={f.title}
                  className="rounded-lg border border-gray-200 p-5 hover:shadow-md transition-shadow"
                >
                  <Icon className="h-6 w-6 text-blue-600" aria-hidden />
                  <h3 className="mt-3 text-base font-semibold">{f.title}</h3>
                  <p className="mt-2 text-sm text-gray-600">{f.body}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* SOCIAL PROOF */}
      <section className="bg-gray-50 border-b border-gray-100">
        <div className="mx-auto max-w-3xl px-6 py-14 text-center">
          <p className="text-base font-medium text-gray-800">
            Built from 530+ competitor app reviews
          </p>
          <p className="mt-1 text-sm text-gray-500">
            Analyzed 600+ merchant pain points on Reddit · 12 features no
            other Shopify app has
          </p>
        </div>
      </section>

      {/* ANTI APP BLOAT */}
      <section className="border-b border-gray-100 bg-white">
        <div className="mx-auto max-w-3xl px-6 py-14 text-center">
          <h2 className="text-2xl font-bold">We practice what we preach</h2>
          <p className="mt-3 text-base text-gray-600">
            StoreMD tells you &ldquo;you have too many apps.&rdquo; That&apos;s
            why StoreMD is ONE app with 5 modules — not 5 separate apps.
            Health, Listings, AI Ready, Compliance, and Browser Testing. One
            install.
          </p>
          <ul className="mt-4 inline-flex flex-wrap justify-center gap-2 text-sm text-gray-700">
            {[
              "Instant cancellation",
              "No code injected",
              "Data encrypted",
              "GDPR compliant",
            ].map((item) => (
              <li
                key={item}
                className="flex items-center gap-1 rounded-full border border-gray-200 px-3 py-1"
              >
                <Check className="h-3 w-3 text-green-600" aria-hidden />
                {item}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* FAQ */}
      <section className="border-b border-gray-100 bg-gray-50">
        <div className="mx-auto max-w-3xl px-6 py-16">
          <h2 className="text-center text-2xl font-bold">
            Frequently asked questions
          </h2>
          <div className="mt-8">
            <FAQ />
          </div>
        </div>
      </section>

      {/* FOOTER CTA */}
      <section className="bg-white">
        <div className="mx-auto max-w-3xl px-6 py-16 text-center">
          <h2 className="text-3xl font-bold">
            Your store deserves a doctor.
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Free plan includes 1 full audit + 2 scans/month. No credit card
            required.
          </p>
          <div className="mt-6">
            <Link
              href={installHref}
              className="inline-flex items-center justify-center rounded-md bg-blue-600 px-6 py-3 text-base font-medium text-white hover:bg-blue-700"
            >
              Add to Shopify — Free
            </Link>
          </div>
          <p className="mt-10 text-xs text-gray-400">
            <Link href="/pricing" className="hover:underline">
              See pricing
            </Link>
          </p>
        </div>
      </section>
    </div>
  );
}
