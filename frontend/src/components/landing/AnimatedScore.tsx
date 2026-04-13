"use client";

import { useEffect, useState } from "react";
import { motion, useInView } from "framer-motion";
import { useRef } from "react";
import { Activity, TrendingUp, Zap } from "lucide-react";

interface AnimatedScoreProps {
  target: number;
}

export function AnimatedScore({ target }: AnimatedScoreProps) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.3 });
  const [score, setScore] = useState(0);

  useEffect(() => {
    if (!inView) return;
    let start = 0;
    const duration = 1800;
    const startTime = performance.now();
    let raf = 0;

    const tick = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(start + (target - start) * eased);
      setScore(current);
      if (progress < 1) raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [inView, target]);

  const circumference = 2 * Math.PI * 70;
  const offset = circumference - (score / 100) * circumference;

  const stroke =
    score >= 80
      ? "#16a34a"
      : score >= 60
        ? "#65a30d"
        : score >= 40
          ? "#ca8a04"
          : score >= 20
            ? "#ea580c"
            : "#dc2626";

  return (
    <div
      ref={ref}
      className="rounded-2xl border border-gray-200 bg-white p-6 shadow-2xl shadow-blue-600/10"
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-gray-500">
            Store Health
          </p>
          <p className="text-sm font-semibold text-gray-900">
            yourstore.myshopify.com
          </p>
        </div>
        <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">
          <TrendingUp className="h-3 w-3" aria-hidden />
          Live
        </span>
      </div>

      <div className="mt-6 flex items-center justify-center">
        <div className="relative">
          <svg
            className="h-48 w-48 -rotate-90"
            viewBox="0 0 160 160"
            role="img"
            aria-label={`Score ${score} out of 100`}
          >
            <circle
              cx="80"
              cy="80"
              r="70"
              fill="none"
              stroke="#f3f4f6"
              strokeWidth="12"
            />
            <circle
              cx="80"
              cy="80"
              r="70"
              fill="none"
              stroke={stroke}
              strokeWidth="12"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              strokeLinecap="round"
              style={{ transition: "stroke-dashoffset 0.05s linear" }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-5xl font-bold text-gray-900">{score}</span>
            <span className="text-xs font-medium text-gray-500">/ 100</span>
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-3 gap-3">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: inView ? 1 : 0 }}
          transition={{ delay: 1.8 }}
          className="rounded-lg bg-gray-50 p-3 text-center"
        >
          <Activity className="mx-auto h-4 w-4 text-blue-600" aria-hidden />
          <p className="mt-1 text-xs text-gray-500">Speed</p>
          <p className="text-sm font-semibold text-gray-900">72</p>
        </motion.div>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: inView ? 1 : 0 }}
          transition={{ delay: 1.9 }}
          className="rounded-lg bg-gray-50 p-3 text-center"
        >
          <Zap className="mx-auto h-4 w-4 text-orange-500" aria-hidden />
          <p className="mt-1 text-xs text-gray-500">Apps</p>
          <p className="text-sm font-semibold text-gray-900">85</p>
        </motion.div>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: inView ? 1 : 0 }}
          transition={{ delay: 2.0 }}
          className="rounded-lg bg-gray-50 p-3 text-center"
        >
          <TrendingUp className="mx-auto h-4 w-4 text-green-600" aria-hidden />
          <p className="mt-1 text-xs text-gray-500">SEO</p>
          <p className="text-sm font-semibold text-gray-900">77</p>
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: inView ? 1 : 0, y: inView ? 0 : 10 }}
        transition={{ delay: 2.1, duration: 0.4 }}
        className="mt-4 rounded-lg border border-red-100 bg-red-50 p-3"
      >
        <p className="text-xs font-semibold text-red-900">
          3 critical issues found
        </p>
        <p className="mt-0.5 text-xs text-red-700">
          Losing ~$1,240/month in conversions
        </p>
      </motion.div>
    </div>
  );
}
