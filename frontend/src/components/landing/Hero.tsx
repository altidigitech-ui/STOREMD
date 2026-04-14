"use client";

import { motion } from "framer-motion";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { DashboardMockup } from "./DashboardMockup";
import { InstallLink } from "./InstallLink";

interface HeroProps {
  installHref: string;
}

export function Hero({ installHref }: HeroProps) {
  return (
    <section className="relative overflow-hidden">
      <div
        className="absolute inset-0 -z-20 animate-gradient-shift bg-mesh"
        aria-hidden
      />
      <div
        className="absolute inset-0 -z-10 bg-dots mask-radial-fade opacity-60"
        aria-hidden
      />

      <div className="mx-auto grid max-w-7xl grid-cols-1 items-center gap-16 px-6 pb-24 pt-36 sm:pt-40 lg:grid-cols-[1.1fr_1fr] lg:pb-32 lg:pt-44">
        <div className="text-center lg:text-left">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3.5 py-1.5 text-xs font-medium text-slate-200 backdrop-blur"
          >
            <ShieldCheck className="h-3.5 w-3.5 text-cyan-400" />
            Built for Shopify · SOC-style data handling
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.08 }}
            className="mt-6 font-display text-5xl font-bold leading-[1.05] tracking-tight text-white sm:text-6xl lg:text-7xl"
          >
            Your store is losing money.
            <br />
            <span className="text-gradient-cyan">Find out how much.</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.18 }}
            className="mx-auto mt-6 max-w-xl text-lg leading-relaxed text-slate-400 lg:mx-0"
          >
            StoreMD scans your entire Shopify store in 60 seconds. Speed, apps,
            SEO, security — one dashboard, zero guesswork.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.28 }}
            className="mt-10 flex flex-col items-center gap-4 lg:items-start"
          >
            <InstallLink
              href={installHref}
              label="hero_install"
              className="group relative inline-flex items-center justify-center gap-2 rounded-xl bg-cyan-500 px-8 py-4 font-display text-base font-bold text-black shadow-glow transition-all hover:bg-cyan-400 hover:shadow-[0_0_60px_rgba(6,182,212,0.6)] focus:outline-none focus:ring-4 focus:ring-cyan-500/30"
            >
              <span
                className="absolute inset-0 -z-10 rounded-xl bg-cyan-400 opacity-60 blur-xl"
                aria-hidden
              />
              Get your free health score
              <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-1" />
            </InstallLink>
            <p className="flex items-center gap-2 text-sm text-slate-500">
              <span>Free plan</span>
              <span className="text-slate-700">·</span>
              <span>No credit card</span>
              <span className="text-slate-700">·</span>
              <span>60-second scan</span>
            </p>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.3 }}
          className="animate-float-slow"
        >
          <DashboardMockup />
        </motion.div>
      </div>
    </section>
  );
}
