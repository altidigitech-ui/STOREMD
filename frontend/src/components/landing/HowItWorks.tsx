"use client";

import { motion } from "framer-motion";
import { Download, ScanLine, Wrench } from "lucide-react";

const STEPS = [
  {
    icon: Download,
    title: "Install",
    body: "Click 'Add to Shopify'. No signup, no config, no code.",
  },
  {
    icon: ScanLine,
    title: "Scan",
    body: "StoreMD scans your entire store automatically. Theme, apps, products, speed, tracking, AI readiness.",
  },
  {
    icon: Wrench,
    title: "Fix",
    body: "Get a prioritized list of issues. Fix the critical ones in 1 click. Watch your score go up.",
  },
];

export function HowItWorks() {
  return (
    <section className="bg-gray-50">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold text-gray-900 sm:text-4xl">
            3 steps. 60 seconds.
          </h2>
          <p className="mt-3 text-base text-gray-600">
            From install to your first fix in less time than it takes to brew
            coffee.
          </p>
        </div>

        <div className="relative mt-16">
          <div
            className="absolute left-1/2 top-10 hidden h-0.5 w-[calc(100%-20rem)] -translate-x-1/2 bg-gradient-to-r from-blue-200 via-blue-400 to-blue-200 md:block"
            aria-hidden
          />
          <div className="grid grid-cols-1 gap-10 md:grid-cols-3">
            {STEPS.map((step, i) => {
              const Icon = step.icon;
              return (
                <motion.div
                  key={step.title}
                  initial={{ opacity: 0, y: 24 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, amount: 0.3 }}
                  transition={{ duration: 0.5, delay: i * 0.15 }}
                  className="relative flex flex-col items-center text-center"
                >
                  <div className="relative z-10 flex h-20 w-20 items-center justify-center rounded-full border-4 border-white bg-gradient-to-br from-blue-500 to-blue-700 text-white shadow-lg shadow-blue-600/30">
                    <Icon className="h-8 w-8" aria-hidden />
                    <span className="absolute -right-1 -top-1 flex h-7 w-7 items-center justify-center rounded-full border-2 border-white bg-gray-900 text-xs font-bold text-white">
                      {i + 1}
                    </span>
                  </div>
                  <h3 className="mt-6 text-xl font-semibold text-gray-900">
                    {step.title}
                  </h3>
                  <p className="mt-2 max-w-xs text-sm text-gray-600">
                    {step.body}
                  </p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
