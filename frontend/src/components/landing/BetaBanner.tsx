"use client";

import { useState } from "react";
import { X } from "lucide-react";

export function BetaBanner() {
  const [visible, setVisible] = useState(true);

  if (!visible) return null;

  return (
    <div className="relative z-50 bg-gradient-to-r from-cyan-500 to-teal-400 px-4 py-2.5 text-center text-sm font-semibold text-black">
      <span className="mr-1">🧪</span>
      We&apos;re looking for{" "}
      <span className="font-extrabold">10 beta testers</span> — get StoreMD
      free for life.{" "}
      <a
        href="https://storemd.vercel.app/preview"
        className="underline decoration-black/40 underline-offset-2 transition hover:decoration-black"
      >
        Start your free scan →
      </a>
      <button
        type="button"
        onClick={() => setVisible(false)}
        className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-0.5 transition hover:bg-black/10"
        aria-label="Dismiss banner"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
