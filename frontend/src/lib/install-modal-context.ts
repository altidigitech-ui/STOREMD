"use client";

import { createContext, useContext } from "react";

interface InstallModalContextValue {
  openModal: () => void;
  installHref: string;
}

export const InstallModalContext =
  createContext<InstallModalContextValue | null>(null);

export function useInstallModal(): InstallModalContextValue | null {
  return useContext(InstallModalContext);
}
