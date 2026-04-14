"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useCurrentStore } from "@/hooks/use-current-store";
import { Card, CardContent, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";
import { useToast } from "@/components/ui/Toast";
import type {
  BillingProvider,
  Plan,
  Store,
  UsageResponse,
} from "@/types";

const PLAN_ORDER: Record<Plan, number> = {
  free: 0,
  starter: 1,
  pro: 2,
  agency: 3,
};

function planRank(plan: Plan): number {
  return PLAN_ORDER[plan] ?? 0;
}

export default function SettingsPage() {
  const { storeId } = useCurrentStore();
  const { toast } = useToast();

  const [store, setStore] = useState<Store | null>(null);
  const [usage, setUsage] = useState<UsageResponse | null>(null);
  const [billingProvider, setBillingProvider] =
    useState<BillingProvider>(null);
  const [upgrading, setUpgrading] = useState<Plan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [email, setEmail] = useState("");
  const [threshold, setThreshold] = useState(5);

  useEffect(() => {
    if (!storeId) return;
    let cancelled = false;
    (async () => {
      try {
        const [storeData, usageData, statusData] = await Promise.all([
          api.stores.get(storeId),
          api.billing.getUsage(),
          api.shopifyBilling.status().catch(() => null),
        ]);
        if (cancelled) return;
        setStore(storeData);
        setUsage(usageData);
        setBillingProvider(statusData?.billing_provider ?? null);
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof ApiError ? e.message : "Failed to load settings",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [storeId]);

  async function handleManageBilling() {
    try {
      const { portal_url } = await api.billing.getPortal();
      window.location.href = portal_url;
    } catch (e) {
      toast({
        title: "Could not open portal",
        description:
          e instanceof ApiError ? e.message : "Please try again.",
        variant: "destructive",
      });
    }
  }

  // Merchants that came from the Shopify App Store (or haven't subscribed yet)
  // go through Shopify Billing. Explicit Stripe subscribers keep using Stripe.
  const useShopifyBilling = billingProvider !== "stripe";

  async function handleUpgrade(plan: Plan) {
    setUpgrading(plan);
    try {
      if (useShopifyBilling) {
        const { confirmation_url } = await api.shopifyBilling.subscribe(plan);
        window.location.href = confirmation_url;
      } else {
        const { checkout_url } = await api.billing.createCheckout(plan);
        window.location.href = checkout_url;
      }
    } catch (e) {
      toast({
        title: "Could not start upgrade",
        description:
          e instanceof ApiError ? e.message : "Please try again.",
        variant: "destructive",
      });
      setUpgrading(null);
    }
  }

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Settings</h1>

      {/* Alert Preferences */}
      <Card>
        <CardTitle>Alert Preferences</CardTitle>
        <CardContent>
          <div className="space-y-3">
            <label className="block">
              <span className="text-sm text-gray-700">
                Send alerts to
              </span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@store.com"
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </label>
            <div>
              <span className="text-sm text-gray-700">
                Alert me when score drops by
              </span>
              <div className="mt-1 flex items-center gap-3">
                <input
                  type="range"
                  min={1}
                  max={20}
                  value={threshold}
                  onChange={(e) => setThreshold(Number(e.target.value))}
                  className="flex-1"
                />
                <span className="w-16 text-sm font-medium text-gray-900">
                  {threshold} pts
                </span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Notification Settings */}
      <Card>
        <CardTitle>Notification Settings</CardTitle>
        <CardContent>
          <p className="text-sm text-gray-600">
            Push notifications and delivery limits. Enable them from your
            device when prompted during onboarding.
          </p>
        </CardContent>
      </Card>

      {/* Plan & Billing */}
      <Card>
        <CardTitle>Plan &amp; Billing</CardTitle>
        <CardContent>
          {usage && (
            <>
              <p className="text-sm text-gray-700">
                Current plan:{" "}
                <span className="font-medium capitalize">{usage.plan}</span>
              </p>
              <div className="mt-3 space-y-2">
                {usage.usage.map((u) => {
                  const pct = u.limit
                    ? Math.min(100, Math.round((u.count / u.limit) * 100))
                    : 0;
                  return (
                    <div key={u.type}>
                      <div className="flex items-baseline justify-between text-xs">
                        <span className="capitalize text-gray-600">
                          {u.type.replace(/_/g, " ")}
                        </span>
                        <span className="text-gray-500">
                          {u.count} / {u.limit || "—"}
                        </span>
                      </div>
                      <div className="mt-1 h-2 overflow-hidden rounded-full bg-gray-100">
                        <div
                          className="h-full bg-blue-600"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          )}
          <div className="mt-4 flex flex-wrap gap-2">
            {(["starter", "pro", "agency"] as const).map((plan) => {
              const currentPlan = (usage?.plan ?? "free") as Plan;
              if (currentPlan === plan) return null;
              const isUpgrade =
                planRank(plan) > planRank(currentPlan);
              return (
                <Button
                  key={plan}
                  variant={isUpgrade ? "default" : "outline"}
                  disabled={upgrading !== null}
                  onClick={() => handleUpgrade(plan)}
                >
                  {upgrading === plan
                    ? "Redirecting…"
                    : `${isUpgrade ? "Upgrade" : "Switch"} to ${plan[0].toUpperCase()}${plan.slice(1)}`}
                </Button>
              );
            })}
            {!useShopifyBilling && (
              <Button variant="outline" onClick={handleManageBilling}>
                Manage subscription
              </Button>
            )}
          </div>
          <p className="mt-2 text-xs text-gray-500">
            {useShopifyBilling
              ? "Billed through Shopify — charges appear on your Shopify invoice."
              : "Billed through Stripe."}
          </p>
        </CardContent>
      </Card>

      {/* Store Info */}
      <Card>
        <CardTitle>Store Info</CardTitle>
        <CardContent>
          {store ? (
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-500">Domain</dt>
                <dd className="font-medium">{store.shopify_shop_domain}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Theme</dt>
                <dd className="font-medium">{store.theme_name ?? "—"}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Apps installed</dt>
                <dd className="font-medium">{store.apps_count}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Products</dt>
                <dd className="font-medium">{store.products_count}</dd>
              </div>
            </dl>
          ) : (
            <p className="text-sm text-gray-500">No store data available.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
