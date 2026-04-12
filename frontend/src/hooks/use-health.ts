"use client";

import { api } from "@/lib/api";
import { useFetch } from "@/hooks/use-fetch";
import type { HealthResponse } from "@/types";

export function useHealth(storeId: string | null) {
  return useFetch<HealthResponse>(
    () => api.scans.getHealth(storeId as string),
    [storeId],
    { enabled: Boolean(storeId) },
  );
}
