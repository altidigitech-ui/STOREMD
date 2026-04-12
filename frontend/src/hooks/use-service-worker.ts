"use client";

import { useEffect } from "react";
import { useToast } from "@/components/ui/Toast";

const UPDATE_CHECK_MS = 60 * 60 * 1000;

export function useServiceWorker() {
  const { toast } = useToast();

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!("serviceWorker" in navigator)) return;

    let interval: ReturnType<typeof setInterval> | null = null;

    navigator.serviceWorker
      .register("/sw.js")
      .then((registration) => {
        interval = setInterval(() => {
          registration.update();
        }, UPDATE_CHECK_MS);

        registration.addEventListener("updatefound", () => {
          const newWorker = registration.installing;
          if (!newWorker) return;
          newWorker.addEventListener("statechange", () => {
            if (
              newWorker.state === "installed" &&
              navigator.serviceWorker.controller
            ) {
              toast({
                title: "Update available",
                description:
                  "Refresh to get the latest version of StoreMD.",
                durationMs: 1_000_000_000,
              });
            }
          });
        });
      })
      .catch(() => {
        // Registration errors are not actionable by the user.
      });

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [toast]);
}
