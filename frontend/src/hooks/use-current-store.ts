"use client";

import { useEffect, useState } from "react";
import { getSupabaseBrowserClient } from "@/lib/supabase";

/**
 * Resolves the current store id from the authenticated Supabase session.
 *
 * Merchants have a 1:N relationship to stores, but at this phase the
 * dashboard assumes a single active store, stored in the user metadata
 * under `active_store_id` (set by the backend at OAuth callback).
 */
export function useCurrentStore(): {
  storeId: string | null;
  isLoading: boolean;
  error: Error | null;
} {
  const [storeId, setStoreId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const supabase = getSupabaseBrowserClient();
        const { data } = await supabase.auth.getSession();
        if (cancelled) return;

        const user = data.session?.user;
        const appMeta = (user?.app_metadata ?? {}) as Record<string, unknown>;
        const userMeta = (user?.user_metadata ?? {}) as Record<string, unknown>;
        const active = appMeta.active_store_id ?? userMeta.active_store_id;
        if (typeof active === "string" && active.length > 0) {
          setStoreId(active);
        } else {
          setStoreId(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e : new Error(String(e)));
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    load();

    const supabase = getSupabaseBrowserClient();
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(() => {
      if (!cancelled) load();
    });

    return () => {
      cancelled = true;
      subscription.unsubscribe();
    };
  }, []);

  return { storeId, isLoading, error };
}
