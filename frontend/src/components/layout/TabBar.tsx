"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  FileText,
  Sparkles,
  MonitorSmartphone,
  Settings as SettingsIcon,
  Lock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { Plan } from "@/types";

interface TabBarProps {
  plan: Plan;
}

interface TabDef {
  href: string;
  label: string;
  testId: string;
  icon: typeof Activity;
  requiredPlan: Plan | null;
}

const TABS: TabDef[] = [
  {
    href: "/dashboard/health",
    label: "Health",
    testId: "tab-health",
    icon: Activity,
    requiredPlan: null,
  },
  {
    href: "/dashboard/listings",
    label: "Listings",
    testId: "tab-listings",
    icon: FileText,
    requiredPlan: null,
  },
  {
    href: "/dashboard/agentic",
    label: "AI Ready",
    testId: "tab-agentic",
    icon: Sparkles,
    requiredPlan: "starter",
  },
  {
    href: "/dashboard/browser",
    label: "Browser",
    testId: "tab-browser",
    icon: MonitorSmartphone,
    requiredPlan: "pro",
  },
  {
    href: "/dashboard/settings",
    label: "Settings",
    testId: "tab-settings",
    icon: SettingsIcon,
    requiredPlan: null,
  },
];

const PLAN_RANK: Record<Plan, number> = {
  free: 0,
  starter: 1,
  pro: 2,
  agency: 3,
};

function isLocked(tab: TabDef, plan: Plan): boolean {
  if (!tab.requiredPlan) return false;
  return PLAN_RANK[plan] < PLAN_RANK[tab.requiredPlan];
}

export function TabBar({ plan }: TabBarProps) {
  const pathname = usePathname();

  return (
    <nav className="flex items-center gap-1 py-2">
      {TABS.map((tab) => {
        const Icon = tab.icon;
        const active = pathname?.startsWith(tab.href) ?? false;
        const locked = isLocked(tab, plan);

        return (
          <Link
            key={tab.href}
            href={tab.href}
            data-testid={tab.testId}
            className={cn(
              "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
              active
                ? "bg-blue-50 text-blue-700"
                : "text-gray-600 hover:bg-gray-100",
              locked && "text-gray-400",
            )}
          >
            <Icon className="h-4 w-4" aria-hidden />
            <span>{tab.label}</span>
            {locked && (
              <span className="ml-1 flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500">
                <Lock className="h-3 w-3" aria-hidden />
                PRO
              </span>
            )}
          </Link>
        );
      })}
    </nav>
  );
}
