"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Mail, ShoppingBag } from "lucide-react";
import { getSupabaseBrowserClient } from "@/lib/supabase";

type MagicStatus =
  | { state: "idle" }
  | { state: "loading" }
  | { state: "sent"; email: string }
  | { state: "error"; message: string };

function normalizeShopDomain(raw: string): string | null {
  const trimmed = raw.trim().toLowerCase();
  if (!trimmed) return null;
  const stripped = trimmed
    .replace(/^https?:\/\//, "")
    .replace(/\/.*$/, "")
    .replace(/\.myshopify\.com$/, "");
  if (!/^[a-z0-9][a-z0-9-]*$/.test(stripped)) return null;
  return `${stripped}.myshopify.com`;
}

function getInstallBase(): string {
  return process.env.NEXT_PUBLIC_BACKEND_URL
    ? `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/auth/install`
    : "/api/v1/auth/install";
}

export default function LoginPage() {
  const [shop, setShop] = useState("");
  const [shopError, setShopError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [magic, setMagic] = useState<MagicStatus>({ state: "idle" });

  function handleShopifyLogin(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const domain = normalizeShopDomain(shop);
    if (!domain) {
      setShopError(
        "Enter a valid store, e.g. your-store.myshopify.com",
      );
      return;
    }
    setShopError(null);
    const url = `${getInstallBase()}?shop=${encodeURIComponent(domain)}`;
    window.location.href = url;
  }

  async function handleMagicLink(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const trimmed = email.trim();
    if (!trimmed) {
      setMagic({ state: "error", message: "Enter your email address." });
      return;
    }
    setMagic({ state: "loading" });
    try {
      const supabase = getSupabaseBrowserClient();
      const { error } = await supabase.auth.signInWithOtp({
        email: trimmed,
        options: {
          emailRedirectTo:
            typeof window !== "undefined"
              ? `${window.location.origin}/auth/verify`
              : undefined,
        },
      });
      if (error) {
        setMagic({ state: "error", message: error.message });
        return;
      }
      setMagic({ state: "sent", email: trimmed });
    } catch (err) {
      setMagic({
        state: "error",
        message:
          err instanceof Error ? err.message : "Could not send magic link.",
      });
    }
  }

  return (
    <div className="min-h-screen bg-white text-gray-900">
      <div
        className="absolute inset-x-0 top-0 -z-10 h-80 bg-[radial-gradient(ellipse_at_top,rgba(37,99,235,0.08),transparent_60%)]"
        aria-hidden
      />

      <div className="mx-auto w-full max-w-md px-6 pt-8">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm font-medium text-gray-600 transition-colors hover:text-gray-900"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden />
          Back to home
        </Link>
      </div>

      <main className="mx-auto flex min-h-[calc(100vh-4rem)] w-full max-w-md flex-col justify-center px-6 py-12">
        <div className="text-center">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-lg font-bold text-gray-900"
          >
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-md bg-blue-600 text-white">
              S
            </span>
            StoreMD
          </Link>
          <h1 className="mt-6 text-3xl font-bold tracking-tight text-gray-900">
            Log in to StoreMD
          </h1>
          <p className="mt-2 text-sm text-gray-600">
            Sign in with your Shopify store or your email.
          </p>
        </div>

        <div className="mt-10 space-y-8">
          <form onSubmit={handleShopifyLogin} className="space-y-3">
            <label
              htmlFor="shop"
              className="block text-sm font-medium text-gray-800"
            >
              Shopify store
            </label>
            <input
              id="shop"
              type="text"
              autoComplete="off"
              placeholder="your-store.myshopify.com"
              value={shop}
              onChange={(e) => {
                setShop(e.target.value);
                if (shopError) setShopError(null);
              }}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 placeholder-gray-400 shadow-sm transition-colors focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
            {shopError && (
              <p className="text-xs text-red-600">{shopError}</p>
            )}
            <button
              type="submit"
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-200"
            >
              <ShoppingBag className="h-4 w-4" aria-hidden />
              Log in with Shopify
            </button>
          </form>

          <div className="relative">
            <div className="absolute inset-0 flex items-center" aria-hidden>
              <div className="w-full border-t border-gray-200" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-white px-3 text-xs uppercase tracking-wider text-gray-500">
                or
              </span>
            </div>
          </div>

          <form onSubmit={handleMagicLink} className="space-y-3">
            <label
              htmlFor="email"
              className="block text-sm font-medium text-gray-800"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={magic.state === "loading" || magic.state === "sent"}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 placeholder-gray-400 shadow-sm transition-colors focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 disabled:bg-gray-50"
            />
            <button
              type="submit"
              disabled={magic.state === "loading" || magic.state === "sent"}
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm font-semibold text-gray-900 shadow-sm transition-colors hover:bg-gray-50 focus:outline-none focus:ring-4 focus:ring-gray-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Mail className="h-4 w-4" aria-hidden />
              {magic.state === "loading"
                ? "Sending…"
                : magic.state === "sent"
                  ? "Link sent"
                  : "Send magic link"}
            </button>
            {magic.state === "sent" && (
              <p className="rounded-md border border-green-200 bg-green-50 px-3 py-2 text-xs text-green-800">
                Check your email ({magic.email}) for the login link.
              </p>
            )}
            {magic.state === "error" && (
              <p className="text-xs text-red-600">{magic.message}</p>
            )}
          </form>
        </div>

        <p className="mt-10 text-center text-xs text-gray-500">
          New to StoreMD?{" "}
          <Link
            href="/"
            className="font-medium text-blue-600 hover:underline"
          >
            Get your free health score →
          </Link>
        </p>
      </main>
    </div>
  );
}
