// Public / non-authenticated layout.
// Used for the landing page and pricing page — no dashboard chrome.

import { TrackingProvider } from "@/components/landing/TrackingProvider";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-[#0a0a0f] text-slate-50 antialiased">
      <TrackingProvider />
      {children}
    </div>
  );
}
