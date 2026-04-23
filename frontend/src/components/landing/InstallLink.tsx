"use client";

import { MouseEvent, ReactNode } from "react";
import { trackEvent, withTrackingParams } from "@/lib/tracking";
import { useInstallModal } from "@/lib/install-modal-context";

interface InstallLinkProps {
  href: string;
  className?: string;
  children: ReactNode;
  label?: string;
}

export function InstallLink({
  href,
  className,
  children,
  label,
}: InstallLinkProps) {
  const modal = useInstallModal();

  const onClick = (event: MouseEvent<HTMLAnchorElement>) => {
    if (event.defaultPrevented) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) {
      return;
    }
    event.preventDefault();
    trackEvent("cta_click", { href, label: label ?? "" });

    if (modal) {
      modal.openModal();
      return;
    }

    // Fallback: navigate directly (no modal context available)
    const enriched = withTrackingParams(href);
    trackEvent("install_start", { href: enriched });
    window.location.href = enriched;
  };

  return (
    <a href={href} onClick={onClick} className={className}>
      {children}
    </a>
  );
}
