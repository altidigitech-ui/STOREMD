"use client";

import { motion } from "framer-motion";
import { Check, X } from "lucide-react";

interface Row {
  feature: string;
  them: string;
  us: string;
  usHighlight?: boolean;
}

const ROWS: Row[] = [
  {
    feature: "How they find issues",
    them: "Parse your HTML and metadata",
    us: "Real browser clicks, add-to-cart, checkout flow",
    usHighlight: true,
  },
  {
    feature: "What happens to issues found",
    them: "Emailed to you as a PDF report",
    us: "Fixed automatically — schema, alt text, redirects, ghost code",
    usHighlight: true,
  },
  {
    feature: "Performance impact on your store",
    them: "Each app = one JavaScript file injected",
    us: "One lightweight script. Most stores load 0.8–1.5s faster",
  },
  {
    feature: "AI commerce readiness (ChatGPT, Gemini)",
    them: "Separate app, often paid extra",
    us: "Built-in. LLMs.txt, GTIN, schema, HS codes — all auto",
  },
  {
    feature: "EU Accessibility Act compliance (EAA)",
    them: "Separate app at $25–50/mo",
    us: "Included. €10,000+ in fines avoided",
  },
  {
    feature: "Agency / multi-store support",
    them: "Per-store pricing (×10 boutiques = ×10 bill)",
    us: "Agency plan: 10 stores included, white-label ready",
  },
  {
    feature: "Typical monthly cost for full coverage",
    them: "$150+/mo across 5 apps",
    us: "$79/mo, one app, done",
    usHighlight: true,
  },
];

const COMPETITORS = [
  "Booster SEO",
  "TinyIMG",
  "Accessibly",
  "Plug In SEO",
  "SearchPie",
];

export function ComparisonTable() {
  return (
    <section className="relative py-24">
      <div className="mx-auto max-w-7xl px-6">
        <div className="mx-auto max-w-3xl text-center">
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="font-display text-4xl font-extrabold tracking-tight text-white sm:text-5xl"
          >
            StoreMD vs{" "}
            <span className="text-gradient-cyan">the usual suspects.</span>
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="mt-5 text-base text-slate-400 sm:text-lg"
          >
            No fluff. No marketing fog. Line by line, here&apos;s how StoreMD stacks up
            against the apps you&apos;re probably paying right now.
          </motion.p>
        </div>

        {/* Competitor chips */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="mt-8 flex flex-wrap items-center justify-center gap-2"
        >
          <span className="text-xs text-slate-500">Compared against:</span>
          {COMPETITORS.map((c) => (
            <span
              key={c}
              className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs text-slate-300 backdrop-blur-xl"
            >
              {c}
            </span>
          ))}
        </motion.div>

        {/* Table */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="mx-auto mt-14 max-w-5xl overflow-hidden rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-xl"
        >
          {/* Header */}
          <div className="grid grid-cols-[1.2fr_1fr_1fr] border-b border-white/10 bg-white/[0.04]">
            <div className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-slate-400">
              Feature
            </div>
            <div className="border-l border-white/10 px-6 py-4 text-xs font-bold uppercase tracking-wider text-rose-400/80">
              The 5 apps you have
            </div>
            <div className="border-l border-cyan-500/30 bg-cyan-500/[0.04] px-6 py-4 text-xs font-bold uppercase tracking-wider text-cyan-400">
              StoreMD
            </div>
          </div>

          {/* Rows */}
          <div className="divide-y divide-white/5">
            {ROWS.map((row, i) => (
              <motion.div
                key={row.feature}
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.3, delay: 0.4 + i * 0.05 }}
                className="grid grid-cols-[1.2fr_1fr_1fr] items-stretch"
              >
                <div className="px-6 py-5 text-sm font-semibold text-white">
                  {row.feature}
                </div>
                <div className="flex items-start gap-3 border-l border-white/10 px-6 py-5 text-sm text-slate-400">
                  <X className="mt-0.5 h-4 w-4 flex-shrink-0 text-rose-400/70" />
                  <span>{row.them}</span>
                </div>
                <div
                  className={`flex items-start gap-3 border-l border-cyan-500/30 px-6 py-5 text-sm ${
                    row.usHighlight
                      ? "bg-cyan-500/[0.06] font-medium text-white"
                      : "bg-cyan-500/[0.02] text-slate-200"
                  }`}
                >
                  <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-cyan-400" />
                  <span>{row.us}</span>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Closing statement */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.6 }}
          className="mx-auto mt-14 max-w-2xl text-center"
        >
          <p className="font-display text-xl font-semibold text-white sm:text-2xl">
            We don&apos;t win on price.{" "}
            <span className="text-gradient-cyan">We win on output.</span>
          </p>
          <p className="mt-3 text-sm text-slate-400">
            Every other app hands you homework. We hand you a fixed store.
            That&apos;s the difference between an audit tool and an agent.
          </p>
        </motion.div>
      </div>
    </section>
  );
}
