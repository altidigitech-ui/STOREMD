"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";

interface FooterCTAProps {
  installHref: string;
}

export function FooterCTA({ installHref }: FooterCTAProps) {
  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-blue-600 to-blue-800 text-white">
      <div
        className="absolute inset-0 -z-0 opacity-30"
        aria-hidden
        style={{
          backgroundImage:
            "radial-gradient(circle at 20% 20%, rgba(255,255,255,0.2) 0%, transparent 40%), radial-gradient(circle at 80% 80%, rgba(255,255,255,0.15) 0%, transparent 40%)",
        }}
      />
      <div className="relative mx-auto max-w-4xl px-6 py-24 text-center">
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.5 }}
          className="text-4xl font-bold sm:text-5xl"
        >
          Your store deserves a doctor.
        </motion.h2>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="mx-auto mt-4 max-w-xl text-lg text-blue-100"
        >
          Free plan. No credit card. 60 seconds.
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="mt-10"
        >
          <Link
            href={installHref}
            className="group inline-flex items-center justify-center gap-2 rounded-lg bg-white px-7 py-4 text-base font-semibold text-blue-700 shadow-2xl transition-all hover:bg-blue-50 focus:outline-none focus:ring-4 focus:ring-white/30"
          >
            Get your free health score
            <ArrowRight
              className="h-5 w-5 transition-transform group-hover:translate-x-1"
              aria-hidden
            />
          </Link>
        </motion.div>
        <p className="mt-6 text-xs text-blue-200">
          Trusted by Shopify merchants worldwide · GDPR compliant · Instant
          cancellation
        </p>
      </div>
    </section>
  );
}
