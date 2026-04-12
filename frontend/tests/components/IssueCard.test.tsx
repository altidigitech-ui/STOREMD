import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { IssueCard } from "@/components/dashboard/IssueCard";
import type { ScanIssue } from "@/types";

function makeIssue(overrides: Partial<ScanIssue> = {}): ScanIssue {
  return {
    id: "issue-1",
    module: "health",
    scanner: "app_impact",
    severity: "critical",
    title: "App 'Privy' injects 340KB of unminified JS",
    description: null,
    impact: "+1.8s load time",
    impact_value: 1.8,
    impact_unit: "seconds",
    fix_type: "manual",
    fix_description: "Consider replacing Privy with a lighter alternative",
    auto_fixable: true,
    fix_applied: false,
    dismissed: false,
    ...overrides,
  };
}

describe("IssueCard", () => {
  it("renders the title and impact", () => {
    render(<IssueCard issue={makeIssue()} />);
    expect(
      screen.getByText(/Privy.*340KB/),
    ).toBeInTheDocument();
    expect(screen.getByText(/\+1.8s load time/)).toBeInTheDocument();
  });

  it("renders the severity badge", () => {
    render(<IssueCard issue={makeIssue({ severity: "major" })} />);
    expect(screen.getByText("major")).toBeInTheDocument();
  });

  it("fires the dismiss callback with the issue id", () => {
    const onDismiss = vi.fn();
    render(
      <IssueCard issue={makeIssue()} onDismiss={onDismiss} />,
    );
    fireEvent.click(screen.getByText("Dismiss"));
    expect(onDismiss).toHaveBeenCalledWith("issue-1");
  });

  it("only renders the Fix button when auto_fixable is true", () => {
    const onFix = vi.fn();
    const { rerender } = render(
      <IssueCard
        issue={makeIssue({ auto_fixable: true })}
        onFix={onFix}
      />,
    );
    expect(screen.getByTestId("fix-button")).toBeInTheDocument();

    rerender(
      <IssueCard
        issue={makeIssue({ auto_fixable: false })}
        onFix={onFix}
      />,
    );
    expect(screen.queryByTestId("fix-button")).not.toBeInTheDocument();
  });
});
