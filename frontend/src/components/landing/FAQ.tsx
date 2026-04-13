"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

const FAQS = [
  {
    q: "How long does a scan take?",
    a: "About 60 seconds for the first scan. Daily scans run at 3 AM and don't interrupt anything.",
  },
  {
    q: "Will StoreMD slow down my store?",
    a: "No. StoreMD reads your store data through the Shopify API. It never injects code into your theme (unless you use One-Click Fix, which only removes code, never adds it).",
  },
  {
    q: "What happens when I uninstall?",
    a: "Your subscription is canceled immediately. No future charges. Any code changes we made are reversed. Zero residual code. Your data is deleted after 30 days.",
  },
  {
    q: "Do I need a developer?",
    a: "No. Most fixes are 1-click or come with simple step-by-step instructions. A few advanced issues (like custom theme code) may need a developer.",
  },
  {
    q: "What's the AI Ready module?",
    a: "Shopify now lets customers buy through ChatGPT, Copilot, and Gemini. StoreMD checks if your products have the data these AI agents need: barcodes, structured descriptions, proper categories. No other app does this.",
  },
  {
    q: "Is my data safe?",
    a: "Yes. Your Shopify access token is encrypted. Your data is isolated — no other merchant can see it. We comply with GDPR and Shopify's data protection requirements.",
  },
  {
    q: "Can I cancel anytime?",
    a: "Yes. Cancel in the Settings tab or through Shopify. Effective immediately. No cancellation fees.",
  },
];

export function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <div className="mx-auto max-w-3xl divide-y divide-gray-200 overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
      {FAQS.map((item, i) => {
        const open = openIndex === i;
        return (
          <div key={item.q}>
            <button
              type="button"
              className="flex w-full items-center justify-between gap-4 px-6 py-5 text-left transition-colors hover:bg-gray-50"
              onClick={() => setOpenIndex(open ? null : i)}
              aria-expanded={open}
            >
              <span className="text-base font-medium text-gray-900">
                {item.q}
              </span>
              <ChevronDown
                className={cn(
                  "h-5 w-5 flex-shrink-0 text-gray-400 transition-transform duration-300",
                  open && "rotate-180 text-blue-600",
                )}
                aria-hidden
              />
            </button>
            <AnimatePresence initial={false}>
              {open && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.25, ease: "easeInOut" }}
                  className="overflow-hidden"
                >
                  <div className="px-6 pb-5 text-sm leading-relaxed text-gray-600">
                    {item.a}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}
    </div>
  );
}
