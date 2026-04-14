"use client";

import { useState } from "react";
import Link from "next/link";
import { Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { isAdmin } from "@/lib/admin";
import type { Plan } from "@/types";

interface MobileNavProps {
  plan: Plan;
  email?: string | null;
}

const LINKS = [
  { href: "/dashboard/health", label: "Health" },
  { href: "/dashboard/listings", label: "Listings" },
  { href: "/dashboard/agentic", label: "AI Ready", requiredPlan: "starter" },
  { href: "/dashboard/browser", label: "Browser", requiredPlan: "pro" },
  { href: "/dashboard/settings", label: "Settings" },
] as const;

const PLAN_RANK: Record<Plan, number> = {
  free: 0,
  starter: 1,
  pro: 2,
  agency: 3,
};

export function MobileNav({ plan, email }: MobileNavProps) {
  const [open, setOpen] = useState(false);
  const showAdmin = isAdmin(email);

  return (
    <div className="md:hidden">
      <button
        data-testid="mobile-menu-toggle"
        type="button"
        aria-label={open ? "Close menu" : "Open menu"}
        onClick={() => setOpen((prev) => !prev)}
        className="inline-flex h-9 w-9 items-center justify-center rounded-md text-gray-700 hover:bg-gray-100"
      >
        {open ? (
          <X className="h-5 w-5" aria-hidden />
        ) : (
          <Menu className="h-5 w-5" aria-hidden />
        )}
      </button>

      {open && (
        <nav
          data-testid="mobile-nav"
          className="absolute left-0 right-0 top-full border-b border-gray-200 bg-white shadow-md"
        >
          <ul className="flex flex-col py-2">
            {LINKS.map((link) => {
              const locked =
                "requiredPlan" in link && link.requiredPlan
                  ? PLAN_RANK[plan] < PLAN_RANK[link.requiredPlan]
                  : false;
              return (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className={cn(
                      "flex items-center justify-between px-4 py-3 text-sm",
                      locked
                        ? "text-gray-400"
                        : "text-gray-800 hover:bg-gray-50",
                    )}
                    onClick={() => setOpen(false)}
                  >
                    <span>{link.label}</span>
                    {locked && (
                      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                        PRO
                      </span>
                    )}
                  </Link>
                </li>
              );
            })}
            {showAdmin && (
              <li>
                <Link
                  href="/dashboard/admin"
                  className="flex items-center justify-between px-4 py-3 text-sm text-purple-700 hover:bg-purple-50"
                  onClick={() => setOpen(false)}
                >
                  <span>Admin</span>
                </Link>
              </li>
            )}
          </ul>
        </nav>
      )}
    </div>
  );
}
