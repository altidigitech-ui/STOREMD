"use client";

import { useOnlineStatus } from "@/hooks/use-online-status";

export function OfflineBanner() {
  const isOnline = useOnlineStatus();
  if (isOnline) return null;

  return (
    <div
      role="status"
      className="bg-yellow-50 border-b border-yellow-200 px-4 py-2 text-center"
    >
      <p className="text-xs text-yellow-800">
        You&apos;re offline. Showing cached data. Some features are
        unavailable.
      </p>
    </div>
  );
}
