"use client";

import { api } from "@/lib/api";
import { useFetch } from "@/hooks/use-fetch";
import type { Store } from "@/types";

export function useStore(storeId: string | null) {
  return useFetch<Store>(
    () => api.stores.get(storeId as string),
    [storeId],
    { enabled: Boolean(storeId) },
  );
}
