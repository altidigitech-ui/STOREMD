import { PricingClient } from "@/components/landing/PricingClient";

export const metadata = {
  title: "StoreMD — Pricing",
  description:
    "Simple pricing. No surprises. Start free. Upgrade when you need more.",
};

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-[#0a0a0f] text-slate-100">
      <div className="mx-auto max-w-6xl px-6 py-16">
        <header className="mb-10 text-center">
          <h1 className="font-display text-3xl font-extrabold text-white sm:text-5xl">
            Simple pricing. <span className="text-gradient-cyan">No surprises.</span>
          </h1>
          <p className="mt-4 text-base text-slate-400">
            Start free. Upgrade when you need more.
          </p>
        </header>
        <PricingClient />
        <footer className="mt-12 text-center text-sm text-slate-400">
          <p>All plans include:</p>
          <ul className="mt-2 inline-flex flex-wrap justify-center gap-3 text-slate-300">
            <li>✓ Instant cancellation, zero fees</li>
            <li>✓ No code injected in your theme</li>
            <li>✓ Data encrypted and isolated</li>
            <li>✓ GDPR compliant</li>
          </ul>
          <p className="mt-4 italic text-slate-500">
            &ldquo;Unlike some apps, we don&apos;t charge you after you
            uninstall.&rdquo;
          </p>
        </footer>
      </div>
    </div>
  );
}
