"use client";

import { useEffect } from "react";
import {
  initTracking,
  trackEvent,
  withTrackingParams,
} from "@/lib/tracking";

/**
 * Mounts on the public landing layout. Handles:
 *  - one-time tracking init (session_id + UTM capture + first pageview)
 *  - delegated click handling on Shopify install CTAs to fire
 *    `cta_click` and append UTM/session_id query params before the
 *    browser follows the navigation.
 */
export function TrackingProvider() {
  useEffect(() => {
    initTracking();

    const onClick = (event: MouseEvent) => {
      const target = event.target;
      if (!(target instanceof Element)) return;

      const anchor = target.closest("a") as HTMLAnchorElement | null;
      if (!anchor) return;
      const href = anchor.getAttribute("href");
      if (!href) return;

      const isInstall = href.includes("/api/v1/auth/install");
      if (!isInstall) return;

      // Fire-and-forget — don't block navigation.
      trackEvent("cta_click", {
        href,
        label: (anchor.textContent || "").trim().slice(0, 80),
      });
      trackEvent("install_start", { href });

      // Rewrite href in-place with UTM + session_id so the backend
      // /install endpoint can persist attribution.
      const enriched = withTrackingParams(href);
      if (enriched !== href) {
        anchor.setAttribute("href", enriched);
      }
    };

    document.addEventListener("click", onClick, { capture: true });
    return () => document.removeEventListener("click", onClick, { capture: true });
  }, []);

  return null;
}
