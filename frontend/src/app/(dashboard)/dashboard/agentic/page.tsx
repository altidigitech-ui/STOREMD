"use client";

import { useEffect, useState } from "react";
import { Check, X, AlertTriangle } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useCurrentStore } from "@/hooks/use-current-store";
import { Card, CardContent, CardTitle } from "@/components/ui/Card";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";
import { cn, getScoreColor } from "@/lib/utils";
import type { AgenticCheck, AgenticScoreResponse } from "@/types";

const CHECK_LABELS: Record<string, string> = {
  gtin_present: "GTIN/Barcode present",
  metafields_filled: "Key metafields filled (material, dimensions, weight)",
  structured_description: "Structured product descriptions",
  schema_markup: "Schema markup on product pages",
  google_category: "Google product categories assigned",
  shopify_catalog: "Published to Shopify Catalog",
};

function StatusIcon({ status }: { status: AgenticCheck["status"] }) {
  if (status === "pass") {
    return (
      <Check className="h-4 w-4 text-green-600" aria-label="Pass" aria-hidden />
    );
  }
  if (status === "partial") {
    return (
      <AlertTriangle
        className="h-4 w-4 text-yellow-600"
        aria-label="Partial"
        aria-hidden
      />
    );
  }
  return <X className="h-4 w-4 text-red-600" aria-label="Fail" aria-hidden />;
}

export default function AgenticPage() {
  const { storeId, isLoading: loadingStore } = useCurrentStore();
  const [data, setData] = useState<AgenticScoreResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!storeId) return;
    let cancelled = false;

    (async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await api.agentic.score(storeId);
        if (cancelled) return;
        setData(result);
      } catch (e) {
        if (cancelled) return;
        setError(
          e instanceof ApiError
            ? e.message
            : "Failed to load agentic readiness score",
        );
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

  const score = data?.score ?? 0;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">AI Ready</h1>

      <Card>
        <CardContent>
          <p className="text-sm text-gray-600">Your store is</p>
          <p
            className={cn(
              "text-5xl font-bold leading-none",
              getScoreColor(score),
            )}
          >
            {score}%
          </p>
          <p className="mt-1 text-sm text-gray-700">
            ready for AI shopping agents
          </p>
          <p className="mt-3 text-xs text-gray-500">
            Shopify now sells through ChatGPT, Copilot, and Gemini. AI orders
            grew 15× in the past year. Products without this data are invisible
            to those agents.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardTitle>6 readiness checks</CardTitle>
        <CardContent>
          {(!data || data.checks.length === 0) ? (
            <p className="text-sm text-gray-500">
              No agentic scan results yet. Trigger a scan with the Agentic
              module enabled to see your checks.
            </p>
          ) : (
            <ul className="divide-y divide-gray-100">
              {data.checks.map((check) => (
                <li
                  key={check.name}
                  className="flex items-start justify-between gap-3 py-3 text-sm"
                >
                  <div className="flex flex-1 items-start gap-2">
                    <StatusIcon status={check.status} />
                    <div className="min-w-0">
                      <p className="font-medium text-gray-900">
                        {CHECK_LABELS[check.name] ?? check.name}
                      </p>
                      {check.status !== "pass" && (
                        <p className="mt-1 text-xs text-gray-500">
                          {check.affected_products} products need attention
                          {check.fix_description && ` — ${check.fix_description}`}
                        </p>
                      )}
                    </div>
                  </div>
                  <span className="text-right text-xs text-gray-500">
                    {check.pass_rate.toFixed(0)}% pass
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
