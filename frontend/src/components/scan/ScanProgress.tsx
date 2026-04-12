"use client";

import { useEffect, useState } from "react";
import { Loader2, CheckCircle2, Lightbulb } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ScanDetailResponse } from "@/types";

const SCAN_FACTS = [
  "Did you know? The average Shopify store has 14 apps, each adding 200-500ms to load time.",
  "Stores that load in under 2 seconds convert 2x better than stores at 4 seconds.",
  "73% of Shopify stores have residual code from uninstalled apps.",
  "The European Accessibility Act requires online stores to be accessible. Fines up to €250,000.",
  "AI shopping agents (ChatGPT, Copilot) can now buy directly from Shopify stores.",
];

const FACT_INTERVAL_MS = 10_000;

interface ScanProgressProps {
  scan: ScanDetailResponse | null;
  elapsedMs: number;
  onContinueAnyway?: () => void;
}

export function ScanProgress({
  scan,
  elapsedMs,
  onContinueAnyway,
}: ScanProgressProps) {
  const [factIndex, setFactIndex] = useState(0);

  useEffect(() => {
    const t = setInterval(() => {
      setFactIndex((i) => (i + 1) % SCAN_FACTS.length);
    }, FACT_INTERVAL_MS);
    return () => clearInterval(t);
  }, []);

  const progress = scan?.metadata?.progress ?? 0;
  const currentStep = scan?.metadata?.current_step ?? "Starting scan...";

  const steps: { label: string; done: boolean }[] = [
    {
      label: "Theme analyzed",
      done: progress >= 20,
    },
    { label: "Apps detected", done: progress >= 40 },
    { label: "Products scanned", done: progress >= 60 },
    { label: "Checking app impact on speed", done: progress >= 80 },
    { label: "Detecting residual code", done: progress >= 95 },
  ];

  const tookTooLong = elapsedMs > 180_000;

  return (
    <div
      data-testid="scan-progress"
      className="mx-auto max-w-xl space-y-6 rounded-lg border border-gray-200 bg-white p-8 shadow-sm"
    >
      <div>
        <h1 className="flex items-center gap-2 text-xl font-semibold">
          <Loader2 className="h-5 w-5 animate-spin text-blue-600" aria-hidden />
          Scanning your store...
        </h1>
        <p className="mt-1 text-xs text-gray-500">{currentStep}</p>
      </div>

      <div className="space-y-2">
        <div className="h-2 overflow-hidden rounded-full bg-gray-100">
          <div
            className="h-full bg-blue-600 transition-all duration-500"
            style={{ width: `${Math.max(5, progress)}%` }}
          />
        </div>
        <p className="text-right text-xs text-gray-500">{progress}%</p>
      </div>

      <ul className="space-y-2">
        {steps.map((step) => (
          <li
            key={step.label}
            className={cn(
              "flex items-center gap-2 text-sm",
              step.done ? "text-gray-900" : "text-gray-400",
            )}
          >
            {step.done ? (
              <CheckCircle2
                className="h-4 w-4 text-green-600"
                aria-hidden
              />
            ) : (
              <Loader2
                className="h-4 w-4 animate-spin text-gray-400"
                aria-hidden
              />
            )}
            <span>{step.label}</span>
          </li>
        ))}
      </ul>

      <div className="flex items-start gap-2 rounded-md bg-blue-50 p-3 text-sm text-blue-800">
        <Lightbulb className="mt-0.5 h-4 w-4 flex-shrink-0" aria-hidden />
        <p>{SCAN_FACTS[factIndex]}</p>
      </div>

      {tookTooLong && onContinueAnyway && (
        <div className="rounded-md border border-yellow-200 bg-yellow-50 p-3 text-sm">
          <p className="text-yellow-800">Taking longer than usual...</p>
          <button
            type="button"
            onClick={onContinueAnyway}
            className="mt-2 text-xs font-medium text-yellow-900 underline"
          >
            Continue anyway →
          </button>
        </div>
      )}
    </div>
  );
}
