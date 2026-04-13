import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy Policy — StoreMD",
  description:
    "How StoreMD collects, uses, and protects merchant data on the Shopify platform.",
};

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-gray-50 py-16 px-6">
      <div className="mx-auto max-w-3xl">
        <Link
          href="/"
          className="text-sm text-blue-600 hover:text-blue-700"
        >
          ← Back to StoreMD
        </Link>

        <h1 className="mt-6 text-4xl font-bold tracking-tight text-gray-900">
          Privacy Policy — StoreMD
        </h1>
        <p className="mt-2 text-sm text-gray-500">Last updated: April 13, 2026</p>

        <div className="mt-10 space-y-8 text-gray-700 leading-relaxed">
          <section>
            <h2 className="text-xl font-semibold text-gray-900">
              What we access
            </h2>
            <p className="mt-2">
              StoreMD reads your store data — products, themes, apps, and script
              tags — to calculate your store health score and generate
              actionable recommendations. We only request the minimum Shopify
              scopes required for our diagnostic features.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900">
              Customer personal data
            </h2>
            <p className="mt-2">
              We do not collect or store customer personal data. StoreMD is a
              merchant-facing diagnostic tool and has no need for end-customer
              PII (names, emails, addresses, payment info).
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900">
              Security & encryption
            </h2>
            <p className="mt-2">
              All store data is encrypted in transit (TLS 1.2+) and at rest.
              Shopify access tokens are encrypted with Fernet (AES-128) in our
              database. Our infrastructure runs on Railway and Supabase with
              SOC 2 compliant hosting.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900">
              Data retention & deletion
            </h2>
            <p className="mt-2">
              When you uninstall StoreMD from your Shopify admin, we
              automatically purge all data associated with your store via the
              GDPR <code className="rounded bg-gray-100 px-1.5 py-0.5 text-sm">
                shop/redact
              </code>{" "}
              webhook (fired by Shopify 48 hours after uninstall). You may also
              request immediate deletion by contacting us.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900">
              Third parties
            </h2>
            <p className="mt-2">
              We do not sell or share your data with third parties. We use
              operational sub-processors (Supabase for database, Railway for
              hosting, Stripe for billing, Anthropic for AI analysis, Sentry
              for error monitoring) strictly to run the service.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900">Your rights</h2>
            <p className="mt-2">
              You can request access, correction, or deletion of your data at
              any time. Shopify-initiated GDPR webhooks (
              <code className="rounded bg-gray-100 px-1.5 py-0.5 text-sm">
                customers/data_request
              </code>
              ,{" "}
              <code className="rounded bg-gray-100 px-1.5 py-0.5 text-sm">
                customers/redact
              </code>
              ,{" "}
              <code className="rounded bg-gray-100 px-1.5 py-0.5 text-sm">
                shop/redact
              </code>
              ) are honored within the timelines required by Shopify.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900">Contact</h2>
            <p className="mt-2">
              Questions, requests, or concerns? Email us at{" "}
              <a
                href="mailto:altidigitech@gmail.com"
                className="text-blue-600 hover:text-blue-700"
              >
                altidigitech@gmail.com
              </a>
              .
            </p>
          </section>
        </div>
      </div>
    </main>
  );
}
