"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

const FAQS = [
  {
    q: "How is this different from other SEO/audit apps?",
    a: "Other apps read your store's metadata and send you a report. We actually use your store — we run a real browser every night, click through your checkout, measure load times on a real phone, and fix the problems we find. You wake up to results, not homework.",
  },
  {
    q: "What does 'fixing it overnight' actually mean?",
    a: "Every night at 3 AM, our AI agent scans your store, detects issues (slow pages, broken links, bad schema, checkout bugs, accessibility fails, ghost scripts), and applies fixes via the Shopify API. You get a morning summary: '12 issues fixed, +$2,400 protected this month.' That's it.",
  },
  {
    q: "Do I really save money switching from 5 apps?",
    a: "Run our free audit — it detects your installed apps and tells you exactly what you'd save. Typical merchant: 5 apps at $150/month combined. StoreMD Pro: $99/month. Saves $612/year, plus your store runs faster because one script replaces five.",
  },
  {
    q: "Will you break my store?",
    a: "No. Every fix is reversible with one click. We log every change, and nothing deploys to your storefront without your approval rules. Critical fixes (like schema) we ship automatically. Risky changes we queue for your review.",
  },
  {
    q: "What about SEO specialists — are you as good?",
    a: "For 95% of merchants, yes. If you need deep keyword research or multi-country hreflang complexity, keep your specialist. StoreMD handles everything else (speed, technical SEO, broken links, schema, accessibility, AI readiness), so you still save 4 apps.",
  },
  {
    q: "How long does a scan take?",
    a: "First scan: ~60 seconds. Nightly scans run at 3 AM in your store's timezone and never interrupt traffic.",
  },
  {
    q: "Will StoreMD slow down my store?",
    a: "The opposite. We don't inject scripts — we only remove bloat and apply fixes via the Shopify API. Most stores get 0.8–1.5s faster within a week.",
  },
  {
    q: "What happens if I uninstall?",
    a: "Subscription ends immediately. All changes we made can be reverted with one click. Your data is deleted within 30 days.",
  },
  {
    q: "Is my data safe?",
    a: "Your Shopify access token is encrypted. Your data is isolated with Postgres RLS. GDPR-compliant and Shopify data-protection compliant.",
  },
  {
    q: "Can I cancel anytime?",
    a: "Yes. One click in Settings or through your Shopify admin. No fees.",
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
