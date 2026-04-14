"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { getSupabaseBrowserClient } from "@/lib/supabase";

type Status =
  | { state: "loading" }
  | { state: "error"; message: string };

function VerifyInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<Status>({ state: "loading" });

  useEffect(() => {
    let cancelled = false;
    const supabase = getSupabaseBrowserClient();

    function redirectTo(path: string) {
      if (cancelled) return;
      router.replace(path);
    }

    const target = searchParams.get("target") ?? "/dashboard";

    async function run() {
      // Case A — PKCE flow: ?code=xxx
      const code = searchParams.get("code");
      if (code) {
        const { error } = await supabase.auth.exchangeCodeForSession(code);
        if (error) {
          setStatus({ state: "error", message: error.message });
          return;
        }
        redirectTo(target);
        return;
      }

      // Case B — OTP token hash: ?token=xxx&type=magiclink&email=xxx
      const token = searchParams.get("token");
      const typeParam = searchParams.get("type");
      const email = searchParams.get("email");
      if (token && email) {
        type OtpType =
          | "signup"
          | "invite"
          | "magiclink"
          | "recovery"
          | "email_change"
          | "email";
        const allowed: OtpType[] = [
          "signup",
          "invite",
          "magiclink",
          "recovery",
          "email_change",
          "email",
        ];
        const type = allowed.includes(typeParam as OtpType)
          ? (typeParam as OtpType)
          : "magiclink";
        const { error } = await supabase.auth.verifyOtp({
          email,
          token,
          type,
        });
        if (error) {
          setStatus({ state: "error", message: error.message });
          return;
        }
        redirectTo(target);
        return;
      }

      // Case C — hash fragment: #access_token=xxx&refresh_token=xxx
      // The Supabase client auto-handles this via detectSessionInUrl, but we
      // still need to wait for it and then redirect. Also handle Supabase
      // error params in the hash (e.g. #error=access_denied).
      if (typeof window !== "undefined" && window.location.hash) {
        const hash = new URLSearchParams(
          window.location.hash.replace(/^#/, ""),
        );
        const hashError = hash.get("error_description") ?? hash.get("error");
        if (hashError) {
          setStatus({ state: "error", message: hashError });
          return;
        }
        const accessToken = hash.get("access_token");
        const refreshToken = hash.get("refresh_token");
        if (accessToken && refreshToken) {
          const { error } = await supabase.auth.setSession({
            access_token: accessToken,
            refresh_token: refreshToken,
          });
          if (error) {
            setStatus({ state: "error", message: error.message });
            return;
          }
          window.history.replaceState(
            null,
            "",
            window.location.pathname + window.location.search,
          );
          redirectTo(target);
          return;
        }
      }

      // Last-resort: maybe the Supabase client already installed a session
      // via onAuthStateChange. Subscribe briefly before giving up.
      const { data } = await supabase.auth.getSession();
      if (data.session) {
        redirectTo(target);
        return;
      }

      const { data: sub } = supabase.auth.onAuthStateChange((event, sess) => {
        if (sess && (event === "SIGNED_IN" || event === "TOKEN_REFRESHED")) {
          sub.subscription.unsubscribe();
          redirectTo(target);
        }
      });

      // If nothing has happened in 4s, surface an error.
      setTimeout(() => {
        if (cancelled) return;
        sub.subscription.unsubscribe();
        setStatus({
          state: "error",
          message: "No sign-in token found. The link may have expired.",
        });
      }, 4000);
    }

    run().catch((e: unknown) => {
      if (cancelled) return;
      setStatus({
        state: "error",
        message: e instanceof Error ? e.message : "Verification failed",
      });
    });

    return () => {
      cancelled = true;
    };
  }, [router, searchParams]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      {status.state === "error" ? (
        <div className="max-w-md rounded-lg border border-red-200 bg-white p-6 text-center shadow-sm">
          <h1 className="text-lg font-semibold text-gray-900">
            Could not sign you in
          </h1>
          <p className="mt-2 text-sm text-gray-600">{status.message}</p>
          <Link
            href="/login"
            className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:underline"
          >
            Try again
          </Link>
        </div>
      ) : (
        <div className="flex items-center gap-3 text-gray-600">
          <div
            className="h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600"
            aria-hidden
          />
          <span className="text-sm">Signing you in…</span>
        </div>
      )}
    </div>
  );
}

export default function VerifyPage() {
  return (
    <Suspense fallback={null}>
      <VerifyInner />
    </Suspense>
  );
}
