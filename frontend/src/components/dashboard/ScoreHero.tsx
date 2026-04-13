"use client";

import {
  ArrowDown,
  ArrowRight,
  ArrowUp,
  Smartphone,
  Monitor,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import {
  cn,
  formatTimeAgo,
  getScoreColor,
  getScoreStroke,
} from "@/lib/utils";

export interface ScoreHeroProps {
  score: number;
  mobileScore: number;
  desktopScore: number;
  trend: "up" | "down" | "stable";
  trendDelta: number;
  lastScanAt: string | null;
  scansRemaining?: number;
  onScanNow?: () => void;
  onUpgrade?: () => void;
}

function ScoreCircle({ score }: { score: number }) {
  const circumference = 2 * Math.PI * 56;
  const clamped = Math.max(0, Math.min(100, score));
  const offset = circumference - (clamped / 100) * circumference;
  const stroke = getScoreStroke(clamped);

  return (
    <div className="relative">
      <svg
        className="h-40 w-40 -rotate-90"
        viewBox="0 0 128 128"
        role="img"
        aria-label={`Score ${score} out of 100`}
      >
        <circle
          cx="64"
          cy="64"
          r="56"
          fill="none"
          stroke="#f3f4f6"
          strokeWidth="10"
        />
        <circle
          cx="64"
          cy="64"
          r="56"
          fill="none"
          stroke={stroke}
          strokeWidth="10"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className={cn(
            "text-4xl font-bold tabular-nums",
            getScoreColor(clamped),
          )}
        >
          {score}
        </span>
        <span className="text-xs font-medium text-gray-500">/ 100</span>
      </div>
    </div>
  );
}

function TrendIndicator({
  trend,
  delta,
}: {
  trend: "up" | "down" | "stable";
  delta: number;
}) {
  if (trend === "up") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-0.5 text-xs font-semibold text-green-700">
        <ArrowUp className="h-3 w-3" aria-hidden />
        +{delta} since last week
      </span>
    );
  }
  if (trend === "down") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-xs font-semibold text-red-700">
        <ArrowDown className="h-3 w-3" aria-hidden />
        -{delta} since last week
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-semibold text-gray-600">
      <ArrowRight className="h-3 w-3" aria-hidden />
      Stable since last week
    </span>
  );
}

export function ScoreHero({
  score,
  mobileScore,
  desktopScore,
  trend,
  trendDelta,
  lastScanAt,
  scansRemaining,
  onScanNow,
  onUpgrade,
}: ScoreHeroProps) {
  const limitReached =
    typeof scansRemaining === "number" && scansRemaining <= 0;

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-center sm:gap-8">
        <div
          data-testid="health-score"
          className="flex flex-shrink-0 flex-col items-center"
        >
          <ScoreCircle score={score} />
        </div>

        <div className="flex-1 space-y-3 text-center sm:text-left">
          <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
            <h2 className="text-base font-semibold text-gray-900">
              Store Health Score
            </h2>
            <TrendIndicator trend={trend} delta={trendDelta} />
          </div>

          <div className="flex flex-wrap items-center justify-center gap-4 sm:justify-start">
            <div className="flex items-center gap-2">
              <Smartphone className="h-4 w-4 text-gray-400" aria-hidden />
              <span className="text-xs text-gray-500">Mobile</span>
              <span
                className={cn(
                  "text-sm font-semibold",
                  getScoreColor(mobileScore),
                )}
              >
                {mobileScore}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Monitor className="h-4 w-4 text-gray-400" aria-hidden />
              <span className="text-xs text-gray-500">Desktop</span>
              <span
                className={cn(
                  "text-sm font-semibold",
                  getScoreColor(desktopScore),
                )}
              >
                {desktopScore}
              </span>
            </div>
          </div>

          <p className="text-xs text-gray-500">
            Last scan: {formatTimeAgo(lastScanAt)}
          </p>

          <div className="pt-1">
            {limitReached ? (
              <Button
                data-testid="scan-now"
                variant="outline"
                onClick={onUpgrade}
              >
                Scan limit reached — Upgrade →
              </Button>
            ) : (
              <Button data-testid="scan-now" onClick={onScanNow}>
                Scan now
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
