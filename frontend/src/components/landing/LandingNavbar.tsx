"use client";

import Link from "next/link";
import { useState } from "react";
import { Menu, X } from "lucide-react";

const NAV_LINKS = [
  { href: "#pricing", label: "Pricing" },
  { href: "#faq", label: "FAQ" },
];

export function LandingNavbar() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-gray-100 bg-white/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <Link
          href="/"
          className="flex items-center gap-2 text-lg font-bold text-gray-900"
        >
          <span className="inline-flex h-7 w-7 items-center justify-center rounded-md bg-blue-600 text-white">
            S
          </span>
          StoreMD
        </Link>

        <nav className="hidden items-center gap-7 md:flex">
          {NAV_LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="text-sm font-medium text-gray-700 transition-colors hover:text-gray-900"
            >
              {l.label}
            </a>
          ))}
          <Link
            href="/login"
            className="text-sm font-medium text-blue-600 transition-colors hover:text-blue-700"
          >
            Log in
          </Link>
        </nav>

        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="inline-flex h-9 w-9 items-center justify-center rounded-md text-gray-700 hover:bg-gray-100 md:hidden"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
        >
          {open ? (
            <X className="h-5 w-5" aria-hidden />
          ) : (
            <Menu className="h-5 w-5" aria-hidden />
          )}
        </button>
      </div>

      {open && (
        <div className="border-t border-gray-100 bg-white md:hidden">
          <div className="mx-auto flex max-w-6xl flex-col gap-1 px-6 py-3">
            {NAV_LINKS.map((l) => (
              <a
                key={l.href}
                href={l.href}
                onClick={() => setOpen(false)}
                className="rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                {l.label}
              </a>
            ))}
            <Link
              href="/login"
              onClick={() => setOpen(false)}
              className="rounded-md px-3 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50"
            >
              Log in
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
