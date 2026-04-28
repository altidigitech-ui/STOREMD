"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Lock, ArrowRight, RotateCcw, AlertTriangle } from "lucide-react";
import { Footer } from "@/components/landing/Footer";
import { LandingNavbar } from "@/components/landing/LandingNavbar";
import { ShopInputModal } from "@/components/landing/ShopInputModal";
import type { PreviewScanResponse, PreviewIssue } from "@/types";

// ─── Constants ───────────────────────────────────────────────────────────────

const LOADING_MESSAGES = [
  "Checking SEO meta tags...",
  "Analyzing accessibility...",
  "Testing security headers...",
  "Checking page performance...",
  "Scanning for broken links...",
  "Checking robots.txt & sitemap...",
  "Almost done...",
];

const SEVERITY_CONFIG = {
  critical: { label: "Critical", bg: "bg-red-500/15", text: "text-red-400", border: "border-red-500/30" },
  major: { label: "Major", bg: "bg-orange-500/15", text: "text-orange-400", border: "border-orange-500/30" },
  minor: { label: "Minor", bg: "bg-yellow-500/15", text: "text-yellow-400", border: "border-yellow-500/30" },
  info: { label: "Info", bg: "bg-blue-500/15", text: "text-blue-400", border: "border-blue-500/30" },
} as const;

const CATEGORY_LABELS: Record<string, string> = {
  seo: "SEO",
  accessibility: "Accessibility",
  security: "Security",
  performance: "Performance",
  links: "Links",
  robots: "Robots",
};

// ─── Score circle ─────────────────────────────────────────────────────────────

function ScoreCircle({ score, animate }: { score: number; animate: boolean }) {
  const [displayed, setDisplayed] = useState(0);
  const raf = useRef<number>(0);

  useEffect(() => {
    if (!animate) return;
    let start = 0;
    const duration = 1500;
    const startTime = performance.now();

    const tick = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayed(Math.round(start + (score - start) * eased));
      if (progress < 1) raf.current = requestAnimationFrame(tick);
    };

    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [score, animate]);

  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (displayed / 100) * circumference;
  const stroke =
    displayed >= 80
      ? "#22c55e"
      : displayed >= 60
        ? "#84cc16"
        : displayed >= 40
          ? "#eab308"
          : displayed >= 20
            ? "#f97316"
            : "#ef4444";

  return (
    <div className="relative h-36 w-36">
      <svg className="h-full w-full -rotate-90" viewBox="0 0 120 120" aria-hidden>
        <circle cx="60" cy="60" r="54" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="10" />
        <circle
          cx="60"
          cy="60"
          r="54"
          fill="none"
          stroke={stroke}
          strokeWidth="10"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.05s linear, stroke 0.3s" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-display text-4xl font-extrabold text-white">{displayed}</span>
        <span className="text-xs font-medium text-slate-500">/ 100</span>
      </div>
    </div>
  );
}

// ─── Loading state ────────────────────────────────────────────────────────────

