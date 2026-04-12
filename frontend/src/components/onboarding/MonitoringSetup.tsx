"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

interface MonitoringSetupProps {
  defaultEmail?: string;
  canInstall: boolean;
  isInstalled: boolean;
  onInstall: () => Promise<boolean>;
  onComplete: (prefs: {
    email: string;
    threshold: number;
  }) => Promise<void>;
  onSkip?: () => void;
}

const THRESHOLDS = [
  { value: 3, label: "3 points (sensitive)" },
  { value: 5, label: "5 points (recommended)" },
  { value: 10, label: "10 points (only major drops)" },
] as const;

export function MonitoringSetup({
  defaultEmail = "",
  canInstall,
  isInstalled,
  onInstall,
  onComplete,
  onSkip,
}: MonitoringSetupProps) {
  const [email, setEmail] = useState(defaultEmail);
  const [threshold, setThreshold] = useState(5);
  const [saving, setSaving] = useState(false);

  async function handleSave() {
    setSaving(true);
    try {
      await onComplete({ email, threshold });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl space-y-6 rounded-lg border border-gray-200 bg-white p-8 shadow-sm">
      <h2 className="text-xl font-semibold">Set up monitoring</h2>

      {/* Q1 — Email */}
      <div>
        <label htmlFor="alert-email" className="block text-sm font-medium">
          1. Send alerts to:
        </label>
        <input
          id="alert-email"
          data-testid="alert-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@store.com"
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {/* Q2 — Threshold */}
      <div>
        <p className="block text-sm font-medium">
          2. Alert me when score drops by:
        </p>
        <div
          data-testid="alert-threshold"
          className="mt-2 flex flex-col gap-2"
          role="radiogroup"
        >
          {THRESHOLDS.map((opt) => (
            <label
              key={opt.value}
              className={cn(
                "flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm",
                threshold === opt.value
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-200",
              )}
            >
              <input
                type="radio"
                name="threshold"
                value={opt.value}
                checked={threshold === opt.value}
                onChange={() => setThreshold(opt.value)}
              />
              {opt.label}
            </label>
          ))}
        </div>
        <p className="mt-1 text-xs text-gray-500">
          We&apos;ll compare each scan to your store&apos;s normal score.
        </p>
      </div>

      {/* Q3 — PWA */}
      {!isInstalled && canInstall && (
        <div data-testid="install-pwa">
          <p className="block text-sm font-medium">
            3. Install StoreMD on your phone?
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Get push notifications. Access your score in one tap.
          </p>
          <div className="mt-2 flex items-center gap-2">
            <Button size="sm" onClick={() => void onInstall()}>
              Add to home screen
            </Button>
            <Button size="sm" variant="ghost">
              Not now
            </Button>
          </div>
        </div>
      )}

      <Button
        className="w-full"
        size="lg"
        onClick={handleSave}
        disabled={saving}
      >
        {saving ? "Saving..." : "Save & Go to Dashboard →"}
      </Button>

      {onSkip && (
        <div className="text-center">
          <button
            type="button"
            onClick={onSkip}
            className="text-xs text-gray-400 hover:text-gray-600 hover:underline"
          >
            Skip setup
          </button>
        </div>
      )}
    </div>
  );
}
