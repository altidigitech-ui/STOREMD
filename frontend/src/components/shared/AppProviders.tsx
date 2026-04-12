"use client";

import type { ReactNode } from "react";
import { ToastProvider } from "@/components/ui/Toast";
import { ServiceWorkerManager } from "@/components/shared/ServiceWorkerManager";

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ToastProvider>
      <ServiceWorkerManager />
      {children}
    </ToastProvider>
  );
}
