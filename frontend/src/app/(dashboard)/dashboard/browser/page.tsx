"use client";

import { useEffect, useState } from "react";
import { EmptyState } from "@/components/shared/EmptyState";
import { UpgradeModal } from "@/components/shared/UpgradeModal";
import { getSupabaseBrowserClient } from "@/lib/supabase";
import type { Plan } from "@/types";

const PLAN_RANK: Record<Plan, number> = {
  free: 0,
  starter: 1,
  pro: 2,
  agency: 3,
};

export default function BrowserPage() {
  const [plan, setPlan] = useState<Plan>("free");
  const [showUpgrade, setShowUpgrade] = useState(false);

  useEffect(() => {
    async function load() {
      const supabase = getSupabaseBrowserClient();
      const { data } = await supabase.auth.getSession();
      const meta = (data.session?.user.user_metadata ?? {}) as Record<
        string,
        unknown
      >;
      const current = (meta.plan as Plan | undefined) ?? "free";
      setPlan(current);
      if (PLAN_RANK[current] < PLAN_RANK.pro) {
        setShowUpgrade(true);
      }
    }
    load();
  }, []);

  const locked = PLAN_RANK[plan] < PLAN_RANK.pro;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Browser Tests</h1>

      {locked ? (
        <>
          <EmptyState
            title="Browser Tests — Pro plan"
            message="See your store exactly as customers see it. Visual change detection, real purchase path simulation, and accessibility testing in real browser conditions."
          />
          <UpgradeModal
            open={showUpgrade}
            onClose={() => setShowUpgrade(false)}
            feature="Browser Tests"
            requiredPlan="pro"
            currentPlan={plan}
          />
        </>
      ) : (
        <EmptyState
          title="Coming in Phase 5"
          message="Visual diff, user simulation, and accessibility live test views will ship in the next phase."
        />
      )}
    </div>
  );
}
