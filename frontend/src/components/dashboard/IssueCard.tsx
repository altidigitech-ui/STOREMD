"use client";

import { AlertTriangle, AlertCircle, Info, Zap } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { cn, getSeverityBorderColor } from "@/lib/utils";
import type { ScanIssue } from "@/types";

export interface IssueCardProps {
  issue: ScanIssue;
  onFix?: (issueId: string) => void;
  onDismiss?: (issueId: string) => void;
}

const severityConfig: Record<
  string,
  { icon: typeof AlertTriangle; chip: string; iconColor: string }
> = {
  critical: {
    icon: AlertTriangle,
    chip: "bg-red-100 text-red-700 border-red-200",
    iconColor: "text-red-600",
  },
  major: {
    icon: AlertCircle,
    chip: "bg-orange-100 text-orange-700 border-orange-200",
    iconColor: "text-orange-600",
  },
  minor: {
    icon: Info,
    chip: "bg-yellow-100 text-yellow-700 border-yellow-200",
    iconColor: "text-yellow-600",
  },
  info: {
    icon: Info,
    chip: "bg-blue-100 text-blue-700 border-blue-200",
    iconColor: "text-blue-600",
  },
};

export function IssueCard({ issue, onFix, onDismiss }: IssueCardProps) {
  const config = severityConfig[issue.severity] ?? severityConfig.info;
  const Icon = config.icon;

  return (
    <div
      data-testid="issue-card"
      className={cn(
        "flex gap-4 rounded-lg border bg-white p-4 shadow-sm transition-shadow hover:shadow-md",
        getSeverityBorderColor(issue.severity),
      )}
    >
      <div className="flex-shrink-0">
        <Icon className={cn("h-5 w-5", config.iconColor)} aria-hidden />
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={cn(
              "inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide",
              config.chip,
            )}
          >
            {issue.severity}
          </span>
          {issue.auto_fixable && (
            <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-blue-700">
              <Zap className="h-2.5 w-2.5" aria-hidden />
              Auto-fix
            </span>
          )}
        </div>
        <h4 className="mt-1.5 text-sm font-semibold text-gray-900">
          {issue.title}
        </h4>
        {issue.impact && (
          <p className="mt-1 text-xs text-gray-500">Impact: {issue.impact}</p>
        )}
        {issue.fix_description && (
          <p className="mt-2 text-sm text-gray-600">{issue.fix_description}</p>
        )}
      </div>

      <div className="flex flex-shrink-0 flex-col gap-2">
        {issue.auto_fixable && onFix && (
          <Button
            data-testid="fix-button"
            size="sm"
            onClick={() => onFix(issue.id)}
          >
            Fix →
          </Button>
        )}
        {onDismiss && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => onDismiss(issue.id)}
          >
            Dismiss
          </Button>
        )}
      </div>
    </div>
  );
}
