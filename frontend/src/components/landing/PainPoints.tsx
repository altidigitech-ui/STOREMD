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
    title: "5 apps = 5 scripts",
    body: "Every app loads JavaScript on every page. Five audit apps means five performance hits — on the very thing they're supposed to measure.",
  },
  {
    Icon: TrendingDown,
    title: "$140/mo on duplicates",
    body: "SEO app + speed app + audit app + accessibility app + link checker. Each $20–40/mo. Combined: your margin.",
  },
  {
    Icon: AlertTriangle,
    title: "5 dashboards, zero overview",
    body: "You open one app for SEO, another for speed, a third for accessibility. Nothing tells you what actually matters most right now.",
  },
  {
    Icon: Bug,
    title: "Ghost code from uninstalls",
    body: "Deleted an app last year? Its scripts are still running. Every old audit app leaves residue that slows your store for months.",
  },
  {
    Icon: Lock,
    title: "5 security surfaces",
    body: "Each app wants access to orders, products, customers. More apps equals more scopes, more risk, more breach points.",
  },
  {
    Icon: Mail,
    title: "5 support tickets to chase",
    body: "When something breaks, good luck finding which of your 23 apps caused it — or which support team to email first.",
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
            Your Shopify stack is <span className="text-gradient-cyan">bleeding you dry.</span>
          </motion.h2>
          <p className="mt-4 text-base text-slate-400">
            The average Shopify store runs 23 apps. Most are redundant. All slow your site. All bill you monthly.
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
