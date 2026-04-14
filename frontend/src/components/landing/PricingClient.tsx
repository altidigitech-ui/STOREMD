"use client";

import { useState } from "react";
import { Check } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import type { Plan } from "@/types";

interface PlanDef {
  id: Plan;
  name: string;
  price: string;
  features: string[];
  mostPopular?: boolean;
}

const PLANS: PlanDef[] = [
  {
    id: "free",
    name: "Free",
    price: "$0/month",
    features: [
      "1 full health audit",
      "2 scans per month",
      "5 product analyses",
      "Health score + trend",
      "Fix recommendations",
    ],
  },
  {
    id: "starter",
    name: "Starter",
    price: "$29/month",
    features: [
      "Everything in Free",
      "Weekly scans",
      "100 product analyses",
      "App impact scanner",
      "Residue detector",
      "Ghost billing detector",
      "One-click fixes (20/month)",
      "Weekly email report",
      "Agentic readiness score",
      "Accessibility scanner",
    ],
  },
  {
    id: "pro",
    name: "Pro",
    price: "$79/month",
    mostPopular: true,
    features: [
      "Everything in Starter",
      "Daily scans",
      "1,000 product analyses",
      "3 stores",
      "Bulk operations",
      "Visual Store Test",
      "Real User Simulation",
      "Accessibility Live Test",
      "Bot traffic filter",
      "AI crawler monitor",
      "Benchmark",
    ],
  },
  {
    id: "agency",
    name: "Agency",
    price: "$199/month",
    features: [
      "Everything in Pro",
      "10 stores",
      "Unlimited product analyses",
      "API access",
      "White-label reports",
      "Priority support",
    ],
  },
];

export function PricingClient() {
  const [loading, setLoading] = useState<Plan | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSelect(plan: Plan) {
    if (plan === "free") {
      const installHref = process.env.NEXT_PUBLIC_BACKEND_URL
        ? `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/auth/install`
        : "/api/v1/auth/install";
      window.location.href = installHref;
      return;
    }

    setLoading(plan);
    setError(null);
    try {
      const { checkout_url } = await api.billing.createCheckout(plan);
      window.location.href = checkout_url;
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.message
          : "Could not start checkout. Please try again.",
      );
    } finally {
      setLoading(null);
    }
  }

  return (
    <>
      {error && (
        <p className="mb-4 text-center text-sm text-red-400">{error}</p>
      )}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        {PLANS.map((plan) => (
          <div
            key={plan.id}
            className={cn(
              "relative flex flex-col rounded-2xl border p-7 backdrop-blur-xl",
              plan.mostPopular
                ? "border-cyan-500/50 bg-gradient-to-b from-cyan-500/10 to-white/[0.02] shadow-glow"
                : "border-white/10 bg-white/[0.04]",
            )}
          >
            {plan.mostPopular && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-cyan-500 px-3 py-1 font-display text-[10px] font-bold uppercase tracking-[0.15em] text-black shadow-glow-sm">
                MOST POPULAR
              </span>
            )}
            <h2 className="font-display text-xl font-bold text-white">
              {plan.name}
            </h2>
            <p className="mt-2 font-display text-4xl font-extrabold text-white">
              {plan.price}
            </p>
            <ul className="mt-5 flex-1 space-y-2.5 text-sm text-slate-300">
              {plan.features.map((f) => (
                <li key={f} className="flex items-start gap-2">
                  <Check
                    className="mt-0.5 h-4 w-4 flex-shrink-0 text-cyan-400"
                    aria-hidden
                  />
                  <span>{f}</span>
                </li>
              ))}
            </ul>
            <div className="mt-6">
              <Button
                className="w-full"
                variant={plan.mostPopular ? "default" : "outline"}
                disabled={loading !== null}
                onClick={() => handleSelect(plan.id)}
              >
                {loading === plan.id
                  ? "Loading..."
                  : plan.id === "free"
                    ? "Add to Shopify"
                    : `Upgrade to ${plan.name}`}
              </Button>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
