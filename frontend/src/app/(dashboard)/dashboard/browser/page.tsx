"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { UpgradeModal } from "@/components/shared/UpgradeModal";
import { Card, CardContent, CardTitle } from "@/components/ui/Card";
import { api, ApiError } from "@/lib/api";
import { getSupabaseBrowserClient } from "@/lib/supabase";
import { useCurrentStore } from "@/hooks/use-current-store";
import { cn } from "@/lib/utils";
import type {
  AccessibilityResponse,
  Plan,
  SimulationResponse,
  SimulationStep,
  VisualDeviceDiff,
  VisualDiffResponse,
} from "@/types";

const PLAN_RANK: Record<Plan, number> = {
  free: 0,
  starter: 1,
  pro: 2,
  agency: 3,
};

interface BrowserData {
  visual: VisualDiffResponse;
  simulation: SimulationResponse;
  accessibility: AccessibilityResponse | null;
}

export default function BrowserPage() {
  const { storeId } = useCurrentStore();
  const [plan, setPlan] = useState<Plan>("free");
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [data, setData] = useState<BrowserData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const locked = PLAN_RANK[plan] < PLAN_RANK.pro;

  const loadBrowserData = useCallback(async (sid: string) => {
    setLoading(true);
    setError(null);
    try {
      const [visual, simulation, accessibility] = await Promise.all([
        api.browser.visualDiff(sid),
        api.browser.simulation(sid),
        api.compliance.accessibility(sid, true).catch(() => null),
      ]);
      setData({ visual, simulation, accessibility });
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.message
          : "Failed to load browser test results",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const supabase = getSupabaseBrowserClient();
      const { data: session } = await supabase.auth.getSession();
      const meta = (session.session?.user.user_metadata ?? {}) as Record<
        string,
        unknown
      >;
      const current = (meta.plan as Plan | undefined) ?? "free";
      if (cancelled) return;
      setPlan(current);
      if (PLAN_RANK[current] < PLAN_RANK.pro) {
        setShowUpgrade(true);
        setLoading(false);
        return;
      }
      if (!storeId) {
        setLoading(false);
        return;
      }
      await loadBrowserData(storeId);
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [storeId, loadBrowserData]);

  if (locked) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">Browser Tests</h1>
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
      </div>
    );
  }

  if (loading) return <LoadingState />;
  if (error) {
    return (
      <ErrorState
        message={error}
        onRetry={storeId ? () => loadBrowserData(storeId) : undefined}
      />
    );
  }
  if (!data) return null;

  const visualEmpty =
    !data.visual.screenshots.mobile?.current_url &&
    !data.visual.screenshots.desktop?.current_url;
  const simulationEmpty =
    !data.simulation.total_time_ms && data.simulation.steps.length === 0;
  const accessibilityEmpty =
    !data.accessibility ||
    (data.accessibility.violations_count === 0 && data.accessibility.score === 0);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Browser Tests</h1>

      {/* Visual Store Test */}
      <Card>
        <CardTitle>Visual Store Test</CardTitle>
        <CardContent>
          {visualEmpty ? (
            <p className="text-sm text-gray-500">
              No screenshots yet. Run a scan with the Browser module to
              capture mobile and desktop renders.
            </p>
          ) : (
            <>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <DeviceScreenshot
                  device="mobile"
                  data={data.visual.screenshots.mobile}
                />
                <DeviceScreenshot
                  device="desktop"
                  data={data.visual.screenshots.desktop}
                />
              </div>
              {data.visual.diff_regions.length > 0 && (
                <ul className="mt-4 space-y-1 text-xs text-gray-600">
                  {data.visual.diff_regions.map((region, i) => (
                    <li key={`${region.area}-${i}`}>
                      • {region.area}: {region.change_pct}% changed
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Real User Simulation */}
      <Card>
        <CardTitle>Real User Simulation</CardTitle>
        <CardContent>
          {simulationEmpty ? (
            <p className="text-sm text-gray-500">
              No simulation results yet. The next browser scan will time the
              full purchase path.
            </p>
          ) : (
            <>
              <p className="text-sm text-gray-700">
                Total purchase path:{" "}
                <span className="font-semibold">
                  {(data.simulation.total_time_ms / 1000).toFixed(1)}s
                </span>
                {data.simulation.bottleneck_step && (
                  <span className="ml-2 text-gray-500">
                    · bottleneck: {data.simulation.bottleneck_step}
                  </span>
                )}
              </p>
              <ol className="mt-3 space-y-2">
                {data.simulation.steps.map((step, idx) => (
                  <SimulationRow key={`${step.name}-${idx}`} step={step} />
                ))}
              </ol>
              {data.simulation.bottleneck_cause && (
                <p className="mt-3 flex items-start gap-2 rounded-md bg-yellow-50 p-2 text-xs text-yellow-800">
                  <AlertTriangle className="mt-0.5 h-3 w-3" aria-hidden />
                  {data.simulation.bottleneck_cause}
                </p>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Accessibility Live */}
      <Card>
        <CardTitle>Accessibility Live</CardTitle>
        <CardContent>
          {accessibilityEmpty ? (
            <p className="text-sm text-gray-500">
              No live accessibility scan yet. Triggered by the Browser module.
            </p>
          ) : (
            <>
              <p className="text-sm text-gray-700">
                Score:{" "}
                <span className="font-semibold">
                  {data.accessibility?.score ?? 0}/100
                </span>
                {data.accessibility?.eaa_compliant ? (
                  <span className="ml-2 text-green-600">EAA compliant ✓</span>
                ) : (
                  <span className="ml-2 text-orange-600">
                    EAA non-compliant
                  </span>
                )}
              </p>
              <ul className="mt-3 divide-y divide-gray-100">
                {data.accessibility?.violations.map((v, i) => (
                  <li
                    key={`${v.rule}-${i}`}
                    className="flex items-start justify-between py-2 text-sm"
                  >
                    <div>
                      <p className="font-medium text-gray-900">{v.rule}</p>
                      {v.fix_description && (
                        <p className="text-xs text-gray-500">
                          {v.fix_description}
                        </p>
                      )}
                    </div>
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-xs",
                        v.severity === "critical" &&
                          "bg-red-50 text-red-700",
                        v.severity === "major" &&
                          "bg-orange-50 text-orange-700",
                        v.severity === "minor" &&
                          "bg-yellow-50 text-yellow-700",
                        v.severity === "info" &&
                          "bg-blue-50 text-blue-700",
                      )}
                    >
                      {v.count} · {v.severity}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function DeviceScreenshot({
  device,
  data,
}: {
  device: "mobile" | "desktop";
  data?: VisualDeviceDiff;
}) {
  if (!data || !data.current_url) {
    return (
      <div className="rounded-md border border-dashed border-gray-300 p-3 text-xs text-gray-500">
        No {device} screenshot
      </div>
    );
  }
  return (
    <div className="rounded-md border border-gray-200 p-3">
      <div className="flex items-baseline justify-between text-xs">
        <span className="font-medium capitalize text-gray-700">{device}</span>
        {data.diff_pct != null && (
          <span
            className={cn(
              "text-xs",
              data.significant_change
                ? "text-orange-600"
                : "text-gray-500",
            )}
          >
            {data.diff_pct}% changed
          </span>
        )}
      </div>
      <div className="mt-2 grid grid-cols-2 gap-2">
        {data.previous_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={data.previous_url}
            alt={`Previous ${device} screenshot`}
            className="max-h-72 w-full rounded border border-gray-200 object-contain"
          />
        )}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={data.current_url}
          alt={`Current ${device} screenshot`}
          className={cn(
            "max-h-72 w-full rounded border border-gray-200 object-contain",
            !data.previous_url && "col-span-2",
          )}
        />
      </div>
    </div>
  );
}

function SimulationRow({ step }: { step: SimulationStep }) {
  return (
    <li
      className={cn(
        "flex items-baseline justify-between rounded-md border px-3 py-2 text-sm",
        step.bottleneck
          ? "border-orange-200 bg-orange-50"
          : "border-gray-200 bg-white",
      )}
    >
      <div className="min-w-0">
        <p className="font-medium text-gray-900">{step.name}</p>
        {step.url && (
          <p className="truncate text-xs text-gray-500">{step.url}</p>
        )}
      </div>
      <div className="text-right text-xs">
        <span
          className={cn(
            "font-semibold",
            step.bottleneck ? "text-orange-700" : "text-gray-700",
          )}
        >
          {(step.time_ms / 1000).toFixed(1)}s
        </span>
        {step.bottleneck && (
          <p className="mt-1 text-xs text-orange-700">Bottleneck</p>
        )}
      </div>
    </li>
  );
}
