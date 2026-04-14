// Public / non-authenticated layout.
// Used for the landing page and pricing page — no dashboard chrome.

import { TrackingProvider } from "@/components/landing/TrackingProvider";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-white text-gray-900">
      <TrackingProvider />
      {children}
    </div>
  );
}
