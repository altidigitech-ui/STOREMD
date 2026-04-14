"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getSupabaseBrowserClient } from "@/lib/supabase";
import { api, ApiError } from "@/lib/api";
import { isAdmin } from "@/lib/admin";
import { TabBar } from "@/components/layout/TabBar";
import { MobileNav } from "@/components/layout/MobileNav";
import { PageTransition } from "@/components/layout/PageTransition";
import { OfflineBanner } from "@/components/shared/OfflineBanner";
import type { Plan } from "@/types";

interface MerchantSession {
  plan: Plan;
  email: string | null;
}

type GateState =
  | { kind: "checking" }
  | { kind: "ready"; session: MerchantSession }
  | { kind: "needs_install"; email: string };

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [state, setState] = useState<GateState>({ kind: "checking" });

  useEffect(() => {
    let cancelled = false;

    async function check() {
      const supabase = getSupabaseBrowserClient();
      const { data } = await supabase.auth.getSession();

      if (cancelled) return;

      if (!data.session) {
        // SessionBootstrap may still be installing tokens from the URL —
        // wait for onAuthStateChange rather than redirecting eagerly.
        const pending =
          typeof window !== "undefined" &&
          (new URL(window.location.href).searchParams.has("access_token") ||
            window.location.hash.includes("access_token"));
        if (!pending) router.replace("/login");
        return;
      }

      const email = data.session.user.email ?? null;
      const meta = (data.session.user.user_metadata ?? {}) as Record<
        string,
        unknown
      >;
      const metaPlan = (meta.plan as Plan | undefined) ?? undefined;
      const metaOnboarding = Boolean(meta.onboarding_completed);

      // Admin always passes through.
      if (isAdmin(email)) {
        setState({
          kind: "ready",
          session: { plan: metaPlan ?? "agency", email },
        });
        return;
      }

      // Fast path: user_metadata already says onboarding is done.
      if (metaOnboarding) {
        setState({
          kind: "ready",
          session: { plan: metaPlan ?? "free", email },
        });
        return;
      }

      // Otherwise consult the backend — a merchant may exist (Shopify
      // install) even if user_metadata wasn't synced.
      try {
        const me = await api.auth.me();
        if (cancelled) return;
        if (me.onboarding_completed) {
          setState({
            kind: "ready",
            session: { plan: me.plan, email: me.email },
          });
        } else {
          // Merchant row exists but onboarding not marked done — let the
          // onboarding flow finish.
          router.replace("/onboarding");
        }
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          // No merchant profile for this account — likely signed up with
          // email/password but hasn't installed StoreMD on a Shopify store.
          setState({ kind: "needs_install", email: email ?? "" });
          return;
        }
        // Transient error — fall back to onboarding.
        router.replace("/onboarding");
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

  if (state.kind === "checking") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div
          className="h-8 w-8 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600"
          aria-label="Loading"
        />
      </div>
    );
  }

  if (state.kind === "needs_install") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
        <div className="max-w-md rounded-xl border border-gray-200 bg-white p-8 text-center shadow-sm">
          <h1 className="text-xl font-semibold text-gray-900">
            Install StoreMD on your Shopify store
          </h1>
          <p className="mt-2 text-sm text-gray-600">
            You're signed in as{" "}
            <span className="font-medium">{state.email}</span>, but no Shopify
            store is linked to this account yet. Install the app from your
            Shopify admin to get started.
          </p>
          <div className="mt-6 flex flex-col gap-3">
            <Link
              href="/login"
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
            >
              Connect your Shopify store
            </Link>
            <button
              type="button"
              onClick={async () => {
                const supabase = getSupabaseBrowserClient();
                await supabase.auth.signOut();
                router.replace("/login");
              }}
              className="text-xs font-medium text-gray-500 hover:text-gray-700"
            >
              Sign out
            </button>
          </div>
        </div>
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
          <MobileNav plan={state.session.plan} email={state.session.email} />
        </div>
        <div className="hidden border-t border-gray-100 md:block">
          <div className="mx-auto max-w-6xl px-4">
            <TabBar plan={state.session.plan} email={state.session.email} />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <PageTransition>{children}</PageTransition>
      </main>
    </div>
  );
}
