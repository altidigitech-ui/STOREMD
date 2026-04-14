"use client";

import { Lock, ShieldCheck, ShoppingBag, Zap } from "lucide-react";

const BADGES = [
  { Icon: ShoppingBag, label: "Shopify" },
  { Icon: Zap, label: "Shopify Plus" },
  { Icon: ShieldCheck, label: "GDPR Compliant" },
  { Icon: Lock, label: "SSL Encrypted" },
  { Icon: ShoppingBag, label: "App Store Verified" },
  { Icon: ShieldCheck, label: "Zero Theme Injection" },
];

export function LogosBar() {
  return (
    <section className="border-y border-white/5 bg-white/[0.02]">
      <div className="mx-auto max-w-7xl px-6 py-8">
        <p className="text-center text-xs font-medium uppercase tracking-[0.2em] text-slate-500">
          Trusted by merchants on
        </p>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-x-10 gap-y-4">
          {BADGES.map(({ Icon, label }) => (
            <div
              key={label}
              className="flex items-center gap-2 text-slate-400 transition-colors hover:text-slate-200"
            >
              <Icon className="h-4 w-4 text-cyan-400/80" />
              <span className="font-display text-sm font-semibold tracking-tight">
                {label}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
