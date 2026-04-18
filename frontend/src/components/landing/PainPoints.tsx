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
    title: "Your site is slow. You just don't feel it.",
    body: "Your phone has fast Wi-Fi. Your customer's phone doesn't. If your store takes 4 seconds to load on a 4G network, 40% of visitors just left. You never saw them.",
  },
  {
    Icon: TrendingDown,
    title: "$150/month on apps you never open",
    body: "SEO app. Speed app. Audit app. Accessibility app. Link checker. Each one sends you a report. You never read it. You keep paying. That's $1,800/year for nothing.",
  },
  {
    Icon: AlertTriangle,
    title: "Your checkout has a bug. You don't know which one.",
    body: "Somewhere between 'Add to Cart' and 'Pay', something breaks. A button, a form field, a shipping rate. You only notice when sales drop. By then, you've lost weeks.",
  },
  {
    Icon: Bug,
    title: "Ghost code from apps you deleted a year ago",
    body: "You uninstalled an app. Its scripts are still on your store. Slowing every page. For months. Every audit app you've ever tried left residue.",
  },
  {
    Icon: Lock,
    title: "Broken links you'll never find manually",
    body: "A supplier discontinued a product. Your old blog post still links to it. Google sees a 404. Your ranking drops. You had no way to know.",
  },
  {
    Icon: Mail,
    title: "Reports you never read, fixes you never ship",
    body: "Your SEO app says 80 things to fix. You fix 2. You feel guilty. You renew the subscription. Next month, same report. Same 2 fixes. Same guilt.",
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
            Your store bleeds money <span className="text-gradient-cyan">every single night.</span>
          </motion.h2>
          <p className="mt-4 text-base text-slate-400">
            You don&apos;t see it. Your apps don&apos;t fix it. Your customers leave. Here&apos;s what&apos;s happening right now, while you&apos;re reading this.
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
