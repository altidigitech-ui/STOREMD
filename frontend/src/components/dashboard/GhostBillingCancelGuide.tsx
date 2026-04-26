"use client";

import { useState } from "react";
import { ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import type { ScanIssue } from "@/types";

interface GhostBillingCancelGuideProps {
  issue: ScanIssue;
  onDismiss: (issueId: string) => void;
}

export function GhostBillingCancelGuide({
  issue,
  onDismiss,
}: GhostBillingCancelGuideProps) {
  const [open, setOpen] = useState(false);

  const ctx = issue.context ?? {};
  const cancelUrl = ctx.cancel_url ?? "";
  const chargeName = ctx.charge_name ?? "this app";
  const chargeAmount = ctx.charge_amount ?? "0";

  function handleMarkResolved() {
    setOpen(false);
    onDismiss(issue.id);
  }

  return (
    <>
      <Button
        size="sm"
        variant="outline"
        data-testid="ghost-billing-guide-button"
        onClick={() => setOpen(true)}
      >
        How to cancel →
      </Button>

      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title={`Cancel ghost charge — saves $${chargeAmount}/month`}
        testId="ghost-billing-cancel-dialog"
        className="max-w-sm"
      >
        <div className="space-y-4">
          {cancelUrl && (
            <a
              href={cancelUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex w-full items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
              data-testid="ghost-billing-open-shopify"
            >
              Open Shopify Billing
              <ExternalLink className="h-3.5 w-3.5 shrink-0" aria-hidden />
            </a>
          )}

          <ol className="space-y-3 text-sm text-gray-700">
            <li className="flex gap-3">
              <span
                aria-hidden
                className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-100 text-[11px] font-bold text-blue-700"
              >
                1
              </span>
              <span>
                Click <strong>Open Shopify Billing</strong> above — opens your
                billing settings in a new tab.
              </span>
            </li>
            <li className="flex gap-3">
              <span
                aria-hidden
                className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-100 text-[11px] font-bold text-blue-700"
              >
                2
              </span>
              <span>
                Find <strong>{chargeName}</strong> in the subscriptions list.
              </span>
            </li>
            <li className="flex gap-3">
              <span
                aria-hidden
                className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-100 text-[11px] font-bold text-blue-700"
              >
                3
              </span>
              <span>
                Click <strong>Cancel subscription</strong> — saves{" "}
                <strong>${chargeAmount}/month</strong> immediately.
              </span>
            </li>
          </ol>

          <div className="border-t border-gray-100 pt-3">
            <button
              type="button"
              className="w-full rounded-md border border-gray-200 px-4 py-2 text-sm text-gray-600 transition-colors hover:bg-gray-50"
              onClick={handleMarkResolved}
              data-testid="ghost-billing-mark-resolved"
            >
              Mark as resolved
            </button>
          </div>
        </div>
      </Dialog>
    </>
  );
}
