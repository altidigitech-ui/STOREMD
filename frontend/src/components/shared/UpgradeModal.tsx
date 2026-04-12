"use client";

import { useState } from "react";
import { Check } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import type { Plan } from "@/types";

interface UpgradeModalProps {
  open: boolean;
  onClose: () => void;
  feature: string;
  requiredPlan: Exclude<Plan, "free">;
  currentPlan: Plan;
}

const PLAN_PRICE: Record<Exclude<Plan, "free">, string> = {
  starter: "$39/month",
  pro: "$99/month",
  agency: "$249/month",
};

const PLAN_BENEFITS: Record<Exclude<Plan, "free">, string[]> = {
  starter: [
    "Weekly scans",
    "100 product analyses",
    "App impact scanner",
    "Residue detector",
    "One-click fixes (20/month)",
    "Weekly email report",
  ],
  pro: [
    "Daily scans",
    "1,000 product analyses",
    "Visual Store Test",
    "Real User Simulation",
    "Accessibility Live Test",
    "Bulk operations",
  ],
  agency: [
    "10 stores",
    "Unlimited product analyses",
    "API access",
    "White-label reports",
    "Priority support",
  ],
};

export function UpgradeModal({
  open,
  onClose,
  feature,
  requiredPlan,
}: UpgradeModalProps) {
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const planLabel =
    requiredPlan.charAt(0).toUpperCase() + requiredPlan.slice(1);

  async function handleUpgrade() {
    setLoading(true);
    try {
      const { checkout_url } = await api.billing.createCheckout(requiredPlan);
      window.location.href = checkout_url;
    } catch (e) {
      toast({
        title: "Checkout failed",
        description:
          e instanceof ApiError
            ? e.message
            : "Payment setup failed. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onClose={onClose} testId="upgrade-modal">
      <div>
        <h2 className="text-base font-semibold text-gray-900">
          {feature} requires {planLabel}
        </h2>
        <p className="mt-1 text-sm text-gray-600">
          Upgrade to {planLabel} ({PLAN_PRICE[requiredPlan]}) to unlock:
        </p>
        <ul className="mt-3 space-y-2">
          {PLAN_BENEFITS[requiredPlan].map((benefit) => (
            <li
              key={benefit}
              className="flex items-center gap-2 text-sm text-gray-700"
            >
              <Check className="h-4 w-4 text-green-600" aria-hidden />
              {benefit}
            </li>
          ))}
        </ul>

        <div className="mt-5 flex items-center justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Maybe later
          </Button>
          <Button onClick={handleUpgrade} disabled={loading}>
            {loading ? "Loading..." : `Upgrade to ${planLabel} →`}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
