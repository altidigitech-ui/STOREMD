"use client";

import { motion } from "framer-motion";
import { Star } from "lucide-react";

interface Quote {
  text: string;
  name: string;
  role: string;
  initials: string;
}

const QUOTES: Quote[] = [
  {
    text: "StoreMD found $200/month in ghost charges I didn't know about. Paid for itself the first week.",
    name: "Sarah K.",
    role: "Store Owner, Apparel",
    initials: "SK",
  },
  {
    text: "Page speed went from 2.1s to 0.8s after following their fixes. Our conversion rate jumped 14%.",
    name: "Mike T.",
    role: "Shopify Plus Merchant",
    initials: "MT",
  },
  {
    text: "The only app that actually explains WHY your store is slow — not just that it is.",
    name: "David L.",
    role: "Agency, 40+ stores",
    initials: "DL",
  },
];

function Avatar({ initials }: { initials: string }) {
  return (
    <div className="flex h-10 w-10 items-center justify-center rounded-full border border-cyan-500/30 bg-gradient-to-br from-cyan-500/20 to-teal-500/10 font-display text-xs font-bold text-cyan-300">
      {initials}
    </div>
  );
}

export function Testimonials() {
  return (
    <section className="relative py-24">
      <div className="mx-auto max-w-7xl px-6">
        <div className="mx-auto max-w-2xl text-center">
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="font-display text-4xl font-extrabold tracking-tight text-white sm:text-5xl"
          >
            Merchants <span className="text-gradient-cyan">love it.</span>
          </motion.h2>
          <p className="mt-4 text-base text-slate-400">
            Real stores. Real numbers. Real fixes.
          </p>
        </div>

        <div className="mt-14 grid grid-cols-1 gap-5 md:grid-cols-3">
          {QUOTES.map((q, i) => (
            <motion.div
              key={q.name}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.5, delay: i * 0.08 }}
              className="relative flex flex-col rounded-2xl border border-white/10 bg-white/[0.04] p-7 backdrop-blur-xl transition-all hover:border-white/20 hover:bg-white/[0.06]"
            >
              <div className="flex gap-0.5">
                {Array.from({ length: 5 }).map((_, s) => (
                  <Star
                    key={s}
                    className="h-4 w-4 fill-cyan-400 text-cyan-400"
                  />
                ))}
              </div>
              <p className="mt-5 flex-1 text-base italic leading-relaxed text-slate-200">
                &ldquo;{q.text}&rdquo;
              </p>
              <div className="mt-6 flex items-center gap-3 border-t border-white/5 pt-4">
                <Avatar initials={q.initials} />
                <div>
                  <div className="font-display text-sm font-semibold text-white">
                    {q.name}
                  </div>
                  <div className="text-xs text-slate-500">{q.role}</div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
