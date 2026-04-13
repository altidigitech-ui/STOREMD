"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useCurrentStore } from "@/hooks/use-current-store";
import { ScoreHero } from "@/components/dashboard/ScoreHero";
import { IssuesList } from "@/components/dashboard/IssuesList";
import { TrendChart } from "@/components/dashboard/TrendChart";
import { Card, CardContent, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";
import { useToast } from "@/components/ui/Toast";
import { formatTimeAgo } from "@/lib/utils";
import type {
  HealthResponse,
  Scan,
  ScanDetailResponse,
  StoreAppsResponse,
} from "@/types";

export default function HealthPage() {
  const { storeId, isLoading: loadingStore } = useCurrentStore();
  const { toast } = useToast();

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [latestScan, setLatestScan] = useState<ScanDetailResponse | null>(null);
  const [apps, setApps] = useState<StoreAppsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!storeId) return;
    setIsLoading(true);
    setError(null);
    try {
      const [healthData, scansPage, appsData] = await Promise.all([
        api.scans.getHealth(storeId),
        api.scans.list(storeId, undefined, 1),
        api.stores.getApps(storeId).catch(() => null),
      ]);

      setHealth(healthData);
      setApps(appsData);

      const firstScan: Scan | undefined = scansPage.data[0];
      if (firstScan) {
        const detail = await api.scans.get(storeId, firstScan.id);
        setLatestScan(detail);
      } else {
        setLatestScan(null);
      }
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "Failed to load store health",
      );
    } finally {
      setIsLoading(false);
    }
  }, [storeId]);

  useEffect(() => {
    if (!storeId) return;
    loadData();
  }, [storeId, loadData]);

  async function handleScanNow() {
    if (!storeId) return;
    try {
      await api.scans.create(storeId, ["health"]);
      toast({
        title: "Scan started",
        description: "Results in about 60 seconds.",
      });
      setTimeout(loadData, 3000);
    } catch (e) {
      if (e instanceof ApiError && e.code === "SCAN_LIMIT_REACHED") {
        toast({
          title: "Scan limit reached",
          description: "Upgrade for more scans.",
        });
      } else {
        toast({
          title: "Scan failed",
          description: e instanceof Error ? e.message : "Unknown error",
          variant: "destructive",
        });
      }
    }
  }

  if (loadingStore || isLoading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={loadData} />;

  if (!storeId) {
    return (
      <EmptyState
        title="No store connected"
        message="We could not find a connected Shopify store."
      />
    );
  }

  if (!health || !latestScan) {
    return (
      <EmptyState
        title="No scans yet"
        message="Run your first scan to see your store health score."
        action={<Button onClick={handleScanNow}>Scan now</Button>}
      />
    );
  }

  const trendHistory = (health.history ?? [])
    .slice()
    .reverse()
    .slice(-7)
    .map((h) => ({ date: h.date, score: h.score }));

  return (
    <div className="space-y-6">
      <ScoreHero
        score={health.score}
        mobileScore={health.mobile_score}
        desktopScore={health.desktop_score}
        trend={health.trend}
        trendDelta={Math.abs(health.trend_delta)}
        lastScanAt={health.last_scan_at}
        onScanNow={handleScanNow}
      />

      <IssuesList issues={latestScan.issues ?? []} />

      {trendHistory.length > 1 && (
        <Card>
          <CardTitle>Score trend — 7 days</CardTitle>
          <CardContent>
            <TrendChart data={trendHistory} trend={health.trend} />
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardTitle>App Impact on Speed</CardTitle>
          <CardContent>
            {!apps || apps.data.length === 0 ? (
              apps && !apps.apps_count_known ? (
                <div className="rounded-md bg-amber-50 p-3 text-sm text-amber-800">
                  <p className="font-medium">
                    App analysis requires additional permissions
                  </p>
                  <p className="mt-1 text-xs text-amber-700">
                    StoreMD needs the &quot;read_apps&quot; scope to analyze
                    your installed apps. This will be available in the next
                    update.
                  </p>
                </div>
              ) : (
                <p className="text-sm text-gray-500">
                  No third-party apps detected.
                </p>
              )
            ) : (
              <ul className="divide-y divide-gray-100">
                {apps.data
                  .slice()
                  .sort((a, b) => b.impact_ms - a.impact_ms)
                  .slice(0, 5)
                  .map((app) => (
                    <li
                      key={app.id}
                      className="flex items-center justify-between py-2 text-sm"
                    >
                      <span className="font-medium text-gray-800">
                        {app.name}
                      </span>
                      <span className="text-gray-600">
                        +{(app.impact_ms / 1000).toFixed(1)}s
                      </span>
                    </li>
                  ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardTitle>Quick Stats</CardTitle>
          <CardContent>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-500">Issues</dt>
                <dd className="font-medium">{health.issues_count}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Critical</dt>
                <dd className="font-medium">{health.critical_count}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Last scan</dt>
                <dd className="font-medium">
                  {formatTimeAgo(health.last_scan_at)}
                </dd>
              </div>
            </dl>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
