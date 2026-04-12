"use client";

import { useEffect } from "react";
import { getSupabaseBrowserClient } from "@/lib/supabase";

export function SessionBootstrap() {
  useEffect(() => {
    if (typeof window === "undefined") return;

    const url = new URL(window.location.href);
    const accessToken = url.searchParams.get("access_token");
    const refreshToken = url.searchParams.get("refresh_token");
    if (!accessToken || !refreshToken) return;

    const supabase = getSupabaseBrowserClient();
    supabase.auth
      .setSession({ access_token: accessToken, refresh_token: refreshToken })
      .finally(() => {
        url.searchParams.delete("access_token");
        url.searchParams.delete("refresh_token");
        url.searchParams.delete("expires_in");
        url.searchParams.delete("token_type");
        window.history.replaceState(null, "", url.toString());
      });
  }, []);

  return null;
}
