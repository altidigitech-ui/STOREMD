"use client";

import { motion } from "framer-motion";
import { X, Sparkles, ArrowRight } from "lucide-react";

const DOOMED_APPS = [
  { category: "SEO app", price: "$39/mo", detail: "Meta tags, schema, audits" },
  { category: "Speed app", price: "$29/mo", detail: "Image compression, Core Web Vitals" },
  { category: "Accessibility app", price: "$25/mo", detail: "WCAG overlay, EAA compliance" },
  { category: "Link checker", price: "$19/mo", detail: "Broken links, redirects" },
  { category: "Audit tool", price: "$38/mo", detail: "SEO reports, issue lists" },
];

export function UninstallWall() {
  return (
    <section className="relative py-24">
      <div className="absolute inset-0 -z-10 bg-gradient-to-b from-rose-500/[0.02] via-transparent to-cyan-500/[0.03]" aria-hidden />

      <div className="mx-auto max-w-7xl px-6">
        <div className="mx-auto max-w-2xl text-center">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="inline-flex items-center gap-2 rounded-full border border-rose-500/30 bg-rose-500/10 px-3.5 py-1.5 text-xs font-bold uppercase tracking-wider text-rose-400"
          >
            <X className="h-3.5 w-3.5" />
            Uninstall day
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="mt-6 font-display text-4xl font-extrabold tracking-tight text-white sm:text-5xl"
          >
            The 5 apps that die{" "}
            <span className="text-gradient-cyan">the day you install StoreMD.</span>
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="mt-4 text-base text-slate-400"
          >
            This is what your monthly Shopify bill looks like before and after.
          </motion.p>
        </div>

        <div className="mt-16 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {DOOMED_APPS.map((app, i) => (
            <motion.div
              key={app.category}
              initial={{ opacity: 0, y: 20, rotate: 0 }}
              whileInView={{ opacity: 1, y: 0, rotate: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.08 }}
              className="group relative overflow-hidden rounded-2xl border border-rose-500/20 bg-white/[0.03] p-6 backdrop-blur-xl"
            >
              {/* KILLED stamp */}
              <div className="pointer-events-none absolute right-4 top-4 -rotate-12 rounded-md border-2 border-rose-500/60 px-2 py-0.5 font-display text-xs font-extrabold uppercase tracking-widest text-rose-400">
                Killed
              </div>

              {/* Strikethrough effect */}
              <div className="relative">
                <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-rose-400/70">
                  Your
                </div>
                <h3 className="font-display text-xl font-semibold text-slate-300 line-through decoration-rose-500/60 decoration-2">
                  {app.category}
                </h3>
                <p className="mt-2 text-sm text-slate-500">{app.detail}</p>
                <div className="mt-4 inline-flex items-center gap-2 text-xs text-slate-500">
                  <span className="font-mono line-through decoration-rose-500/60">{app.price}</span>
                  <span className="text-rose-400">→ $0</span>
                </div>
              </div>
            </motion.div>
          ))}

          {/* The replacement — StoreMD card */}
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.98 }}
            whileInView={{ opacity: 1, y: 0, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="group relative overflow-hidden rounded-2xl border border-cyan-500/40 bg-gradient-to-br from-cyan-500/[0.1] to-teal-500/[0.05] p-6 shadow-glow-sm backdrop-blur-xl"
          >
            <div className="absolute -right-10 -top-10 h-32 w-32 rounded-full bg-cyan-500/20 blur-3xl" aria-hidden />
            <div className="relative">
              <div className="mb-2 inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-cyan-400">
                <Sparkles className="h-3.5 w-3.5" />
                Installed
              </div>
              <h3 className="font-display text-xl font-semibold text-white">
                StoreMD Pro
              </h3>
              <p className="mt-2 text-sm text-slate-300">
                All 5 above, in 1 AI agent. Actually fixes what it finds.
              </p>
              <div className="mt-4 flex items-center gap-2 text-xs">
                <span className="font-mono text-cyan-400">$79/mo</span>
                <ArrowRight className="h-3 w-3 text-emerald-400" />
                <span className="font-semibold text-emerald-400">
                  Save $852/year
                </span>
              </div>
            </div>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="mx-auto mt-14 max-w-2xl text-center"
        >
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 backdrop-blur-xl">
            <div className="text-sm text-slate-400">Total killed per month</div>
            <div className="mt-2 flex items-center justify-center gap-4 font-display text-2xl font-bold">
              <span className="text-rose-400 line-through decoration-rose-500/60">
                $150/mo
              </span>
              <ArrowRight className="h-6 w-6 text-slate-500" />
              <span className="text-cyan-400">$79/mo</span>
            </div>
            <div className="mt-2 text-sm font-semibold text-emerald-400">
              Saved: $852 per year. Free space: priceless.
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
