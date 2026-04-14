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
    body: "Mobile & desktop Lighthouse scores with day-over-day trend tracking.",
  },
  {
    Icon: Layers,
    title: "App Impact",
    body: "See exactly which apps add load time — and how much — to every page of your store.",
    span: "wide",
  },
  {
    Icon: BarChart3,
    title: "Listing Optimizer",
    body: "SEO score per product with concrete fix suggestions for title, description, and tags.",
  },
  {
    Icon: Shield,
    title: "Security Monitor",
    body: "SSL, security headers, permission scopes, third-party apps — all verified.",
  },
  {
    Icon: Eye,
    title: "Ghost Detection",
    body: "Find charges and code from apps you already removed — before they cost you more.",
  },
  {
    Icon: Mail,
    title: "Email Health",
    body: "SPF, DKIM, DMARC verification so your emails land in inboxes, not spam folders.",
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
            Everything your store needs.
            <br />
            <span className="text-gradient-cyan">Nothing it doesn&apos;t.</span>
          </motion.h2>
          <p className="mt-4 text-base text-slate-400">
            One focused app replacing five bloated ones.
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
