"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface PricingPreviewProps {
  installHref: string;
}

const TIERS = [
  {
    id: "free",
    name: "Free",
    price: "$0",
    cadence: "forever",
    blurb: "Try StoreMD risk-free",
    features: [
      "1 full audit",
      "2 scans per month",
      "Health score + Listing optimizer",
      "Email alerts",
    ],
    cta: "Start free",
  },
  {
    id: "starter",
    name: "Starter",
    price: "$39",
    cadence: "/month",
    blurb: "For active merchants",
    features: [
      "Everything in Free",
      "Weekly scans",
      "App impact analysis",
      "Code residue detection",
      "Security monitoring",
      "Ghost billing detection",
    ],
    cta: "Upgrade to Starter",
    popular: true,
  },
  {
    id: "pro",
    name: "Pro",
    price: "$99",
    cadence: "/month",
    blurb: "For serious stores",
    features: [
      "Everything in Starter",
      "Daily scans",
      "Real browser testing",
      "Visual diffs",
      "AI readiness score",
      "Priority support",
    ],
    cta: "Upgrade to Pro",
  },
];

export function PricingPreview({ installHref }: PricingPreviewProps) {
  return (
    <section className="bg-white" id="pricing">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold text-gray-900 sm:text-4xl">
            Simple pricing. Start free.
          </h2>
          <p className="mt-3 text-base text-gray-600">
            No credit card required. Cancel anytime. Upgrade when you&apos;re
            ready.
          </p>
        </div>

        <div className="mt-14 grid grid-cols-1 gap-6 md:grid-cols-3">
          {TIERS.map((tier, i) => (
            <motion.div
              key={tier.id}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              whileHover={{ y: -4 }}
              className={cn(
                "relative flex flex-col rounded-2xl border bg-white p-8 transition-shadow",
                tier.popular
                  ? "border-blue-500 shadow-xl shadow-blue-600/10"
                  : "border-gray-200 shadow-sm hover:shadow-md",
              )}
            >
              {tier.popular && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-gradient-to-r from-blue-600 to-blue-500 px-4 py-1 text-xs font-bold uppercase tracking-wide text-white shadow-md">
                  Most Popular
                </span>
              )}

              <div>
                <h3 className="text-lg font-semibold text-gray-900">
                  {tier.name}
                </h3>
                <p className="mt-1 text-sm text-gray-500">{tier.blurb}</p>
              </div>

              <div className="mt-5 flex items-baseline gap-1">
                <span className="text-4xl font-bold text-gray-900">
                  {tier.price}
                </span>
                <span className="text-sm text-gray-500">{tier.cadence}</span>
              </div>

              <ul className="mt-6 flex-1 space-y-3">
                {tier.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm">
                    <Check
                      className="mt-0.5 h-4 w-4 flex-shrink-0 text-green-600"
                      aria-hidden
                    />
                    <span className="text-gray-700">{f}</span>
                  </li>
                ))}
              </ul>

              <Link
                href={tier.id === "free" ? installHref : "/pricing"}
                className={cn(
                  "mt-8 inline-flex w-full items-center justify-center rounded-lg px-4 py-3 text-sm font-semibold transition-colors",
                  tier.popular
                    ? "bg-blue-600 text-white hover:bg-blue-700"
                    : "border border-gray-300 bg-white text-gray-900 hover:bg-gray-50",
                )}
              >
                {tier.cta}
              </Link>
            </motion.div>
          ))}
        </div>

        <p className="mt-8 text-center text-sm text-gray-500">
          Need Agency ($249/mo) with 10 stores and white-label?{" "}
          <Link href="/pricing" className="text-blue-600 hover:underline">
            See full pricing →
          </Link>
        </p>
      </div>
    </section>
  );
}
