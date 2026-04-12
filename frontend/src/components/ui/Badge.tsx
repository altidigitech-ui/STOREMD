import type { HTMLAttributes } from "react";
import { cn, getSeverityColor } from "@/lib/utils";

type Severity = "critical" | "major" | "minor" | "info";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  severity?: Severity;
}

export function Badge({
  className,
  severity = "info",
  children,
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium",
        getSeverityColor(severity),
        className,
      )}
      {...props}
    >
      {children}
    </span>
  );
}
