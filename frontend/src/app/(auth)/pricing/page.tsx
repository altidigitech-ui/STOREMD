import { PricingClient } from "@/components/landing/PricingClient";

export const metadata = {
  title: "StoreMD — Pricing",
  description:
    "Simple pricing. No surprises. Start free. Upgrade when you need more.",
};

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-white">
      <div className="mx-auto max-w-6xl px-6 py-16">
        <header className="mb-10 text-center">
          <h1 className="text-3xl font-bold sm:text-4xl">
            Simple pricing. No surprises.
          </h1>
          <p className="mt-3 text-base text-gray-600">
            Start free. Upgrade when you need more.
          </p>
        </header>
        <PricingClient />
        <footer className="mt-12 text-center text-sm text-gray-500">
          <p>All plans include:</p>
          <ul className="mt-2 inline-flex flex-wrap justify-center gap-3">
            <li>✓ Instant cancellation, zero fees</li>
            <li>✓ No code injected in your theme</li>
            <li>✓ Data encrypted and isolated</li>
            <li>✓ GDPR compliant</li>
          </ul>
          <p className="mt-4 italic text-gray-400">
            &ldquo;Unlike some apps, we don&apos;t charge you after you
            uninstall.&rdquo;
          </p>
        </footer>
      </div>
    </div>
  );
}
