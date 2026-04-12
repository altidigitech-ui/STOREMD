"use client";

import { useEffect, useState } from "react";
import { ArrowDown, ArrowRight, ArrowUp, Download } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useCurrentStore } from "@/hooks/use-current-store";
import { Card, CardContent, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";
import { cn, getScoreColor } from "@/lib/utils";
import type { WeeklyReportResponse } from "@/types";

export default function ReportsPage() {
  const { storeId, isLoading: loadingStore } = useCurrentStore();
  const [report, setReport] = useState<WeeklyReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!storeId) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await api.reports.latest(storeId);
        if (!cancelled) setReport(data);
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof ApiError
              ? e.message
              : "Failed to load weekly report",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [storeId]);

  if (loadingStore || loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;

  if (!report || (!report.period && !report.score)) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">Weekly report</h1>
        <EmptyState
          title="No report yet"
          message="Your first weekly report will be generated Sunday at 09:00 UTC."
        />
      </div>
    );
  }

  const TrendIcon =
    report.trend === "up"
      ? ArrowUp
      : report.trend === "down"
        ? ArrowDown
        : ArrowRight;
  const trendColor =
    report.trend === "up"
      ? "text-green-600"
      : report.trend === "down"
        ? "text-red-600"
        : "text-gray-500";

  return (
    <div className="space-y-6">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Weekly report</h1>
        <p className="text-xs text-gray-500">{report.period}</p>
      </div>

      <Card>
        <CardContent>
          <div className="flex items-baseline gap-3">
            <p
              className={cn(
                "text-5xl font-bold leading-none",
                getScoreColor(report.score),
              )}
            >
              {report.score}
            </p>
            <p className="text-sm text-gray-500">/100</p>
            <span
              className={cn(
                "ml-3 inline-flex items-center gap-1 text-sm",
                trendColor,
              )}
            >
              <TrendIcon className="h-4 w-4" aria-hidden />
              {report.score_delta > 0 && "+"}
              {report.score_delta} vs last week
            </span>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-md border border-green-200 bg-green-50 p-3">
              <p className="text-xs text-green-700">Issues resolved</p>
              <p className="text-2xl font-semibold text-green-800">
                {report.issues_resolved}
              </p>
            </div>
            <div className="rounded-md border border-orange-200 bg-orange-50 p-3">
              <p className="text-xs text-orange-700">New issues</p>
              <p className="text-2xl font-semibold text-orange-800">
                {report.new_issues}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardTitle>Top action</CardTitle>
        <CardContent>
          <p className="text-sm text-gray-700">{report.top_action}</p>
        </CardContent>
      </Card>

      {report.report_pdf_url && (
        <div>
          <a href={report.report_pdf_url} target="_blank" rel="noreferrer">
            <Button variant="outline">
              <Download className="mr-2 h-4 w-4" aria-hidden />
              Download PDF
            </Button>
          </a>
        </div>
      )}
    </div>
  );
}
