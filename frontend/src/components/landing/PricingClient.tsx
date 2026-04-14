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
        <p className="mb-4 text-center text-sm text-red-600">{error}</p>
      )}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        {PLANS.map((plan) => (
          <div
            key={plan.id}
            className={cn(
              "relative flex flex-col rounded-lg border bg-white p-6",
              plan.mostPopular
                ? "border-blue-500 shadow-md"
                : "border-gray-200",
            )}
          >
            {plan.mostPopular && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-blue-600 px-3 py-1 text-xs font-semibold text-white">
                MOST POPULAR
              </span>
            )}
            <h2 className="text-lg font-semibold">{plan.name}</h2>
            <p className="mt-1 text-2xl font-bold">{plan.price}</p>
            <ul className="mt-4 flex-1 space-y-2 text-sm text-gray-700">
              {plan.features.map((f) => (
                <li key={f} className="flex items-start gap-2">
                  <Check
                    className="mt-0.5 h-4 w-4 flex-shrink-0 text-green-600"
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
