"use client";

import { motion } from "framer-motion";
import {
  AlertTriangle,
  Bug,
  Eye,
  Gauge,
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
    Icon: TrendingDown,
    title: "$150/month on apps you never open",
    body: "SEO app, speed app, accessibility app, audit app, link checker. Each sends a report. You never read it. $1,800/year gone. For nothing.",
  },
  {
    Icon: Gauge,
    title: "5 apps = 5 scripts = slow store",
    body: "Every audit app loads JavaScript on every page. Five audit apps slowing the store they're supposed to audit. The irony is expensive.",
  },
  {
    Icon: AlertTriangle,
    title: "Reports you never read. Fixes you never ship.",
    body: "\"80 issues found.\" You fix 2. You feel guilty. You renew the subscription. Next month: same report. Same 2 fixes. Same guilt.",
  },
  {
    Icon: Bug,
    title: "Ghost code from apps you deleted last year",
    body: "Uninstalled ≠ gone. Old scripts keep running. Performance stays tanked. Nobody tells you. You just see conversions drop.",
  },
  {
    Icon: Eye,
    title: "Broken checkout, silent bug",
    body: "A button, a field, a shipping rate stops working. You only notice when Monday's sales are flat. By then you lost a week. Good luck finding which app caused it.",
  },
  {
    Icon: Mail,
    title: "5 dashboards. Zero overview.",
    body: "You open one app for SEO, another for speed, a third for accessibility. Nothing tells you what matters most right now. You fix what's loud, not what costs you money.",
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
            You don&apos;t have a Shopify problem. <span className="text-gradient-cyan">You have an app problem.</span>
          </motion.h2>
          <p className="mt-4 text-base text-slate-400">
            23 apps installed. 5 dashboards open. $150/month out. Zero things actually fixed. Sound familiar?
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
