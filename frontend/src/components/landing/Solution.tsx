"use client";

import { motion } from "framer-motion";
import { CheckCircle2 } from "lucide-react";
import { DashboardMockup } from "./DashboardMockup";

const BULLETS = [
  {
    title: "Reports don't pay rent. We do.",
    body: "Other apps hand you a PDF. We hand you a fixed store. Broken links redirected, schema deployed, alt text written, ghost code removed, slow images compressed. Done — not documented.",
  },
  {
    title: "One script instead of five. Measurable speed.",
    body: "Every app you uninstall = one less JavaScript load on every page. Stores that migrate to StoreMD typically gain 0.8–1.5s on page speed within a week. That's 5–10% more conversions, free.",
  },
  {
    title: "The only agent that actually uses your store.",
    body: "We don't parse metadata from the outside. We open your store in a real browser, click your buttons, add to cart, complete checkout on a real slow 4G phone. If your customer can't buy, we know before they do.",
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
            The audit era is over. <span className="text-gradient-cyan">Meet your new agent.</span>
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="mt-4 text-lg text-slate-400"
          >
            StoreMD does what your 5 apps do — better, cheaper, and actually finishes the job. One dashboard. One bill. One script. One agent that doesn&apos;t just find problems, it fixes them.
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
