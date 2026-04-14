"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getSupabaseBrowserClient } from "@/lib/supabase";
import { TabBar } from "@/components/layout/TabBar";
import { MobileNav } from "@/components/layout/MobileNav";
import { PageTransition } from "@/components/layout/PageTransition";
import { OfflineBanner } from "@/components/shared/OfflineBanner";
import type { Plan } from "@/types";

interface MerchantSession {
  plan: Plan;
  onboardingCompleted: boolean;
  email: string | null;
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [session, setSession] = useState<MerchantSession | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function check() {
      try {
        const supabase = getSupabaseBrowserClient();
        const { data } = await supabase.auth.getSession();

        if (cancelled) return;

        if (!data.session) {
          // SessionBootstrap may still be installing tokens from the URL
          // — let onAuthStateChange wake us up rather than redirecting eagerly.
          const pending =
            typeof window !== "undefined" &&
            new URL(window.location.href).searchParams.has("access_token");
          if (!pending) router.replace("/");
          return;
        }

        const meta = (data.session.user.user_metadata ?? {}) as Record<
          string,
          unknown
        >;
        const plan = (meta.plan as Plan | undefined) ?? "free";
        const onboardingCompleted = Boolean(meta.onboarding_completed);
        const email = data.session.user.email ?? null;

        if (!onboardingCompleted) {
          router.replace("/onboarding");
          return;
        }

        setSession({ plan, onboardingCompleted, email });
      } finally {
        if (!cancelled) setChecking(false);
      }
    }

    check();

    const supabase = getSupabaseBrowserClient();
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(() => {
      if (!cancelled) check();
    });

    return () => {
      cancelled = true;
      subscription.unsubscribe();
    };
  }, [router]);

  if (checking || !session) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div
          className="h-8 w-8 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600"
          aria-label="Loading"
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <OfflineBanner />
      <header className="sticky top-0 z-20 border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded bg-blue-600" aria-hidden />
            <span className="text-base font-semibold">StoreMD</span>
          </div>
          <MobileNav plan={session.plan} email={session.email} />
        </div>
        <div className="hidden border-t border-gray-100 md:block">
          <div className="mx-auto max-w-6xl px-4">
            <TabBar plan={session.plan} email={session.email} />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <PageTransition>{children}</PageTransition>
      </main>
    </div>
  );
}
