"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { InstallLink } from "./InstallLink";

interface PricingPreviewProps {
  installHref: string;
}

interface Tier {
  id: string;
  name: string;
  price: string;
  cadence: string;
  blurb: string;
  features: string[];
  cta: string;
  popular?: boolean;
}

const TIERS: Tier[] = [
  {
    id: "free",
    name: "Free",
    price: "$0",
    cadence: "/month",
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
    price: "$29",
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
  },
  {
    id: "pro",
    name: "Pro",
    price: "$79",
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
    popular: true,
  },
  {
    id: "agency",
    name: "Agency",
    price: "$199",
    cadence: "/month",
    blurb: "For agencies & power users",
    features: [
      "Everything in Pro",
      "Unlimited scans",
      "Multi-store support",
      "Dedicated account manager",
      "Custom integrations",
    ],
    cta: "Upgrade to Agency",
  },
];

export function PricingPreview({ installHref }: PricingPreviewProps) {
  return (
    <section className="relative bg-[#0d1117] py-24" id="pricing">
      <div
        className="absolute inset-x-0 top-0 -z-10 h-px bg-gradient-to-r from-transparent via-cyan-500/40 to-transparent"
        aria-hidden
      />
      <div className="mx-auto max-w-7xl px-6">
        <div className="mx-auto max-w-2xl text-center">
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="font-display text-4xl font-extrabold tracking-tight text-white sm:text-5xl"
          >
            Simple pricing.{" "}
            <span className="text-gradient-cyan">Start free.</span>
          </motion.h2>
          <p className="mt-4 text-base text-slate-400">
            No credit card required. Cancel anytime. Upgrade when you&apos;re
            ready.
          </p>
        </div>

        <div className="mt-14 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
          {TIERS.map((tier, i) => (
            <motion.div
              key={tier.id}
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: i * 0.08 }}
              className={cn(
                "relative flex flex-col rounded-2xl border p-7 backdrop-blur-xl transition-all",
                tier.popular
                  ? "border-cyan-500/50 bg-gradient-to-b from-cyan-500/[0.08] to-white/[0.02] shadow-glow"
                  : "border-white/10 bg-white/[0.04] hover:border-white/20 hover:bg-white/[0.06]",
              )}
            >
              {tier.popular && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-cyan-500 px-3 py-1 font-display text-[10px] font-bold uppercase tracking-[0.15em] text-black shadow-glow-sm">
                  Most Popular
                </span>
              )}

              <div>
                <h3 className="font-display text-xl font-bold text-white">
                  {tier.name}
                </h3>
                <p className="mt-1.5 text-xs text-slate-400">{tier.blurb}</p>
              </div>

              <div className="mt-5 flex items-baseline gap-1">
                <span className="font-display text-5xl font-extrabold text-white">
                  {tier.price}
                </span>
                <span className="text-sm font-medium text-slate-400">
                  {tier.cadence}
                </span>
              </div>

              <ul className="mt-6 flex-1 space-y-3">
                {tier.features.map((f) => (
                  <li key={f} className="flex items-start gap-2.5 text-sm">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-cyan-400" />
                    <span className="text-slate-300">{f}</span>
                  </li>
                ))}
              </ul>

              {tier.id === "free" ? (
                <InstallLink
                  href={installHref}
                  label={`pricing_${tier.id}_install`}
                  className={cn(
                    "mt-8 inline-flex w-full items-center justify-center rounded-lg px-4 py-3 font-display text-sm font-semibold transition-all",
                    tier.popular
                      ? "bg-cyan-500 text-black shadow-glow-sm hover:bg-cyan-400 hover:shadow-glow"
                      : "border border-white/15 bg-white/5 text-white hover:bg-white/10",
                  )}
                >
                  {tier.cta}
                </InstallLink>
              ) : (
                <Link
                  href="/pricing"
                  className={cn(
                    "mt-8 inline-flex w-full items-center justify-center rounded-lg px-4 py-3 font-display text-sm font-semibold transition-all",
                    tier.popular
                      ? "bg-cyan-500 text-black shadow-glow-sm hover:bg-cyan-400 hover:shadow-glow"
                      : "border border-white/15 bg-white/5 text-white hover:bg-white/10",
                  )}
                >
                  {tier.cta}
                </Link>
              )}
            </motion.div>
          ))}
        </div>

        <p className="mt-10 text-center text-sm text-slate-500">
          Need a custom plan or more details?{" "}
          <Link
            href="/pricing"
            className="text-cyan-400 transition-colors hover:text-cyan-300"
          >
            See full pricing →
          </Link>
        </p>
      </div>
    </section>
  );
}
