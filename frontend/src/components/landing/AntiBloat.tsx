"use client";

import { motion } from "framer-motion";
import { ArrowRight, Check, X } from "lucide-react";

const OLD_APPS = [
  { name: "Speed Booster", price: 29 },
  { name: "Review App", price: 19 },
  { name: "SEO Tool", price: 39 },
  { name: "Analytics", price: 49 },
  { name: "Accessibility", price: 15 },
];

const BADGES = [
  "No code injected",
  "Instant cancellation",
  "Data encrypted",
  "GDPR compliant",
];

export function AntiBloat() {
  const total = OLD_APPS.reduce((sum, app) => sum + app.price, 0);

  return (
    <section className="bg-white">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-3xl font-bold text-gray-900 sm:text-4xl">
            One app that replaces five
          </h2>
          <p className="mt-3 text-base text-gray-600">
            Other apps make you install 5 separate tools. StoreMD is one app
            with 5 modules.
          </p>
        </div>

        <div className="mt-14 grid grid-cols-1 items-center gap-6 md:grid-cols-[1fr_auto_1fr]">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.5 }}
            className="rounded-2xl border border-gray-200 bg-gray-50 p-6"
          >
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">
              The old way
            </p>
            <ul className="mt-4 space-y-3">
              {OLD_APPS.map((app) => (
                <li
                  key={app.name}
                  className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3"
                >
                  <div className="flex items-center gap-3">
                    <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-50 text-red-500">
                      <X className="h-4 w-4" aria-hidden />
                    </span>
                    <span className="text-sm font-medium text-gray-700">
                      {app.name}
                    </span>
                  </div>
                  <span className="text-sm font-semibold text-gray-500">
                    ${app.price}/mo
                  </span>
                </li>
              ))}
            </ul>
            <div className="mt-4 border-t border-gray-200 pt-4 text-right">
              <p className="text-xs uppercase text-gray-500">Total</p>
              <p className="text-2xl font-bold text-red-600">${total}/month</p>
            </div>
          </motion.div>

          <div className="flex justify-center md:px-2">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-600 text-white shadow-lg shadow-blue-600/30">
              <ArrowRight className="h-6 w-6" aria-hidden />
            </div>
          </div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="relative rounded-2xl border-2 border-blue-500 bg-gradient-to-br from-blue-50 to-white p-6 shadow-xl shadow-blue-600/10"
          >
            <span className="absolute -top-3 left-6 rounded-full bg-blue-600 px-3 py-1 text-xs font-bold uppercase tracking-wide text-white">
              StoreMD
            </span>
            <p className="mt-2 text-xs font-semibold uppercase tracking-wider text-blue-700">
              The StoreMD way
            </p>
            <ul className="mt-4 space-y-3">
              {[
                "Store Health Monitor",
                "Listing Optimizer",
                "AI Readiness",
                "Compliance & Fixes",
                "Browser Testing",
              ].map((mod) => (
                <li
                  key={mod}
                  className="flex items-center gap-3 rounded-lg border border-blue-100 bg-white px-4 py-3"
                >
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-green-50 text-green-600">
                    <Check className="h-4 w-4" aria-hidden />
                  </span>
                  <span className="text-sm font-medium text-gray-900">
                    {mod}
                  </span>
                </li>
              ))}
            </ul>
            <div className="mt-4 border-t border-blue-100 pt-4 text-right">
              <p className="text-xs uppercase text-blue-700">Starting at</p>
              <p className="text-2xl font-bold text-blue-600">$0/month</p>
            </div>
          </motion.div>
        </div>

        <div className="mt-10 flex flex-wrap items-center justify-center gap-2">
          {BADGES.map((badge) => (
            <span
              key={badge}
              className="inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 shadow-sm"
            >
              <Check className="h-3 w-3 text-green-600" aria-hidden />
              {badge}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
