"use client";

import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { InstallLink } from "./InstallLink";

interface FooterCTAProps {
  installHref: string;
}

export function FooterCTA({ installHref }: FooterCTAProps) {
  return (
    <section className="relative overflow-hidden border-y border-white/5">
      <div
        className="absolute inset-0 -z-10 animate-gradient-shift"
        style={{
          background:
            "radial-gradient(ellipse 60% 80% at 50% 50%, rgba(6,182,212,0.18), transparent 60%), radial-gradient(ellipse 80% 60% at 20% 80%, rgba(20,184,166,0.12), transparent 60%), #0a0a0f",
          backgroundSize: "200% 200%",
        }}
        aria-hidden
      />
      <div className="absolute inset-0 -z-10 bg-dots opacity-30" aria-hidden />

      <div className="relative mx-auto max-w-4xl px-6 py-28 text-center">
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="font-display text-4xl font-extrabold tracking-tight text-white sm:text-6xl"
        >
          Stop guessing.
          <br />
          <span className="text-gradient-cyan">Start diagnosing.</span>
        </motion.h2>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="mx-auto mt-5 max-w-xl text-lg text-slate-300"
        >
          Get your store health score in 60 seconds.
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="mt-10"
        >
          <InstallLink
            href={installHref}
            label="footer_cta_install"
            className="group inline-flex items-center justify-center gap-2 rounded-xl bg-cyan-500 px-8 py-4 font-display text-base font-bold text-black shadow-glow transition-all hover:bg-cyan-400 hover:shadow-[0_0_60px_rgba(6,182,212,0.6)] focus:outline-none focus:ring-4 focus:ring-cyan-500/30"
          >
            Get your free health score
            <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-1" />
          </InstallLink>
        </motion.div>
        <p className="mt-6 text-sm text-slate-500">
          Join 100+ merchants already using StoreMD
        </p>
      </div>
    </section>
  );
}
