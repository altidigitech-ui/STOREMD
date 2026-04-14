"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { AnimatedScore } from "./AnimatedScore";

interface HeroProps {
  installHref: string;
}

export function Hero({ installHref }: HeroProps) {
  return (
    <section className="relative overflow-hidden border-b border-gray-100 bg-white">
      <div
        className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,rgba(37,99,235,0.08),transparent_60%)]"
        aria-hidden
      />
      <div className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-10 px-6 py-16 sm:py-24 lg:grid-cols-2 lg:py-28">
        <div className="text-center lg:text-left">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-3 py-1 text-xs font-medium text-gray-700 shadow-sm"
          >
            <ShieldCheck className="h-3.5 w-3.5 text-blue-600" aria-hidden />
            Built for Shopify
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.05 }}
            className="mt-5 text-4xl font-bold leading-tight tracking-tight text-gray-900 sm:text-5xl lg:text-6xl"
          >
            Your Shopify store is losing money right now.{" "}
            <span className="text-blue-600">Find out how much.</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.15 }}
            className="mx-auto mt-5 max-w-xl text-base text-gray-600 sm:text-lg lg:mx-0"
          >
            StoreMD scans your store in 60 seconds and shows you exactly
            what&apos;s costing you sales — slow apps, broken tracking, dead
            products, ghost charges.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.25 }}
            className="mt-8 flex flex-col items-center gap-3 lg:items-start"
          >
            <Link
              href={installHref}
              className="group relative inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-7 py-4 text-base font-semibold text-white shadow-lg shadow-blue-600/30 transition-all hover:bg-blue-700 hover:shadow-blue-600/40 focus:outline-none focus:ring-4 focus:ring-blue-200"
            >
              <span
                className="absolute inset-0 -z-10 rounded-lg bg-blue-600 animate-ping opacity-20"
                aria-hidden
              />
              Get your free health score
              <ArrowRight
                className="h-5 w-5 transition-transform group-hover:translate-x-1"
                aria-hidden
              />
            </Link>
            <p className="text-xs text-gray-500">
              Free plan available. No credit card. Installs in 1 click.
            </p>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="relative mx-auto w-full max-w-md"
        >
          <AnimatedScore target={78} />
        </motion.div>
      </div>
    </section>
  );
}
