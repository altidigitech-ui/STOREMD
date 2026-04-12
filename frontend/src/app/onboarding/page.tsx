"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { getSupabaseBrowserClient } from "@/lib/supabase";
import { useCurrentStore } from "@/hooks/use-current-store";
import { useInstallPrompt } from "@/hooks/use-install-prompt";
import { ScanProgress } from "@/components/scan/ScanProgress";
import { ScoreHero } from "@/components/dashboard/ScoreHero";
import { IssueCard } from "@/components/dashboard/IssueCard";
import { MonitoringSetup } from "@/components/onboarding/MonitoringSetup";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";
import type { ScanDetailResponse } from "@/types";

type Phase = "scanning" | "reveal" | "setup";

const POLL_INTERVAL_MS = 3_000;
const SCAN_TIMEOUT_MS = 3 * 60_000;

export default function OnboardingPage() {
  const router = useRouter();
  const { storeId, isLoading: loadingStore } = useCurrentStore();
  const { canInstall, isInstalled, install } = useInstallPrompt();

  const [phase, setPhase] = useState<Phase>("scanning");
  const [scan, setScan] = useState<ScanDetailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [merchantEmail, setMerchantEmail] = useState("");
  const [elapsedMs, setElapsedMs] = useState(0);

  const retried = useRef(false);
  const startedAt = useRef<number>(Date.now());
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollTimer.current) {
      clearInterval(pollTimer.current);
      pollTimer.current = null;
    }
  }, []);

  // Load merchant email from Supabase (pre-fill).
  useEffect(() => {
    async function loadEmail() {
      const supabase = getSupabaseBrowserClient();
      const { data } = await supabase.auth.getSession();
      setMerchantEmail(data.session?.user.email ?? "");
    }
    loadEmail();
  }, []);

  const startScan = useCallback(async () => {
    if (!storeId) return;
    try {
      startedAt.current = Date.now();
      setError(null);
      const created = await api.scans.create(storeId, [
        "health",
        "listings",
        "agentic",
      ]);

      pollTimer.current = setInterval(async () => {
        try {
          const detail = await api.scans.get(storeId, created.id);
          setScan(detail);
          setElapsedMs(Date.now() - startedAt.current);

          if (detail.status === "completed") {
            stopPolling();
            setPhase("reveal");
          } else if (detail.status === "failed") {
            stopPolling();
            if (!retried.current) {
              retried.current = true;
              void startScan();
            } else {
              setError(
                "The scan encountered an error. Please try again later.",
              );
            }
          }
        } catch (e) {
          if (e instanceof ApiError) setError(e.message);
        }
      }, POLL_INTERVAL_MS);
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.message
          : "Could not start scan. Please try again.",
      );
    }
  }, [storeId, stopPolling]);

  useEffect(() => {
    if (!storeId) return;
    startScan();
    return () => stopPolling();
  }, [storeId, startScan, stopPolling]);

  // Hard timeout.
  useEffect(() => {
    if (phase !== "scanning") return;
    const t = setInterval(() => {
      setElapsedMs(Date.now() - startedAt.current);
    }, 1000);
    return () => clearInterval(t);
  }, [phase]);

  async function handleCompleteSetup(prefs: {
    email: string;
    threshold: number;
  }) {
    // Save preferences to Supabase user metadata as a lightweight
    // bridge until a dedicated backend endpoint ships.
    const supabase = getSupabaseBrowserClient();
    await supabase.auth.updateUser({
      data: {
        notification_email: prefs.email,
        alert_threshold: prefs.threshold,
        onboarding_completed: true,
      },
    });
    router.replace("/dashboard");
  }

  function handleContinueAnyway() {
    stopPolling();
    router.replace("/dashboard");
  }

  if (loadingStore) return <LoadingState />;

  if (!storeId) {
    return (
      <div className="mx-auto mt-16 max-w-xl">
        <ErrorState message="No store connected. Please reinstall StoreMD from Shopify." />
      </div>
    );
  }

  if (phase === "scanning") {
    return (
      <div className="py-12">
        {error ? (
          <div className="mx-auto max-w-xl">
            <ErrorState message={error} onRetry={startScan} />
          </div>
        ) : (
          <ScanProgress
            scan={scan}
            elapsedMs={elapsedMs}
            onContinueAnyway={
              elapsedMs > SCAN_TIMEOUT_MS ? handleContinueAnyway : undefined
            }
          />
        )}
      </div>
    );
  }

  if (phase === "reveal" && scan) {
    const topIssues = (scan.issues ?? []).slice(0, 3);
    const score = scan.score ?? 0;
    const mobile = scan.mobile_score ?? 0;
    const desktop = scan.desktop_score ?? 0;

    return (
      <div className="mx-auto max-w-2xl space-y-6 py-10">
        <h1 className="text-center text-2xl font-bold">
          Your Store Health Score
        </h1>
        <ScoreHero
          score={score}
          mobileScore={mobile}
          desktopScore={desktop}
          trend="stable"
          trendDelta={0}
          lastScanAt={scan.completed_at}
        />
        {topIssues.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-lg font-semibold">
              {topIssues.length} top issue
              {topIssues.length > 1 ? "s" : ""} found
            </h2>
            {topIssues.map((issue) => (
              <IssueCard key={issue.id} issue={issue} />
            ))}
          </div>
        )}
        <div className="rounded-lg border border-green-200 bg-green-50 p-4">
          <p className="text-sm font-medium text-green-800">
            Enable weekly monitoring (Free)
          </p>
          <p className="mt-1 text-xs text-green-700">
            Get alerts when your score drops.
          </p>
          <Button
            className="mt-3"
            data-testid="enable-monitoring"
            onClick={() => setPhase("setup")}
          >
            Enable monitoring
          </Button>
        </div>
      </div>
    );
  }

  // setup phase
  return (
    <div className="py-12">
      <MonitoringSetup
        defaultEmail={merchantEmail}
        canInstall={canInstall}
        isInstalled={isInstalled}
        onInstall={install}
        onComplete={handleCompleteSetup}
        onSkip={() => void handleCompleteSetup({
          email: merchantEmail,
          threshold: 5,
        })}
      />
    </div>
  );
}
