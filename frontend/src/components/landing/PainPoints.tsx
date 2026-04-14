"use client";

import { motion } from "framer-motion";
import {
  AlertTriangle,
  Bug,
  Gauge,
  Lock,
  Mail,
  TrendingDown,
  type LucideIcon,
} from "lucide-react";
import { useRef, useState, MouseEvent } from "react";

interface Pain {
  Icon: LucideIcon;
  title: string;
  body: string;
}

const PAINS: Pain[] = [
  {
    Icon: Gauge,
    title: "Slow page load",
    body: "Every second costs you 7% in conversions. Most stores don't know their real speed.",
  },
  {
    Icon: Bug,
    title: "Ghost code",
    body: "Uninstalled apps leave scripts that slow your store down — for months.",
  },
  {
    Icon: AlertTriangle,
    title: "Broken tracking",
    body: "Your Meta Pixel fires 3 times. GA4 is missing on checkout. You're flying blind.",
  },
  {
    Icon: TrendingDown,
    title: "Poor listings",
    body: "Products that Google and ChatGPT can't understand don't sell.",
  },
  {
    Icon: Lock,
    title: "Security gaps",
    body: "Missing headers, weak scopes, exposed secrets — your customers' browsers can see them.",
  },
  {
    Icon: Mail,
    title: "Email in spam",
    body: "No SPF. No DKIM. Your order confirmations never arrive in inboxes.",
  },
];

function PainCard({ pain, index }: { pain: Pain; index: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [transform, setTransform] = useState("");

  const onMove = (e: MouseEvent<HTMLDivElement>) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    setTransform(
      `perspective(1000px) rotateY(${x * 6}deg) rotateX(${-y * 6}deg)`,
    );
  };

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: index * 0.06 }}
      onMouseMove={onMove}
      onMouseLeave={() => setTransform("")}
      style={{ transform, transition: "transform 0.2s ease-out" }}
      className="group relative rounded-2xl border border-white/10 bg-white/[0.04] p-6 backdrop-blur-xl transition-colors hover:border-cyan-500/30 hover:bg-white/[0.08]"
    >
      <div className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-cyan-500/20 bg-cyan-500/10 text-cyan-400 shadow-glow-sm">
        <pain.Icon className="h-5 w-5" />
      </div>
      <h3 className="mt-5 font-display text-xl font-semibold text-white">
        {pain.title}
      </h3>
      <p className="mt-2 text-sm leading-relaxed text-slate-400">
        {pain.body}
      </p>
    </motion.div>
  );
}

export function PainPoints() {
  return (
    <section className="relative py-24">
      <div className="mx-auto max-w-7xl px-6">
        <div className="mx-auto max-w-2xl text-center">
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="font-display text-4xl font-extrabold tracking-tight text-white sm:text-5xl"
          >
            What&apos;s silently killing your revenue?
          </motion.h2>
          <p className="mt-4 text-base text-slate-400">
            Six problems every Shopify store has. Most merchants discover them
            too late.
          </p>
        </div>

        <div className="mt-14 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {PAINS.map((pain, i) => (
            <PainCard key={pain.title} pain={pain} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}
