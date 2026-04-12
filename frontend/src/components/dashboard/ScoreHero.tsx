"use client";

import { ArrowDown, ArrowRight, ArrowUp } from "lucide-react";
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
  const circumference = 2 * Math.PI * 45;
  const clamped = Math.max(0, Math.min(100, score));
  const offset = circumference - (clamped / 100) * circumference;

  return (
    <svg
      className="h-32 w-32"
      viewBox="0 0 100 100"
      role="img"
      aria-label={`Score ${score} out of 100`}
    >
      <circle
        cx="50"
        cy="50"
        r="45"
        fill="none"
        stroke="#e5e7eb"
        strokeWidth="8"
      />
      <circle
        cx="50"
        cy="50"
        r="45"
        fill="none"
        stroke={getScoreStroke(clamped)}
        strokeWidth="8"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform="rotate(-90 50 50)"
        className="transition-all duration-1000 ease-out"
      />
      <text
        x="50"
        y="50"
        textAnchor="middle"
        dominantBaseline="central"
        className="fill-gray-900 text-3xl font-bold"
      >
        {score}
      </text>
    </svg>
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
      <span className="inline-flex items-center gap-1 text-sm text-green-600">
        <ArrowUp className="h-4 w-4" aria-hidden />
        +{delta} since last week
      </span>
    );
  }
  if (trend === "down") {
    return (
      <span className="inline-flex items-center gap-1 text-sm text-red-600">
        <ArrowDown className="h-4 w-4" aria-hidden />
        -{delta} since last week
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-sm text-gray-500">
      <ArrowRight className="h-4 w-4" aria-hidden />
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
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-start">
        <div
          data-testid="health-score"
          className="flex flex-shrink-0 flex-col items-center"
        >
          <ScoreCircle score={score} />
          <p className={cn("mt-2 text-xs font-medium", getScoreColor(score))}>
            /100
          </p>
        </div>

        <div className="flex-1 space-y-2">
          <TrendIndicator trend={trend} delta={trendDelta} />
          <p className="text-sm text-gray-600">
            Mobile:{" "}
            <span className={cn("font-medium", getScoreColor(mobileScore))}>
              {mobileScore}
            </span>
            {"  |  "}
            Desktop:{" "}
            <span className={cn("font-medium", getScoreColor(desktopScore))}>
              {desktopScore}
            </span>
          </p>
          <p className="text-xs text-gray-500">
            Last scan: {formatTimeAgo(lastScanAt)}
          </p>

          <div className="pt-2">
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
