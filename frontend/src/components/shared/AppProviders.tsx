"use client";

import type { ReactNode } from "react";
import { ToastProvider } from "@/components/ui/Toast";
import { ServiceWorkerManager } from "@/components/shared/ServiceWorkerManager";
import { SessionBootstrap } from "@/components/shared/SessionBootstrap";

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ToastProvider>
      <SessionBootstrap />
      <ServiceWorkerManager />
      {children}
    </ToastProvider>
  );
}
