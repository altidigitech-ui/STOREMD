"use client";

import { motion } from "framer-motion";
import { CheckCircle2 } from "lucide-react";
import { DashboardMockup } from "./DashboardMockup";

const BULLETS = [
  {
    title: "AI-powered analysis across 12 health dimensions",
    body: "Speed, apps, SEO, security, email, accessibility — scanned in one pass.",
  },
  {
    title: "Issues ranked by revenue impact, not just severity",
    body: "We tell you what's costing you money today, not what some audit score says.",
  },
  {
    title: "One-click fix suggestions for every problem found",
    body: "Clear, actionable steps. Most fixes require zero developer time.",
  },
];

export function Solution() {
  return (
    <section className="relative py-24">
      <div
        className="absolute inset-x-0 top-0 -z-10 h-full bg-gradient-to-b from-cyan-500/[0.03] to-transparent"
        aria-hidden
      />
      <div className="mx-auto grid max-w-7xl grid-cols-1 items-center gap-16 px-6 lg:grid-cols-2">
        <div>
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="font-display text-4xl font-extrabold tracking-tight text-white sm:text-5xl"
          >
            One scan. Every problem.{" "}
            <span className="text-gradient-cyan">Clear fixes.</span>
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="mt-4 text-lg text-slate-400"
          >
            StoreMD doesn&apos;t just audit your store. It diagnoses it like a
            doctor — and writes the prescription.
          </motion.p>

          <ul className="mt-10 space-y-6">
            {BULLETS.map((b, i) => (
              <motion.li
                key={b.title}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, amount: 0.3 }}
                transition={{ duration: 0.4, delay: i * 0.1 }}
                className="flex gap-4"
              >
                <div className="mt-1 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full border border-cyan-500/30 bg-cyan-500/10 text-cyan-400">
                  <CheckCircle2 className="h-4 w-4" />
                </div>
                <div>
                  <div className="font-display text-lg font-semibold text-white">
                    {b.title}
                  </div>
                  <p className="mt-1 text-sm text-slate-400">{b.body}</p>
                </div>
              </motion.li>
            ))}
          </ul>
        </div>

        <div>
          <DashboardMockup />
        </div>
      </div>
    </section>
  );
}
