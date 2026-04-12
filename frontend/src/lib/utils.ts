import clsx, { type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

// ───────────── Score colors (from docs/UI.md) ─────────────
export function getScoreColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-lime-600";
  if (score >= 40) return "text-yellow-600";
  if (score >= 20) return "text-orange-600";
  return "text-red-600";
}

export function getScoreBg(score: number): string {
  if (score >= 80) return "bg-green-50";
  if (score >= 60) return "bg-lime-50";
  if (score >= 40) return "bg-yellow-50";
  if (score >= 20) return "bg-orange-50";
  return "bg-red-50";
}

export function getScoreStroke(score: number): string {
  if (score >= 80) return "#16a34a";
  if (score >= 60) return "#65a30d";
  if (score >= 40) return "#ca8a04";
  if (score >= 20) return "#ea580c";
  return "#dc2626";
}

// ───────────── Severity ─────────────
export function getSeverityColor(severity: string): string {
  const map: Record<string, string> = {
    critical: "text-red-600 bg-red-50 border-red-200",
    major: "text-orange-600 bg-orange-50 border-orange-200",
    minor: "text-yellow-600 bg-yellow-50 border-yellow-200",
    info: "text-blue-600 bg-blue-50 border-blue-200",
  };
  return map[severity] ?? map.info;
}

export function getSeverityBorderColor(severity: string): string {
  const map: Record<string, string> = {
    critical: "border-l-4 border-l-red-600 border-red-200",
    major: "border-l-4 border-l-orange-600 border-orange-200",
    minor: "border-l-4 border-l-yellow-600 border-yellow-200",
    info: "border-l-4 border-l-blue-600 border-blue-200",
  };
  return map[severity] ?? map.info;
}

// ───────────── Time formatting ─────────────
export function formatTimeAgo(iso: string | null | undefined): string {
  if (!iso) return "Never";
  const date = new Date(iso);
  const diffMs = Date.now() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);

  if (diffSec < 60) return "Just now";
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `${diffH}h ago`;
  const diffD = Math.floor(diffH / 24);
  if (diffD < 30) return `${diffD} day${diffD > 1 ? "s" : ""} ago`;
  const diffMo = Math.floor(diffD / 30);
  if (diffMo < 12) return `${diffMo} month${diffMo > 1 ? "s" : ""} ago`;
  const diffY = Math.floor(diffMo / 12);
  return `${diffY} year${diffY > 1 ? "s" : ""} ago`;
}

export function formatDateShort(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}
