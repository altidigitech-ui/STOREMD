"use client";

import { MouseEvent, ReactNode } from "react";
import { trackEvent, withTrackingParams } from "@/lib/tracking";

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
  const onClick = (event: MouseEvent<HTMLAnchorElement>) => {
    if (event.defaultPrevented) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) {
      return;
    }
    event.preventDefault();
    const enriched = withTrackingParams(href);
    trackEvent("cta_click", { href: enriched, label: label ?? "" });
    trackEvent("install_start", { href: enriched });
    window.location.href = enriched;
  };

  return (
    <a href={href} onClick={onClick} className={className}>
      {children}
    </a>
  );
}
