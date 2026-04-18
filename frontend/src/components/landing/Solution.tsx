"use client";

import { motion } from "framer-motion";
import { CheckCircle2 } from "lucide-react";
import { DashboardMockup } from "./DashboardMockup";

const BULLETS = [
  {
    title: "We don't read your store. We use it.",
    body: "Other apps parse metadata. We click buttons, add to cart, go through checkout, measure real load times on real networks. The only way to find what real customers feel.",
  },
  {
    title: "No reports. No to-do lists. No guilt.",
    body: "You wake up to one message: '12 issues fixed tonight. +$2,400 in sales protected this month.' That's it. No PDF. No homework. No feeling like a bad founder.",
  },
  {
    title: "Replace 5 apps. Keep one. Save $600/year.",
    body: "SEO, speed, accessibility, broken links, audits. Five subscriptions, five scripts slowing your store, five dashboards you never open. StoreMD does all of it for $99/month.",
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
            You sleep. <span className="text-gradient-cyan">We fix.</span>
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="mt-4 text-lg text-slate-400"
          >
            Every night at 3 AM, StoreMD goes on your store like a real customer. Clicks every button. Tries the checkout. Loads pages from a slow phone. Whatever breaks — we fix it. You wake up to a shorter list and a faster store.
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
