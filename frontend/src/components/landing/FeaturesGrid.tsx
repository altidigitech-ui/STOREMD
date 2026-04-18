"use client";

import { motion } from "framer-motion";
import {
  Activity,
  BarChart3,
  Bug,
  Eye,
  Layers,
  Shield,
  type LucideIcon,
} from "lucide-react";

interface Feature {
  Icon: LucideIcon;
  title: string;
  body: string;
  span?: "wide";
}

const FEATURES: Feature[] = [
  {
    Icon: BarChart3,
    title: "Kills your SEO app",
    body: "Meta tags, alt text, schema, sitemap, keyword optimization, broken link auto-redirects. Does everything a standalone SEO app does — and actually ships the fixes.",
  },
  {
    Icon: Activity,
    title: "Kills your speed app",
    body: "Core Web Vitals, image compression, lazy load, ghost script detection. Replaces your dedicated speed app — without adding yet another script to your theme.",
    span: "wide",
  },
  {
    Icon: Shield,
    title: "Kills your accessibility app",
    body: "WCAG 2.1 AA + EU Accessibility Act (EAA) compliance. Fines start at €10,000 per violation. Replaces your accessibility overlay — fraction of the price.",
  },
  {
    Icon: Bug,
    title: "Kills your audit tool",
    body: "Full health score across 20 dimensions. Prioritized by revenue impact, not severity. We don't rank issues — we rank them by how much money they cost you.",
  },
  {
    Icon: Eye,
    title: "AI commerce — already built in",
    body: "ChatGPT Shopping, Gemini, Copilot, Perplexity. LLMs.txt, GTIN, HS codes, structured data. No separate AEO app needed. The next $2,400 in sales will come from AI search.",
  },
  {
    Icon: Layers,
    title: "The one thing nobody else does",
    body: "Real browser simulation every day. Our agent clicks through your store like a real customer, from a real phone, on real slow networks. Catches bugs before your buyers do.",
  },
];

export function FeaturesGrid() {
  return (
    <section id="features" className="relative py-24">
      <div className="mx-auto max-w-7xl px-6">
        <div className="mx-auto max-w-2xl text-center">
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="font-display text-4xl font-extrabold tracking-tight text-white sm:text-5xl"
          >
            Why we crush
            <br />
            <span className="text-gradient-cyan">the 5 apps we replace.</span>
          </motion.h2>
          <p className="mt-4 text-base text-slate-400">
            Not a compromise bundle. We beat the specialists at their own game — because we do what they refuse to do.
          </p>
        </div>

        <div className="mt-14 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: i * 0.05 }}
              whileHover={{ y: -4 }}
              className={`group relative overflow-hidden rounded-2xl border border-white/10 bg-white/[0.04] p-7 backdrop-blur-xl transition-all hover:border-cyan-500/30 hover:bg-white/[0.07] hover:shadow-glow-sm ${
                f.span === "wide" ? "lg:col-span-2" : ""
              }`}
            >
              <div
                className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-cyan-500/10 blur-3xl transition-opacity duration-500 group-hover:bg-cyan-500/20"
                aria-hidden
              />
              <div className="relative">
                <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl border border-cyan-500/20 bg-gradient-to-br from-cyan-500/15 to-teal-500/10 text-cyan-300">
                  <f.Icon className="h-5 w-5" />
                </div>
                <h3 className="mt-5 font-display text-xl font-semibold text-white">
                  {f.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-400">
                  {f.body}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
