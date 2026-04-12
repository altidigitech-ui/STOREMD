"use client";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { cn, getSeverityBorderColor } from "@/lib/utils";
import type { ScanIssue } from "@/types";

export interface IssueCardProps {
  issue: ScanIssue;
  onFix?: (issueId: string) => void;
  onDismiss?: (issueId: string) => void;
}

export function IssueCard({ issue, onFix, onDismiss }: IssueCardProps) {
  return (
    <div
      data-testid="issue-card"
      className={cn(
        "flex gap-4 rounded-lg border bg-white p-4",
        getSeverityBorderColor(issue.severity),
      )}
    >
      <div className="flex-shrink-0">
        <Badge severity={issue.severity}>{issue.severity}</Badge>
      </div>

      <div className="min-w-0 flex-1">
        <h4 className="text-sm font-medium text-gray-900">{issue.title}</h4>
        {issue.impact && (
          <p className="mt-1 text-xs text-gray-500">
            Impact: {issue.impact}
          </p>
        )}
        {issue.fix_description && (
          <p className="mt-2 text-sm text-gray-600">
            {issue.fix_description}
          </p>
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
