import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AppProviders } from "@/components/shared/AppProviders";

export const metadata: Metadata = {
  title: "StoreMD — Shopify Store Health",
  description: "AI agent that monitors your Shopify store health 24/7",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "StoreMD",
  },
  icons: {
    apple: "/icons/icon-192x192.png",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: "#2563eb",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-sans">
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
