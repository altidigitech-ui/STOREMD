import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ScoreHero } from "@/components/dashboard/ScoreHero";

describe("ScoreHero", () => {
  it("displays the score inside the health-score wrapper", () => {
    render(
      <ScoreHero
        score={67}
        mobileScore={52}
        desktopScore={81}
        trend="up"
        trendDelta={9}
        lastScanAt={new Date().toISOString()}
      />,
    );
    const wrapper = screen.getByTestId("health-score");
    expect(wrapper).toBeInTheDocument();
    expect(wrapper.textContent).toContain("67");
  });

  it("renders a positive trend with a + sign", () => {
    render(
      <ScoreHero
        score={67}
        mobileScore={52}
        desktopScore={81}
        trend="up"
        trendDelta={9}
        lastScanAt={null}
      />,
    );
    expect(screen.getByText(/\+9 since last week/)).toBeInTheDocument();
  });

  it("renders a negative trend with a - sign", () => {
    render(
      <ScoreHero
        score={55}
        mobileScore={40}
        desktopScore={70}
        trend="down"
        trendDelta={4}
        lastScanAt={null}
      />,
    );
    expect(screen.getByText(/-4 since last week/)).toBeInTheDocument();
  });

  it("applies a red color for low scores", () => {
    const { container } = render(
      <ScoreHero
        score={15}
        mobileScore={10}
        desktopScore={20}
        trend="stable"
        trendDelta={0}
        lastScanAt={null}
      />,
    );
    // The /100 label uses getScoreColor which resolves to text-red-600
    // for scores below 20.
    const label = container.querySelector(".text-red-600");
    expect(label).not.toBeNull();
  });

  it("switches the CTA to an upgrade button when the scan limit is reached", () => {
    const onUpgrade = vi.fn();
    render(
      <ScoreHero
        score={67}
        mobileScore={52}
        desktopScore={81}
        trend="stable"
        trendDelta={0}
        lastScanAt={null}
        scansRemaining={0}
        onUpgrade={onUpgrade}
      />,
    );
    const cta = screen.getByTestId("scan-now");
    expect(cta.textContent).toMatch(/Upgrade/);
  });
});
