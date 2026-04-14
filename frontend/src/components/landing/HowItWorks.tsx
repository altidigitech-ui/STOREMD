"use client";

import { motion } from "framer-motion";
import { Download, Search, Wrench, type LucideIcon } from "lucide-react";

interface Step {
  Icon: LucideIcon;
  title: string;
  body: string;
}

const STEPS: Step[] = [
  {
    Icon: Download,
    title: "Install",
    body: "One click from the Shopify App Store. No configuration. No developer required.",
  },
  {
    Icon: Search,
    title: "Scan",
    body: "60-second automated audit. Speed, apps, SEO, security, listings — all at once.",
  },
  {
    Icon: Wrench,
    title: "Fix",
    body: "Prioritized issues with clear, actionable recommendations. Most are one-click.",
  },
];

export function HowItWorks() {
  return (
    <section className="relative py-24">
      <div className="mx-auto max-w-7xl px-6">
        <div className="mx-auto max-w-2xl text-center">
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="font-display text-4xl font-extrabold tracking-tight text-white sm:text-5xl"
          >
            Three steps. <span className="text-gradient-cyan">Zero friction.</span>
          </motion.h2>
          <p className="mt-4 text-base text-slate-400">
            From install to first fix in under 5 minutes.
          </p>
        </div>

        <div className="relative mt-16">
          <svg
            className="absolute left-1/2 top-12 hidden h-1 w-[calc(66%+4rem)] -translate-x-1/2 lg:block"
            viewBox="0 0 800 4"
            preserveAspectRatio="none"
            aria-hidden
          >
            <defs>
              <linearGradient id="stepLine" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="rgba(6,182,212,0)" />
                <stop offset="50%" stopColor="rgba(6,182,212,0.5)" />
                <stop offset="100%" stopColor="rgba(6,182,212,0)" />
              </linearGradient>
            </defs>
            <motion.line
              x1="0"
              y1="2"
              x2="800"
              y2="2"
              stroke="url(#stepLine)"
              strokeWidth="2"
              strokeDasharray="8 8"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 1.5, ease: "easeInOut" }}
            />
          </svg>

          <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
            {STEPS.map((step, i) => (
              <motion.div
                key={step.title}
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: i * 0.15 }}
                className="relative rounded-2xl border border-white/10 bg-white/[0.04] p-8 text-center backdrop-blur-xl"
              >
                <div className="mx-auto flex h-20 w-20 items-center justify-center">
                  <span className="absolute top-8 inline-flex h-16 w-16 items-center justify-center rounded-2xl border border-white/10 bg-gradient-to-br from-cyan-500/20 to-teal-500/10 shadow-glow-sm">
                    <step.Icon className="h-7 w-7 text-cyan-300" />
                  </span>
                </div>
                <div className="mt-6 font-display text-sm font-bold uppercase tracking-[0.2em] text-cyan-400">
                  Step {i + 1}
                </div>
                <h3 className="mt-2 font-display text-2xl font-bold text-white">
                  {step.title}
                </h3>
                <p className="mx-auto mt-3 max-w-sm text-sm leading-relaxed text-slate-400">
                  {step.body}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