function LoadingView({ shop }: { shop: string }) {
  const [msgIndex, setMsgIndex] = useState(0);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const msgTimer = setInterval(() => {
      setMsgIndex((i) => Math.min(i + 1, LOADING_MESSAGES.length - 1));
    }, 3000);

    // Simulate 0→90% in 10s
    const startTime = performance.now();
    let raf: number;
    const tick = (now: number) => {
      const elapsed = (now - startTime) / 10_000;
      const p = Math.min(elapsed, 1);
      const eased = 1 - Math.pow(1 - p, 2);
      setProgress(Math.round(eased * 90));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    return () => {
      clearInterval(msgTimer);
      cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#0a0a0f] px-6 text-slate-100">
      <div className="flex flex-col items-center gap-8 text-center">
        <Link href="/" className="flex items-center gap-2 font-display text-xl font-bold text-white">
          <Image src="/icons/icon-192x192.png" alt="StoreMD" width={36} height={36} className="rounded-xl" />
          StoreMD
        </Link>

        <motion.div
          className="relative flex h-36 w-36 items-center justify-center"
          animate={{ scale: [1, 1.04, 1] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
        >
          <div className="absolute inset-0 rounded-full border-2 border-cyan-500/20" />
          <div className="absolute inset-0 rounded-full bg-cyan-500/5" />
          <span className="font-display text-3xl font-extrabold text-cyan-400">{progress}%</span>
        </motion.div>

        <div>
          <p className="font-display text-xl font-semibold text-white">
            Scanning <span className="text-cyan-400">{shop}</span>
          </p>
          <AnimatePresence mode="wait">
            <motion.p
              key={msgIndex}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.3 }}
              className="mt-2 text-sm text-slate-400"
            >
              {LOADING_MESSAGES[msgIndex]}
            </motion.p>
          </AnimatePresence>
        </div>

        <div className="h-1.5 w-64 overflow-hidden rounded-full bg-white/5">
          <motion.div
            className="h-full rounded-full bg-cyan-500"
            style={{ width: `${progress}%` }}
            transition={{ duration: 0.1 }}
          />
        </div>
      </div>
    </div>
  );
}

// ─── Error state ──────────────────────────────────────────────────────────────

function ErrorView({ shop, message }: { shop: string; message: string }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#0a0a0f] px-6 text-slate-100">
      <div className="flex max-w-md flex-col items-center gap-6 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-red-500/10 ring-1 ring-red-500/20">
          <AlertTriangle className="h-8 w-8 text-red-400" />
        </div>
        <div>
          <p className="font-display text-xl font-bold text-white">Scan failed</p>
          <p className="mt-2 text-sm text-slate-400">{message}</p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="inline-flex items-center gap-2 rounded-lg bg-cyan-500 px-5 py-2.5 text-sm font-semibold text-black transition hover:bg-cyan-400"
          >
            <RotateCcw className="h-4 w-4" />
            Try again
          </button>
          <button
            type="button"
            onClick={() => { window.location.href = "/"; }}
            className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-white/10"
          >
            Try another store
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Issue card ───────────────────────────────────────────────────────────────

function IssueCard({ issue }: { issue: PreviewIssue }) {
  const sev = SEVERITY_CONFIG[issue.severity] ?? SEVERITY_CONFIG.info;
  const catLabel = CATEGORY_LABELS[issue.category] ?? issue.category;

  return (
    <div className={`rounded-xl border ${sev.border} ${sev.bg} p-4`}>
      <div className="flex flex-wrap items-start gap-2">
        <span className={`shrink-0 rounded-md px-2 py-0.5 text-xs font-bold uppercase tracking-wide ${sev.text}`}>
          {sev.label}
        </span>
        <span className="shrink-0 rounded-md border border-white/10 bg-white/5 px-2 py-0.5 text-xs text-slate-400">
          {catLabel}
        </span>
        {issue.fix_available_after_install && (
          <span className="shrink-0 rounded-md bg-cyan-500/10 px-2 py-0.5 text-xs font-medium text-cyan-400 ring-1 ring-cyan-500/20">
            Auto-fixable with StoreMD
          </span>
        )}
      </div>
      <p className="mt-2.5 text-sm font-semibold text-white">{issue.title}</p>
      <p className="mt-1 text-xs leading-relaxed text-slate-400">{issue.description}</p>
    </div>
  );
}

// ─── Results view ─────────────────────────────────────────────────────────────

function ResultsView({
  result,
  shop,
  installHref,
}: {
  result: PreviewScanResponse;
  shop: string;
  installHref: string;
}) {
  const [showModal, setShowModal] = useState(false);
  const installUrl = `${installHref}?shop=${encodeURIComponent(shop)}`;
  const extraChecks = result.checks_available_after_install - result.checks_run;

  // Sort issues: critical → major → minor → info
  const SEVERITY_ORDER = ["critical", "major", "minor", "info"];
  const sortedIssues = [...result.issues].sort(
    (a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity),
  );

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-slate-100">
      <LandingNavbar installHref={installHref} />

      {/* Score hero */}
      <section className="pb-12 pt-28">
        <div className="mx-auto max-w-4xl px-6 text-center">
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-sm font-medium text-slate-500"
          >
            Preview scan for
          </motion.p>
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="mt-1 font-display text-xl font-bold text-white"
          >
            {shop}
          </motion.p>

          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.15, duration: 0.5 }}
            className="mt-8 flex flex-col items-center gap-4"
          >
            <ScoreCircle score={result.preview_score} animate />
            <div className="text-center">
              <p className="font-display text-lg font-bold text-white">Preview Score</p>
              <p className="mt-1 text-sm text-slate-400">
                {result.checks_run} of {result.checks_available_after_install} checks completed
              </p>
            </div>
          </motion.div>

          {/* Summary pills */}
          {(result.summary.critical > 0 || result.summary.major > 0 || result.summary.minor > 0) && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
              className="mt-6 flex flex-wrap justify-center gap-3"
            >
              {result.summary.critical > 0 && (
                <span className="rounded-full bg-red-500/15 px-4 py-1.5 text-sm font-semibold text-red-400 ring-1 ring-red-500/30">
                  {result.summary.critical} critical
                </span>
              )}
              {result.summary.major > 0 && (
                <span className="rounded-full bg-orange-500/15 px-4 py-1.5 text-sm font-semibold text-orange-400 ring-1 ring-orange-500/30">
                  {result.summary.major} major
                </span>
              )}
              {result.summary.minor > 0 && (
                <span className="rounded-full bg-yellow-500/15 px-4 py-1.5 text-sm font-semibold text-yellow-400 ring-1 ring-yellow-500/30">
                  {result.summary.minor} minor
                </span>
              )}
            </motion.div>
          )}
        </div>
      </section>

      <div className="mx-auto max-w-4xl px-6 pb-32">
        {/* Issues list */}
        {sortedIssues.length > 0 ? (
          <section className="mb-16">
            <h2 className="mb-4 font-display text-xl font-bold text-white">
              Issues found ({sortedIssues.length})
            </h2>
            <div className="flex flex-col gap-3">
              {sortedIssues.map((issue, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 + i * 0.04 }}
                >
                  <IssueCard issue={issue} />
                </motion.div>
              ))}
            </div>
          </section>
        ) : (
          <section className="mb-16 rounded-2xl border border-green-500/20 bg-green-500/5 p-8 text-center">
            <p className="font-display text-xl font-bold text-green-400">No issues found in this preview scan</p>
            <p className="mt-2 text-sm text-slate-400">
              Install StoreMD for {extraChecks} additional deep checks including app impact, ghost billing, and more.
            </p>
          </section>
        )}

        {/* Locked modules */}
        <section className="mb-16">
          <h2 className="mb-2 font-display text-xl font-bold text-white">
            Locked — {result.locked_modules.length} more modules
          </h2>
          <p className="mb-6 text-sm text-slate-400">
            These checks require StoreMD to be installed and connected to your Shopify store.
          </p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {result.locked_modules.map((mod, i) => (
              <motion.div
                key={mod.name}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.05 + i * 0.04 }}
                className="flex items-start gap-3 rounded-xl border border-white/10 bg-white/[0.02] p-4 opacity-60"
              >
                <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/5">
                  <Lock className="h-4 w-4 text-slate-500" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-300">{mod.name}</p>
                  <p className="mt-0.5 text-xs text-slate-500">{mod.description}</p>
                  <span className="mt-1.5 inline-block rounded border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-medium text-slate-500">
                    Requires install
                  </span>
                </div>
              </motion.div>
            ))}
          </div>
        </section>
      </div>

      {/* Sticky CTA */}
      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-white/5 bg-[#0a0a0f]/95 px-6 py-4 backdrop-blur-xl">
        <div className="mx-auto flex max-w-4xl flex-col items-center gap-3 sm:flex-row sm:justify-between">
          <div className="text-center sm:text-left">
            <p className="font-display text-base font-bold text-white">
              Get the full picture — install StoreMD
            </p>
            <p className="text-xs text-slate-400">
              Unlock {extraChecks > 0 ? `${extraChecks} more checks` : "all checks"} + automatic fixes
            </p>
          </div>
          <a
            href={installUrl}
            className="inline-flex shrink-0 items-center gap-2 rounded-xl bg-cyan-500 px-6 py-3 font-display text-sm font-bold text-black shadow-glow transition hover:bg-cyan-400 hover:shadow-[0_0_40px_rgba(6,182,212,0.5)]"
          >
            Install StoreMD free
            <ArrowRight className="h-4 w-4" />
          </a>
        </div>
      </div>

      <Footer />

      <ShopInputModal open={showModal} onClose={() => setShowModal(false)} />
    </div>
  );
}

