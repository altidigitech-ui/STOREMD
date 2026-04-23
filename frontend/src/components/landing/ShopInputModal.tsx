"use client";

import { useEffect, useRef, useState, KeyboardEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X, Store, ArrowRight, AlertCircle } from "lucide-react";
import { trackEvent, withTrackingParams } from "@/lib/tracking";

const SHOP_REGEX = /^[a-zA-Z0-9][a-zA-Z0-9-]*\.myshopify\.com$/;

function normalizeShopDomain(raw: string): string {
  const trimmed = raw.trim().toLowerCase();
  if (trimmed.includes(".")) return trimmed;
  return `${trimmed}.myshopify.com`;
}

interface ShopInputModalProps {
  open: boolean;
  installHref: string;
  onClose: () => void;
}

export function ShopInputModal({ open, installHref, onClose }: ShopInputModalProps) {
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const backdropRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-focus and reset state when modal opens
  useEffect(() => {
    if (open) {
      setValue("");
      setError(null);
      // Small delay so the animation starts before focus steals layout
      const t = setTimeout(() => inputRef.current?.focus(), 50);
      return () => clearTimeout(t);
    }
  }, [open]);

  // Escape key
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose, open]);

  // Prevent body scroll while open
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  // Focus trap: Tab/Shift+Tab cycle within the modal
  useEffect(() => {
    if (!open) return;
    const el = containerRef.current;
    if (!el) return;

    const handleTabKey = (e: globalThis.KeyboardEvent) => {
      if (e.key !== "Tab") return;
      const focusable = el.querySelectorAll<HTMLElement>(
        'button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    document.addEventListener("keydown", handleTabKey);
    return () => document.removeEventListener("keydown", handleTabKey);
  }, [open]);

  function handleSubmit() {
    const normalized = normalizeShopDomain(value);
    if (!SHOP_REGEX.test(normalized)) {
      setError("Enter a valid Shopify store URL (e.g. yourstore.myshopify.com)");
      inputRef.current?.focus();
      return;
    }
    setError(null);
    const url = withTrackingParams(`${installHref}?shop=${normalized}`);
    trackEvent("shop_input_submit", { shop: normalized, href: url });
    window.location.href = url;
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") handleSubmit();
  }

  function handleBackdropClick(e: React.MouseEvent<HTMLDivElement>) {
    if (e.target === backdropRef.current) onClose();
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          ref={backdropRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby="shop-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center px-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          onClick={handleBackdropClick}
          style={{ backgroundColor: "rgba(10, 10, 15, 0.85)", backdropFilter: "blur(8px)" }}
        >
          <motion.div
            ref={containerRef}
            role="document"
            className="relative w-full max-w-md rounded-2xl border border-white/10 bg-[#0f0f1a] p-8 shadow-2xl"
            initial={{ opacity: 0, scale: 0.94, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.94, y: 12 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close button */}
            <button
              type="button"
              aria-label="Close modal"
              className="absolute right-4 top-4 rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-white/5 hover:text-slate-300"
              onClick={onClose}
            >
              <X size={18} aria-hidden="true" />
            </button>

            {/* Icon */}
            <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-xl bg-cyan-500/10 ring-1 ring-cyan-500/20">
              <Store size={22} className="text-cyan-400" aria-hidden="true" />
            </div>

            {/* Heading */}
            <h2
              id="shop-modal-title"
              className="font-display text-2xl font-bold tracking-tight text-white"
            >
              Enter your Shopify domain
            </h2>
            <p className="mt-2 text-sm text-slate-400">
              We&apos;ll scan your store and show you exactly what to fix — for free.
            </p>

            {/* Input */}
            <div className="mt-6">
              <label
                htmlFor="shop-domain-input"
                className="mb-2 block text-xs font-medium uppercase tracking-widest text-slate-500"
              >
                Shopify domain
              </label>
              <input
                ref={inputRef}
                id="shop-domain-input"
                type="text"
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="off"
                spellCheck={false}
                placeholder="yourstore.myshopify.com"
                value={value}
                onChange={(e) => {
                  setValue(e.target.value);
                  if (error) setError(null);
                }}
                onKeyDown={handleKeyDown}
                aria-describedby={error ? "shop-domain-error" : undefined}
                aria-invalid={!!error}
                className={[
                  "w-full rounded-xl border bg-white/5 px-4 py-3 text-sm text-slate-100 placeholder-slate-600",
                  "outline-none transition-all",
                  "focus:ring-2",
                  error
                    ? "border-red-500/50 focus:ring-red-500/30"
                    : "border-white/10 focus:border-cyan-500/50 focus:ring-cyan-500/20",
                ].join(" ")}
              />
              {error && (
                <p
                  id="shop-domain-error"
                  role="alert"
                  className="mt-2 flex items-center gap-1.5 text-xs text-red-400"
                >
                  <AlertCircle size={13} aria-hidden="true" />
                  {error}
                </p>
              )}
            </div>

            {/* CTA */}
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!value.trim()}
              className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-cyan-500 px-6 py-3.5 text-sm font-semibold text-[#0a0a0f] transition-all hover:bg-cyan-400 active:scale-[0.98] disabled:opacity-50"
            >
              Start free audit
              <ArrowRight size={16} aria-hidden="true" />
            </button>

            <p className="mt-4 text-center text-xs text-slate-600">
              No credit card required &middot; Installs in 30 seconds
            </p>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
