import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useHealth } from "@/hooks/use-health";
import { api } from "@/lib/api";
import type { HealthResponse } from "@/types";

vi.mock("@/lib/supabase", () => ({
  getSupabaseBrowserClient: () => ({
    auth: {
      getSession: async () => ({ data: { session: null } }),
    },
  }),
}));

describe("useHealth", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("returns the health payload when the API call succeeds", async () => {
    const payload: HealthResponse = {
      score: 67,
      mobile_score: 52,
      desktop_score: 81,
      trend: "up",
      trend_delta: 9,
      last_scan_at: null,
      issues_count: 3,
      critical_count: 1,
      previous_score: 58,
      history: [],
    };
    vi.spyOn(api.scans, "getHealth").mockResolvedValue(payload);

    const { result } = renderHook(() => useHealth("store-1"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    expect(result.current.data).toEqual(payload);
    expect(result.current.error).toBeNull();
  });

  it("surfaces an error when the API call fails", async () => {
    vi.spyOn(api.scans, "getHealth").mockRejectedValue(new Error("boom"));

    const { result } = renderHook(() => useHealth("store-1"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    expect(result.current.data).toBeNull();
    expect(result.current.error?.message).toBe("boom");
  });
});
