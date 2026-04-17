"use client";

import { motion } from "framer-motion";
import {
  Activity,
  BarChart3,
  Eye,
  Layers,
  Mail,
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
    Icon: Activity,
    title: "Speed Analysis",
    body: "Mobile & desktop Core Web Vitals with day-over-day trend tracking. Replaces PageSpeed Optimizer, SpeedBoost, and similar.",
  },
  {
    Icon: Layers,
    title: "App Impact Analyzer",
    body: "See exactly which apps add load time and by how much. The app that tells you which other apps to uninstall.",
    span: "wide",
  },
  {
    Icon: BarChart3,
    title: "SEO & Listings Optimizer",
    body: "Per-product SEO score, metadata, alt text, schema. Replaces Analyzify, SEO King, Booster SEO, Tapita.",
  },
  {
    Icon: Shield,
    title: "Accessibility & Compliance",
    body: "WCAG 2.1 AA + EU EAA deadline. Replaces Accessibly, UserWay, accessiBe — at a fraction of the price.",
  },
  {
    Icon: Eye,
    title: "AI Commerce Readiness",
    body: "ChatGPT Shopping, Copilot, Gemini compatibility. GTIN, HS codes, metafields. No other Shopify app does this yet.",
  },
  {
    Icon: Mail,
    title: "Broken Links & Ghost Code",
    body: "Dead product links, 404s, residue from uninstalled apps. Replaces Broken Link Checker and similar crawlers.",
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
            Everything those 5 apps did.
            <br />
            <span className="text-gradient-cyan">Better. And together.</span>
          </motion.h2>
          <p className="mt-4 text-base text-slate-400">
            Not a compromise bundle. Each module matches or beats its specialist competitor.
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