// ─── Empty input view ─────────────────────────────────────────────────────────

function EmptyShopView() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#0a0a0f] px-6 text-slate-100">
      <ShopInputModal open onClose={() => {}} />
    </div>
  );
}

// ─── Main client component ────────────────────────────────────────────────────

export function PreviewClient() {
  const [shop, setShop] = useState<string | null>(null);
  const [result, setResult] = useState<PreviewScanResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const installHref = process.env.NEXT_PUBLIC_BACKEND_URL
    ? `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/auth/install`
    : "/api/v1/auth/install";

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const shopParam = params.get("shop");
    if (!shopParam) return;

    setShop(shopParam);
    setLoading(true);

    fetch("/api/v1/preview/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ shop_domain: shopParam }),
    })
      .then((res) => res.json())
      .then((data: PreviewScanResponse) => {
        setResult(data);
      })
      .catch(() => {
        setResult({
          shop_domain: shopParam,
          store_url: `https://${shopParam}`,
          preview_score: 0,
          scan_duration_ms: 0,
          checks_run: 0,
          checks_available_after_install: 21,
          issues: [],
          summary: { critical: 0, major: 0, minor: 0, info: 0 },
          locked_modules: [],
          error: "An unexpected error occurred. Please try again.",
        });
      })
      .finally(() => setLoading(false));
  }, []);

  if (!shop) {
    return <EmptyShopView />;
  }

  if (loading) {
    return <LoadingView shop={shop} />;
  }

  if (!result) {
    return <LoadingView shop={shop} />;
  }

  if (result.error) {
    return <ErrorView shop={shop} message={result.error} />;
  }

  return <ResultsView result={result} shop={shop} installHref={installHref} />;
}
