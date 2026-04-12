"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { getSupabaseBrowserClient } from "@/lib/supabase";

function VerifyInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const email = searchParams.get("email");
    const token = searchParams.get("token");
    const target = searchParams.get("target") ?? "/dashboard";

    if (!email || !token) {
      router.replace("/");
      return;
    }

    const supabase = getSupabaseBrowserClient();
    supabase.auth
      .verifyOtp({ email, token, type: "magiclink" })
      .then(({ error: err }) => {
        if (err) {
          setError(err.message);
          return;
        }
        router.replace(target);
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "Verification failed");
      });
  }, [router, searchParams]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      {error ? (
        <div className="max-w-md rounded-lg border border-red-200 bg-white p-6 text-center shadow-sm">
          <h1 className="text-lg font-semibold text-gray-900">
            Could not sign you in
          </h1>
          <p className="mt-2 text-sm text-gray-600">{error}</p>
          <p className="mt-4 text-sm text-gray-500">
            Please reinstall StoreMD from your Shopify admin.
          </p>
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
