"use client";

import { motion } from "framer-motion";
import { CheckCircle2 } from "lucide-react";
import { DashboardMockup } from "./DashboardMockup";

const BULLETS = [
  {
    title: "Replace 5 apps with 1 — save $140/mo on average",
    body: "SEO audit, speed monitoring, health scoring, accessibility, broken links. All in Pro at $99/mo instead of $140+/mo spread across five specialists.",
  },
  {
    title: "One script, not five — measurable speed gains",
    body: "Stores that switch to StoreMD typically see 0.8–1.5s faster page loads just from removing redundant audit app scripts.",
  },
  {
    title: "We migrate your configs for you",
    body: "Install StoreMD, tell us what you're replacing, we import your settings. No data loss. No downtime. No developer needed.",
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
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="font-display text-4xl font-extrabold tracking-tight text-white sm:text-5xl"
          >
            One app. Five replaced.{" "}
            <span className="text-gradient-cyan">Zero bloat.</span>
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="mt-4 text-lg text-slate-400"
          >
            StoreMD does what Analyzify, SEO King, PageSpeed Optimizer, Accessibly and Broken Link Checker do — in one app, with one dashboard, on one bill.
          </motion.p>

          <ul className="mt-10 space-y-6">
            {BULLETS.map((b, i) => (
              <motion.li
                key={b.title}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
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
