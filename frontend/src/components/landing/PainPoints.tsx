"use client";

import { motion } from "framer-motion";

const PAINS = [
  {
    emoji: "🐌",
    title: "Your store takes 6+ seconds to load",
    body: "You've installed 15 apps over the years. Each one added JavaScript. Your customers leave before the page even loads. You're losing thousands in sales every day.",
  },
  {
    emoji: "💸",
    title: "You're paying for apps you don't use",
    body: "That review app you uninstalled 6 months ago? It's still billing you $29/month. And its code is still slowing your store down.",
  },
  {
    emoji: "🤖",
    title: "AI shoppers can't find your products",
    body: "ChatGPT, Copilot, and Gemini now buy products directly from Shopify stores. If your listings aren't optimized, you're invisible to 100M+ AI users.",
  },
  {
    emoji: "📊",
    title: "Your tracking pixels are broken",
    body: "Your Meta Pixel fired 3 times on the same page. Your GA4 is missing on checkout. You're burning ad budget on bad data.",
  },
  {
    emoji: "📉",
    title: "You don't know your store's health",
    body: "Is your store faster or slower than last month? Which app update broke your speed? You have no baseline, no monitoring, no alerts.",
  },
  {
    emoji: "⚖️",
    title: "The EU Accessibility Act is here",
    body: "EU stores must be accessible. Fines up to €250,000. Do you know if your store is compliant? Most Shopify stores aren't.",
  },
];

const container = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.08 },
  },
};

const item = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

export function PainPoints() {
  return (
    <section className="bg-slate-950 text-white">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-3xl font-bold sm:text-4xl">Sound familiar?</h2>
          <p className="mt-3 text-base text-gray-400">
            These are the six silent killers of Shopify stores. You probably
            have at least three.
          </p>
        </div>

        <motion.div
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.15 }}
          className="mt-12 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3"
        >
          {PAINS.map((pain) => (
            <motion.div
              key={pain.title}
              variants={item}
              className="group relative rounded-2xl border border-white/10 bg-white/[0.03] p-6 transition-all hover:border-white/20 hover:bg-white/[0.05]"
            >
              <div
                className="absolute inset-x-0 -top-px mx-6 h-px bg-gradient-to-r from-transparent via-blue-500/50 to-transparent opacity-0 transition-opacity group-hover:opacity-100"
                aria-hidden
              />
              <span
                className="text-3xl"
                aria-hidden
                role="img"
              >
                {pain.emoji}
              </span>
              <h3 className="mt-4 text-lg font-semibold text-white">
                {pain.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-gray-400">
                {pain.body}
              </p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
