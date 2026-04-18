"use client";

import { motion } from "framer-motion";
import { CheckCircle2, X, Check } from "lucide-react";

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

const BEFORE_APPS = [
  { name: "SEO King", price: "$40/mo" },
  { name: "PageSpeed Optimizer", price: "$30/mo" },
  { name: "Accessibly", price: "$25/mo" },
  { name: "Broken Link Checker", price: "$20/mo" },
  { name: "Plug In SEO", price: "$35/mo" },
];

function BillComparison() {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {/* BEFORE card */}
      <motion.div
        initial={{ opacity: 0, x: -30 }}
        whileInView={{ opacity: 1, x: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
        className="relative overflow-hidden rounded-2xl border border-rose-500/30 bg-rose-500/[0.04] p-8 backdrop-blur-xl"
      >
        <div className="mb-6 flex items-center justify-between">
          <div className="inline-flex items-center gap-2 rounded-full border border-rose-500/30 bg-rose-500/10 px-3 py-1 text-xs font-bold uppercase tracking-wider text-rose-400">
            <X className="h-3.5 w-3.5" />
            Before
          </div>
          <div className="text-xs text-slate-500">Your current stack</div>
        </div>

        <ul className="space-y-3">
          {BEFORE_APPS.map((app, i) => (
            <motion.li
              key={app.name}
              initial={{ opacity: 0, x: -10 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.3, delay: 0.2 + i * 0.08 }}
              className="flex items-center justify-between border-b border-white/5 pb-3 text-sm"
            >
              <span className="flex items-center gap-2 text-slate-300">
                <X className="h-4 w-4 text-rose-400" />
                {app.name}
              </span>
              <span className="font-mono text-slate-400">{app.price}</span>
            </motion.li>
          ))}
        </ul>

        <div className="mt-6 border-t border-rose-500/20 pt-4">
          <div className="flex items-end justify-between">
            <span className="text-sm text-slate-400">Monthly total</span>
            <span className="font-display text-3xl font-bold text-rose-400">
              $150<span className="text-base text-slate-500">/mo</span>
            </span>
          </div>
          <div className="mt-1 flex items-end justify-between">
            <span className="text-xs text-slate-500">Yearly waste</span>
            <span className="font-mono text-sm text-rose-400/80">$1,800/year</span>
          </div>
        </div>

        <div className="mt-6 space-y-2 text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <X className="h-3 w-3 text-rose-400" /> 5 dashboards to open
          </div>
          <div className="flex items-center gap-2">
            <X className="h-3 w-3 text-rose-400" /> 5 scripts slowing your store
          </div>
          <div className="flex items-center gap-2">
            <X className="h-3 w-3 text-rose-400" /> 5 reports you never read
          </div>
        </div>
      </motion.div>

      {/* AFTER card */}
      <motion.div
        initial={{ opacity: 0, x: 30 }}
        whileInView={{ opacity: 1, x: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6, delay: 0.2 }}
        className="relative overflow-hidden rounded-2xl border border-cyan-500/30 bg-gradient-to-br from-cyan-500/[0.08] to-teal-500/[0.04] p-8 shadow-glow-sm backdrop-blur-xl"
      >
        <div className="absolute -right-12 -top-12 h-40 w-40 rounded-full bg-cyan-500/20 blur-3xl" aria-hidden />

        <div className="relative mb-6 flex items-center justify-between">
          <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-xs font-bold uppercase tracking-wider text-cyan-400">
            <Check className="h-3.5 w-3.5" />
            After
          </div>
          <div className="text-xs text-cyan-400/70">With StoreMD</div>
        </div>

        <div className="relative flex items-center justify-between border-b border-cyan-500/20 pb-6">
          <span className="flex items-center gap-2 font-display text-lg font-semibold text-white">
            <CheckCircle2 className="h-5 w-5 text-cyan-400" />
            StoreMD Pro
          </span>
          <span className="font-mono text-slate-300">$99/mo</span>
        </div>

        <div className="relative mt-6">
          <div className="flex items-end justify-between">
            <span className="text-sm text-slate-400">Monthly total</span>
            <span className="font-display text-3xl font-bold text-cyan-400">
              $99<span className="text-base text-slate-500">/mo</span>
            </span>
          </div>
          <div className="mt-1 flex items-end justify-between">
            <span className="text-xs text-slate-500">Saved per year</span>
            <span className="font-mono text-sm font-semibold text-emerald-400">+$612/year</span>
          </div>
        </div>

        <div className="relative mt-6 space-y-2 text-xs text-slate-300">
          <div className="flex items-center gap-2">
            <Check className="h-3 w-3 text-emerald-400" /> 1 dashboard
          </div>
          <div className="flex items-center gap-2">
            <Check className="h-3 w-3 text-emerald-400" /> 1 script — 0.8–1.5s faster pages
          </div>
          <div className="flex items-center gap-2">
            <Check className="h-3 w-3 text-emerald-400" /> 0 reports — we ship the fixes
          </div>
        </div>
      </motion.div>
    </div>
  );
}

export function Solution() {
  return (
    <section className="relative py-24">
      <div
        className="absolute inset-x-0 top-0 -z-10 h-full bg-gradient-to-b from-cyan-500/[0.03] to-transparent"
        aria-hidden
      />
      <div className="mx-auto max-w-7xl px-6">
        <div className="mx-auto max-w-3xl text-center">
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="font-display text-4xl font-extrabold tracking-tight text-white sm:text-5xl"
          >
            The audit era is over.{" "}
            <span className="text-gradient-cyan">Meet your new agent.</span>
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="mx-auto mt-5 text-lg text-slate-400"
          >
            StoreMD does what your 5 apps do — better, cheaper, and actually finishes the job.
            One dashboard. One bill. One script. One agent that doesn&apos;t just find problems,
            it fixes them.
          </motion.p>
        </div>

        {/* Bill comparison visual */}
        <div className="mx-auto mt-16 max-w-5xl">
          <BillComparison />
        </div>

        {/* 3 bullets below */}
        <div className="mx-auto mt-20 max-w-4xl">
          <ul className="grid grid-cols-1 gap-8 lg:grid-cols-3">
            {BULLETS.map((b, i) => (
              <motion.li
                key={b.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.1 }}
                className="relative rounded-2xl border border-white/10 bg-white/[0.04] p-6 backdrop-blur-xl"
              >
                <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl border border-cyan-500/30 bg-cyan-500/10 text-cyan-400">
                  <CheckCircle2 className="h-5 w-5" />
                </div>
                <div className="font-display text-lg font-semibold text-white">
                  {b.title}
                </div>
                <p className="mt-2 text-sm text-slate-400">{b.body}</p>
              </motion.li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
