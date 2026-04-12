"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useCurrentStore } from "@/hooks/use-current-store";
import { Card, CardContent, CardTitle } from "@/components/ui/Card";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";
import { cn, getScoreColor } from "@/lib/utils";
import type {
  ListingPriority,
  ListingsPrioritiesResponse,
  ListingsScanResponse,
  ProductListing,
} from "@/types";

export default function ListingsPage() {
  const { storeId, isLoading: loadingStore } = useCurrentStore();
  const [scan, setScan] = useState<ListingsScanResponse | null>(null);
  const [priorities, setPriorities] =
    useState<ListingsPrioritiesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sort, setSort] = useState<"score_asc" | "score_desc" | "revenue_desc">(
    "score_asc",
  );

  useEffect(() => {
    if (!storeId) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [scanData, prioritiesData] = await Promise.all([
          api.listings.scan(storeId as string, { sort, limit: 50 }),
          api.listings.priorities(storeId as string).catch(() => null),
        ]);
        if (cancelled) return;
        setScan(scanData);
        setPriorities(prioritiesData);
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof ApiError ? e.message : "Failed to load listings");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [storeId, sort]);

  if (loadingStore || loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;

  const products = scan?.data ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h1 className="text-2xl font-bold text-gray-900">Listings</h1>
        {scan && (
          <p className="text-sm text-gray-600">
            {scan.products_scanned} products scanned · avg score{" "}
            <span className={cn("font-medium", getScoreColor(scan.avg_score))}>
              {scan.avg_score}
            </span>
          </p>
        )}
      </div>

      {/* Top priorities */}
      {priorities && priorities.data.length > 0 && (
        <Card>
          <CardTitle>Top priorities</CardTitle>
          <CardContent>
            <ul className="divide-y divide-gray-100">
              {priorities.data.slice(0, 5).map((p: ListingPriority) => (
                <li
                  key={p.shopify_product_id}
                  className="flex items-center justify-between py-2 text-sm"
                >
                  <div className="min-w-0 flex-1 pr-3">
                    <p className="truncate font-medium text-gray-900">
                      {p.title || p.shopify_product_id}
                    </p>
                    {p.top_issue && (
                      <p className="truncate text-xs text-gray-500">
                        {p.top_issue}
                      </p>
                    )}
                  </div>
                  <div className="text-right text-xs">
                    <span
                      className={cn("font-semibold", getScoreColor(p.score ?? 0))}
                    >
                      {p.score ?? "—"}
                    </span>
                    {p.revenue_30d != null && (
                      <span className="ml-2 text-gray-500">
                        ${p.revenue_30d.toFixed(0)}/mo
                      </span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Catalogue table */}
      <Card>
        <div className="mb-3 flex items-center justify-between">
          <CardTitle>Catalogue</CardTitle>
          <select
            value={sort}
            onChange={(e) =>
              setSort(
                e.target.value as
                  | "score_asc"
                  | "score_desc"
                  | "revenue_desc",
              )
            }
            className="rounded-md border border-gray-300 px-2 py-1 text-xs"
          >
            <option value="score_asc">Score: Low → High</option>
            <option value="score_desc">Score: High → Low</option>
            <option value="revenue_desc">Revenue: High → Low</option>
          </select>
        </div>
        <CardContent>
          {products.length === 0 ? (
            <EmptyState
              title="No listings analyzed yet"
              message="Run a scan with the Listings module enabled to populate this view."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs text-gray-500">
                  <tr>
                    <th className="py-2 pr-3">Product</th>
                    <th className="py-2 pr-3 text-right">Score</th>
                    <th className="py-2 pr-3 text-right">Title</th>
                    <th className="py-2 pr-3 text-right">Description</th>
                    <th className="py-2 pr-3 text-right">Images</th>
                    <th className="py-2 pr-3 text-right">SEO</th>
                    <th className="py-2 text-right">Revenue 30d</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {products.map((p: ProductListing) => (
                    <tr key={p.shopify_product_id}>
                      <td className="py-2 pr-3">
                        <p className="truncate font-medium text-gray-900">
                          {p.title || p.shopify_product_id}
                        </p>
                      </td>
                      <td
                        className={cn(
                          "py-2 pr-3 text-right font-semibold",
                          getScoreColor(p.score ?? 0),
                        )}
                      >
                        {p.score ?? "—"}
                      </td>
                      <td className="py-2 pr-3 text-right">
                        {p.title_score ?? "—"}
                      </td>
                      <td className="py-2 pr-3 text-right">
                        {p.description_score ?? "—"}
                      </td>
                      <td className="py-2 pr-3 text-right">
                        {p.images_score ?? "—"}
                      </td>
                      <td className="py-2 pr-3 text-right">
                        {p.seo_score ?? "—"}
                      </td>
                      <td className="py-2 text-right text-gray-600">
                        {p.revenue_30d != null
                          ? `$${p.revenue_30d.toFixed(0)}`
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
