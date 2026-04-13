"use client";

import { motion } from "framer-motion";
import {
  Activity,
  Bolt,
  Ghost,
  FileText,
  Sparkles,
  MonitorSmartphone,
} from "lucide-react";
import { cn } from "@/lib/utils";

type Plan = "Free" | "Starter" | "Pro";

const FEATURES: Array<{
  icon: typeof Activity;
  title: string;
  before: string;
  after: string;
  plan: Plan;
  color: string;
}> = [
  {
    icon: Activity,
    title: "Health Score 24/7",
    before: "You guess if your store is fast.",
    after: "You know your score is 72/100, down 5 points since Tuesday.",
    plan: "Free",
    color: "bg-blue-100 text-blue-600",
  },
  {
    icon: Bolt,
    title: "App Impact Analysis",
    before: "You don't know which app is slow.",
    after:
      "\u201CPrivy adds 1.8s to every page load. Remove it to gain +12 points.\u201D",
    plan: "Starter",
    color: "bg-amber-100 text-amber-600",
  },
  {
    icon: Ghost,
    title: "Ghost Code & Billing Detection",
    before: "Uninstalled apps still bill you and inject code.",
    after:
      "\u201CLoox was uninstalled 3 months ago but still charges $39/mo and injects 4 scripts.\u201D",
    plan: "Starter",
    color: "bg-purple-100 text-purple-600",
  },
  {
    icon: FileText,
    title: "Listing Optimizer",
    before: "You manually check each product.",
    after:
      "\u201CProduct X: Score 34/100. Missing alt text on 3 images, title too short, no meta description.\u201D",
    plan: "Free",
    color: "bg-emerald-100 text-emerald-600",
  },
  {
    icon: Sparkles,
    title: "AI Readiness Check",
    before: "You don't know if AI agents can buy from your store.",
    after:
      "\u201CYour store is 45% ready for AI shopping. 3 critical fixes needed.\u201D",
    plan: "Starter",
    color: "bg-pink-100 text-pink-600",
  },
  {
    icon: MonitorSmartphone,
    title: "Real Browser Testing",
    before: "You test your store on your own phone.",
    after:
      "StoreMD simulates a real purchase path and measures load times at every step.",
    plan: "Pro",
    color: "bg-indigo-100 text-indigo-600",
  },
];

const planStyles: Record<Plan, string> = {
  Free: "bg-gray-100 text-gray-700",
  Starter: "bg-blue-100 text-blue-700",
  Pro: "bg-purple-100 text-purple-700",
};

export function Solution() {
  return (
    <section className="relative overflow-hidden bg-white">
      <div
        className="absolute inset-0 -z-10 bg-[linear-gradient(180deg,rgba(37,99,235,0.04),transparent_40%)]"
        aria-hidden
      />
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="mx-auto max-w-3xl text-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
            The Solution
          </span>
          <h2 className="mt-4 text-3xl font-bold text-gray-900 sm:text-4xl">
            StoreMD finds what&apos;s broken.{" "}
            <span className="text-blue-600">And fixes it.</span>
          </h2>
          <p className="mt-3 text-base text-gray-600">
            One app. 12+ scanners. Running 24/7.
          </p>
        </div>

        <div className="mt-14 grid grid-cols-1 gap-5 md:grid-cols-2">
          {FEATURES.map((feature, i) => {
            const Icon = feature.icon;
            return (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.2 }}
                transition={{ duration: 0.5, delay: i * 0.05 }}
                className="group flex gap-5 rounded-2xl border border-gray-200 bg-white p-6 transition-all hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-lg"
              >
                <div
                  className={cn(
                    "flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl",
                    feature.color,
                  )}
                >
                  <Icon className="h-6 w-6" aria-hidden />
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-base font-semibold text-gray-900">
                      {feature.title}
                    </h3>
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide",
                        planStyles[feature.plan],
                      )}
                    >
                      {feature.plan}
                    </span>
                  </div>

                  <div className="mt-3 space-y-2">
                    <div className="flex items-start gap-2 text-sm">
                      <span className="mt-0.5 inline-flex h-5 w-10 flex-shrink-0 items-center justify-center rounded bg-red-100 text-[10px] font-bold uppercase text-red-700">
                        Before
                      </span>
                      <p className="text-gray-600">{feature.before}</p>
                    </div>
                    <div className="flex items-start gap-2 text-sm">
                      <span className="mt-0.5 inline-flex h-5 w-10 flex-shrink-0 items-center justify-center rounded bg-green-100 text-[10px] font-bold uppercase text-green-700">
                        After
                      </span>
                      <p className="font-medium text-gray-900">
                        {feature.after}
                      </p>
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
