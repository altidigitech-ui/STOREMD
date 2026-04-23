import { LandingPageClient } from "@/components/landing/LandingPageClient";

export const metadata = {
  title:
    "StoreMD — One app. Five killed. Zero regrets.",
  description:
    "Stop paying 5 Shopify apps $150/month to send you reports you never read. StoreMD replaces your SEO, speed, accessibility, broken link and audit apps with one AI agent that actually fixes problems.",
  alternates: {
    canonical: "https://storemd.vercel.app",
  },
  openGraph: {
    title: "StoreMD — One app. Five killed. Zero regrets.",
    description:
      "The only Shopify app that uninstalls the others. Replace 5 apps with one agent that actually fixes what's broken. Save $852/year. Faster store. No more PDFs.",
    url: "https://storemd.vercel.app",
    siteName: "StoreMD",
    type: "website",
    images: [
      {
        url: "https://storemd.vercel.app/og-image.png",
        width: 1200,
        height: 630,
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "StoreMD — One app. Five killed. Zero regrets.",
    description:
      "The only Shopify app that uninstalls the others. Replace 5 with one agent that actually fixes what's broken.",
    images: ["https://storemd.vercel.app/og-image.png"],
  },
};

export default function LandingPage() {
  const installHref = process.env.NEXT_PUBLIC_BACKEND_URL
    ? `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/auth/install`
    : "/api/v1/auth/install";

  return <LandingPageClient installHref={installHref} />;
}
