"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getSupabaseBrowserClient } from "@/lib/supabase";

export function SessionBootstrap() {
  const router = useRouter();

  useEffect(() => {
    if (typeof window === "undefined") return;

    const supabase = getSupabaseBrowserClient();

    async function install() {
      const url = new URL(window.location.href);

      // Query-param style (legacy: backend minted ?access_token=…&refresh_token=…)
      const qsAccess = url.searchParams.get("access_token");
      const qsRefresh = url.searchParams.get("refresh_token");
      if (qsAccess && qsRefresh) {
        await supabase.auth.setSession({
          access_token: qsAccess,
          refresh_token: qsRefresh,
        });
        url.searchParams.delete("access_token");
        url.searchParams.delete("refresh_token");
        url.searchParams.delete("expires_in");
        url.searchParams.delete("token_type");
        window.history.replaceState(null, "", url.toString());
        router.refresh();
        return;
      }

      // Hash-fragment style (Supabase implicit flow)
      if (window.location.hash) {
        const hash = new URLSearchParams(
          window.location.hash.replace(/^#/, ""),
        );
        const hAccess = hash.get("access_token");
        const hRefresh = hash.get("refresh_token");
        if (hAccess && hRefresh) {
          await supabase.auth.setSession({
            access_token: hAccess,
            refresh_token: hRefresh,
          });
          window.history.replaceState(
            null,
            "",
            window.location.pathname + window.location.search,
          );
          router.refresh();
        }
      }
    }

    install();
  }, [router]);

  return null;
}
