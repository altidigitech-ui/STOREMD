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
    title: "Real customer simulation",
    body: "We run Playwright every night — real browser, real clicks, real checkout flow. If your customer can't buy, we know before they do.",
  },
  {
    Icon: Layers,
    title: "App bloat detection",
    body: "We find which of your 23 apps are slowing your store, which left ghost code behind, and which ones you can delete today without losing anything.",
    span: "wide",
  },
  {
    Icon: BarChart3,
    title: "SEO that ships, not reports",
    body: "Meta tags, alt text, schema, broken links, bad URLs. We fix them. You don't read a PDF. You see the ranking go up.",
  },
  {
    Icon: Shield,
    title: "Accessibility before you get sued",
    body: "EU Accessibility Act is live. Fines start at €10,000. We make your store compliant overnight. Replaces Accessibly, UserWay, accessiBe.",
  },
  {
    Icon: Eye,
    title: "AI commerce ready — without thinking",
    body: "ChatGPT Shopping, Gemini, Copilot. GTIN, schema, LLMs.txt. We set it all up so AI agents recommend your products when customers ask.",
  },
  {
    Icon: Mail,
    title: "Memory that compounds",
    body: "Month 1, we learn your store. Month 6, we know what breaks on Black Friday before it happens. The only audit tool that gets smarter.",
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
            What actually happens
            <br />
            <span className="text-gradient-cyan">while you sleep.</span>
          </motion.h2>
          <p className="mt-4 text-base text-slate-400">
            Not a feature list. A list of problems that die overnight.
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
