"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

const FAQS = [
  {
    q: "Which apps does StoreMD actually replace?",
    a: "Most commonly: Analyzify, SEO King, Booster SEO, Avada SEO Suite, Tapita, PageSpeed Optimizer, Accessibly, UserWay, and Broken Link Checker. If you have a specific app in mind, email us — we likely already replace it.",
  },
  {
    q: "Do I really save $140/mo?",
    a: "Depends on your current stack. Run our free audit — we detect your installed apps and show you the exact number. Most stores save $80–200/mo.",
  },
  {
    q: "Will I lose my SEO data or settings if I switch?",
    a: "No. When you install Pro or Agency, we import configs from your previous apps (meta titles, alt text rules, redirects, etc.) so you start where you left off. Free migration is included.",
  },
  {
    q: "Is StoreMD really as good as a dedicated SEO app?",
    a: "For 95% of merchants, yes — we match or exceed core features. If you need deep keyword research or complex international hreflang, keep your specialist and use StoreMD for everything else (you'd still save 4 apps).",
  },
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
    <div className="mx-auto max-w-3xl divide-y divide-white/5 overflow-hidden rounded-2xl border border-white/10 bg-white/[0.04] backdrop-blur-xl">
      {FAQS.map((item, i) => {
        const open = openIndex === i;
        return (
          <div key={item.q}>
            <button
              type="button"
              className="flex w-full items-center justify-between gap-4 px-6 py-5 text-left transition-colors hover:bg-white/[0.03]"
              onClick={() => setOpenIndex(open ? null : i)}
              aria-expanded={open}
            >
              <span className="font-display text-base font-semibold text-white">
                {item.q}
              </span>
              <ChevronDown
                className={cn(
                  "h-5 w-5 flex-shrink-0 text-slate-500 transition-all duration-300",
                  open && "rotate-180 text-cyan-400",
                )}
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
                  <div className="px-6 pb-5 text-sm leading-relaxed text-slate-400">
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
