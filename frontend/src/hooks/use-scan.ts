"use client";

import { api } from "@/lib/api";
import { useFetch } from "@/hooks/use-fetch";
import type { ScanDetailResponse } from "@/types";

export function useScan(storeId: string | null, scanId: string | null) {
  return useFetch<ScanDetailResponse>(
    () => api.scans.get(storeId as string, scanId as string),
    [storeId, scanId],
    { enabled: Boolean(storeId && scanId) },
  );
}
