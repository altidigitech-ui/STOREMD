"use client";

import { useState } from "react";
import { IssueCard } from "@/components/dashboard/IssueCard";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/shared/EmptyState";
import type { ScanIssue } from "@/types";

interface IssuesListProps {
  issues: ScanIssue[];
  onFix?: (issueId: string) => void;
  onDismiss?: (issueId: string) => void;
  collapsedLimit?: number;
}

export function IssuesList({
  issues,
  onFix,
  onDismiss,
  collapsedLimit = 3,
}: IssuesListProps) {
  const [expanded, setExpanded] = useState(false);

  if (issues.length === 0) {
    return (
      <EmptyState
        title="All clear! ✅"
        message="No issues detected. Your store is in great shape."
      />
    );
  }

  const criticalCount = issues.filter((i) => i.severity === "critical").length;
  const visible = expanded ? issues : issues.slice(0, collapsedLimit);
  const hiddenCount = issues.length - visible.length;

  return (
    <div data-testid="issues-list" className="space-y-3">
      <div className="flex items-baseline justify-between">
        <h3 className="text-lg font-semibold text-gray-900">
          <span data-testid="issues-count">{issues.length}</span> issues found
          {criticalCount > 0 && (
            <span className="ml-2 text-sm font-normal text-gray-500">
              ({criticalCount} critical)
            </span>
          )}
        </h3>
      </div>

      <div className="space-y-3">
        {visible.map((issue) => (
          <IssueCard
            key={issue.id}
            issue={issue}
            onFix={onFix}
            onDismiss={onDismiss}
          />
        ))}
      </div>

      {hiddenCount > 0 && (
        <div className="pt-2 text-center">
          <Button variant="ghost" size="sm" onClick={() => setExpanded(true)}>
            Show all {issues.length} issues
          </Button>
        </div>
      )}
    </div>
  );
}
