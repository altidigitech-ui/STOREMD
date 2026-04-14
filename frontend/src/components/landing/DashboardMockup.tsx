"use client";

import { motion } from "framer-motion";
import { AlertTriangle, Activity, Info, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";

const TARGET_SCORE = 78;
const RADIUS = 54;
const CIRC = 2 * Math.PI * RADIUS;

const ISSUES = [
  {
    severity: "CRITICAL",
    title: "18 apps installed",
    sub: "Est. 1.2s added load time",
    color: "text-rose-400",
    border: "border-rose-500/30",
    bg: "bg-rose-500/10",
    Icon: AlertTriangle,
  },
  {
    severity: "MAJOR",
    title: "SPF record missing",
    sub: "Emails likely landing in spam",
    color: "text-amber-400",
    border: "border-amber-500/30",
    bg: "bg-amber-500/10",
    Icon: Activity,
  },
  {
    severity: "MINOR",
    title: "Alt text missing",
    sub: "42 product images affected",
    color: "text-cyan-400",
    border: "border-cyan-500/30",
    bg: "bg-cyan-500/10",
    Icon: Info,
  },
];

export function DashboardMockup() {
  const [score, setScore] = useState(0);

  useEffect(() => {
    const start = performance.now();
    const duration = 1800;
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      setScore(Math.round(TARGET_SCORE * eased));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  const offset = CIRC - (score / 100) * CIRC;

  return (
    <div className="relative mx-auto w-full max-w-lg perspective-1000">
      <div
        className="absolute -inset-6 -z-10 rounded-[2rem] bg-gradient-to-br from-cyan-500/20 via-teal-500/10 to-transparent blur-2xl"
        aria-hidden
      />

      <motion.div
        initial={{ opacity: 0, rotateY: -14, rotateX: 6, y: 30 }}
        animate={{ opacity: 1, rotateY: -6, rotateX: 3, y: 0 }}
        transition={{ duration: 1, ease: "easeOut" }}
        className="preserve-3d relative rounded-2xl border border-white/10 bg-white/[0.04] p-6 shadow-2xl backdrop-blur-xl"
      >
        <div className="mb-5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-rose-500/70" />
              <span className="h-2.5 w-2.5 rounded-full bg-amber-400/70" />
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/70" />
            </div>
            <span className="ml-2 font-mono text-[11px] text-slate-500">
              storemd.app / health
            </span>
          </div>
          <div className="flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[10px] font-medium text-cyan-300">
            <Sparkles className="h-3 w-3" />
            Live scan
          </div>
        </div>

        <div className="flex items-center gap-6">
          <div className="relative flex h-32 w-32 flex-shrink-0 items-center justify-center">
            <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
              <circle
                cx="60"
                cy="60"
                r={RADIUS}
                stroke="rgba(255,255,255,0.08)"
                strokeWidth="8"
                fill="none"
              />
              <motion.circle
                cx="60"
                cy="60"
                r={RADIUS}
                stroke="url(#scoreGrad)"
                strokeWidth="8"
                strokeLinecap="round"
                fill="none"
                strokeDasharray={CIRC}
                strokeDashoffset={offset}
                style={{ filter: "drop-shadow(0 0 8px rgba(6,182,212,0.6))" }}
              />
              <defs>
                <linearGradient id="scoreGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#22d3ee" />
                  <stop offset="100%" stopColor="#2dd4bf" />
                </linearGradient>
              </defs>
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="font-display text-4xl font-bold text-white">
                {score}
              </span>
              <span className="text-[10px] uppercase tracking-wider text-slate-400">
                of 100
              </span>
            </div>
          </div>

          <div className="flex-1 space-y-1.5">
            <div className="text-xs uppercase tracking-wider text-slate-500">
              Store Health
            </div>
            <div className="font-display text-lg font-semibold text-white">
              Needs attention
            </div>
            <div className="text-[11px] text-slate-400">
              12 issues across 5 modules
            </div>
            <div className="mt-3 flex gap-3 text-[10px]">
              <Stat label="Crit" value="3" tone="rose" />
              <Stat label="Major" value="5" tone="amber" />
              <Stat label="Minor" value="4" tone="cyan" />
            </div>
          </div>
        </div>

        <div className="mt-5 space-y-2.5">
          {ISSUES.map((issue, i) => (
            <motion.div
              key={issue.title}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.6 + i * 0.15, duration: 0.5 }}
              className={`flex items-center gap-3 rounded-xl border ${issue.border} ${issue.bg} px-3 py-2.5`}
            >
              <issue.Icon className={`h-4 w-4 ${issue.color}`} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span
                    className={`text-[9px] font-bold uppercase tracking-wider ${issue.color}`}
                  >
                    {issue.severity}
                  </span>
                  <span className="truncate text-xs font-medium text-white">
                    {issue.title}
                  </span>
                </div>
                <div className="mt-0.5 truncate text-[10px] text-slate-400">
                  {issue.sub}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "rose" | "amber" | "cyan";
}) {
  const toneMap = {
    rose: "text-rose-400",
    amber: "text-amber-400",
    cyan: "text-cyan-400",
  };
  return (
    <div className="flex items-baseline gap-1">
      <span className={`font-display font-bold ${toneMap[tone]}`}>{value}</span>
      <span className="uppercase tracking-wider text-slate-500">{label}</span>
    </div>
  );
}
