"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

const FAQS = [
  {
    q: "Which apps does StoreMD actually replace?",
    a: "Most commonly: Booster SEO, SEO King, Smart SEO, Tapita, SearchPie, PageSpeed Optimizer, TinyIMG (SEO features), Accessibly, UserWay, accessiBe, Plug In SEO, broken link checkers, and LLMs.txt / AEO apps. If you have a specific app in mind, email us — we probably already replace it.",
  },
  {
    q: "How is StoreMD different from the SEO/audit apps I already use?",
    a: "Other apps read your metadata and send you a PDF. We actually use your store — real browser, real clicks, real checkout flow, real slow-network testing. And we don't stop at finding issues: we ship the fixes automatically. You wake up to results, not homework.",
  },
  {
    q: "Do I really save $850/year switching?",
    a: "Depends on your current stack. Run our free audit — we detect your installed apps and show you the exact number. Typical merchant: 5 apps at $150/month combined. StoreMD Pro: $79/month. That's $852/year saved. Plus your store runs faster because one script replaces five.",
  },
  {
    q: "Will I lose my SEO data or settings if I switch?",
    a: "No. When you install Pro or Agency, we import configs from your previous apps — meta titles, alt text rules, redirects, schema. You start where you left off. Free migration included.",
  },
  {
    q: "Is StoreMD really as good as a dedicated SEO app?",
    a: "For 95% of merchants, yes — we match or exceed core features. If you need deep keyword research or multi-country hreflang complexity, keep your specialist and use StoreMD for everything else (you'd still save 4 apps).",
  },
  {
    q: "Will StoreMD break my store?",
    a: "No. Every fix is reversible with one click. We log every change. Risky changes queue for your review — nothing touches your storefront without approval rules you control. We also never inject scripts; we only apply fixes via the Shopify API.",
  },
  {
    q: "How long does a scan take?",
    a: "First scan: ~60 seconds. Scheduled scans run in the background and never interrupt traffic.",
  },
  {
    q: "Will StoreMD slow down my store?",
    a: "The opposite. We don't inject scripts into your theme. We apply fixes via the Shopify API. Most stores get 0.8–1.5s faster within the first week after removing redundant audit apps.",
  },
  {
    q: "What happens if I uninstall?",
    a: "Subscription ends immediately. All changes are reversible in one click. Your data is deleted within 30 days.",
  },
  {
    q: "Can I cancel anytime?",
    a: "Yes. One click in Settings or through Shopify. No fees. No questions.",
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
