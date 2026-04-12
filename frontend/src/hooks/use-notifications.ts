"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { NotificationsResponse } from "@/types";

export function useNotifications(unreadOnly: boolean = false) {
  const [data, setData] = useState<NotificationsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchList = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await api.notifications.list(undefined, unreadOnly);
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e : new Error(String(e)));
    } finally {
      setIsLoading(false);
    }
  }, [unreadOnly]);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  const markRead = useCallback(
    async (id: string) => {
      await api.notifications.markRead(id);
      await fetchList();
    },
    [fetchList],
  );

  return {
    data,
    isLoading,
    error,
    refetch: fetchList,
    markRead,
  };
}
