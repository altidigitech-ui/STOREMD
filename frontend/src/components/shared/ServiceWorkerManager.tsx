"use client";

import { useServiceWorker } from "@/hooks/use-service-worker";

export function ServiceWorkerManager(): null {
  useServiceWorker();
  return null;
}
