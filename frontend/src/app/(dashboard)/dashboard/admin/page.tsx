"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getSupabaseBrowserClient } from "@/lib/supabase";
import { isAdmin } from "@/lib/admin";
import {
  api,
  type AdminAnalytics,
  type AdminError,
  type AdminMerchant,
  type AdminOverview,
  type AdminScan,
} from "@/lib/api";

interface AdminData {
  overview: AdminOverview;
  merchants: AdminMerchant[];
  scans: AdminScan[];
  errors: AdminError[];
  analytics: AdminAnalytics;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function Kpi({
  label,
  value,
  sublabel,
}: {
  label: string;
  value: string | number;
  sublabel?: string;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="text-xs font-medium uppercase tracking-wide text-gray-500">
        {label}
      </div>
      <div className="mt-2 text-2xl font-semibold text-gray-900">{value}</div>
      {sublabel && (
        <div className="mt-1 text-xs text-gray-500">{sublabel}</div>
      )}
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mt-8">
      <h2 className="mb-3 text-lg font-semibold text-gray-900">{title}</h2>
      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
        {children}
      </div>
    </section>
  );
}

function Table({
  headers,
  rows,
}: {
  headers: string[];
  rows: (string | number | null)[][];
}) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            {headers.map((h) => (
              <th
                key={h}
                className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {rows.length === 0 ? (
            <tr>
              <td
                colSpan={headers.length}
                className="px-4 py-6 text-center text-sm text-gray-500"
              >
                No data.
              </td>
            </tr>
          ) : (
            rows.map((row, i) => (
              <tr key={i} className="hover:bg-gray-50">
                {row.map((cell, j) => (
                  <td key={j} className="px-4 py-2 text-gray-700">
                    {cell ?? "—"}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export default function AdminPage() {
  const router = useRouter();
  const [authChecked, setAuthChecked] = useState(false);
  const [data, setData] = useState<AdminData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function check() {
      const supabase = getSupabaseBrowserClient();
      const { data: sessionData } = await supabase.auth.getSession();
      const email = sessionData.session?.user.email ?? null;
      if (cancelled) return;
      if (!isAdmin(email)) {
        router.replace("/dashboard");
        return;
      }
      setAuthChecked(true);
    }
    check();
    return () => {
      cancelled = true;
    };
  }, [router]);

  useEffect(() => {
    if (!authChecked) return;
    let cancelled = false;
    (async () => {
      try {
        const [overview, merchantsResp, scansResp, errorsResp, analytics] =
          await Promise.all([
            api.admin.overview(),
            api.admin.merchants(),
            api.admin.scans(50),
            api.admin.errors(50),
            api.admin.analytics(),
          ]);
        if (cancelled) return;
        setData({
          overview,
          merchants: merchantsResp.merchants,
          scans: scansResp.scans,
          errors: errorsResp.errors,
          analytics,
        });
      } catch (err) {
        if (!cancelled) setError((err as Error).message);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authChecked]);

  if (!authChecked) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <div
          className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-purple-600"
          aria-label="Loading"
        />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        Failed to load admin data: {error}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <div
          className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-purple-600"
          aria-label="Loading"
        />
      </div>
    );
  }

  const { overview, merchants, scans, errors, analytics } = data;

  return (
    <div>
      <header className="mb-6 flex items-baseline justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Admin</h1>
          <p className="text-sm text-gray-500">
            Internal dashboard — visible only to altidigitech@gmail.com.
          </p>
        </div>
      </header>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Kpi label="Total Merchants" value={overview.total_merchants} />
        <Kpi
          label="Total Scans"
          value={overview.total_scans}
          sublabel={`${overview.scans_today} today / ${overview.scans_this_week} this week`}
        />
        <Kpi
          label="Active Subs"
          value={overview.active_subscriptions}
          sublabel={
            overview.avg_health_score !== null
              ? `Avg score: ${overview.avg_health_score}`
              : undefined
          }
        />
        <Kpi label="MRR (€)" value={overview.mrr} />
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Kpi
          label="Visits Today"
          value={overview.visits_today}
          sublabel={`${overview.visits_this_week}/wk · ${overview.visits_this_month}/mo`}
        />
        <Kpi label="Unique Visitors" value={overview.unique_visitors_today} />
        <Kpi label="Installs Today" value={overview.installs_today} />
        <Kpi
          label="Conversion Rate"
          value={`${overview.conversion_rate}%`}
          sublabel="installs / unique visitors today"
        />
      </div>

      <Section title="Funnel (last 30 days)">
        <Table
          headers={["Stage", "Count"]}
          rows={[
            ["Landing visits", analytics.funnel.landing_visits],
            ["CTA clicks", analytics.funnel.cta_clicks],
            ["Install starts", analytics.funnel.install_starts],
            ["Install completes", analytics.funnel.install_completes],
            ["Paid conversions", analytics.funnel.paid_conversions],
          ]}
        />
      </Section>

      <Section title="Traffic by Source (30d)">
        <Table
          headers={["Source", "Visits", "Installs"]}
          rows={analytics.visits_by_source.map((r) => [
            r.source,
            r.visits,
            r.installs,
          ])}
        />
      </Section>

      <Section title="Traffic by Campaign (30d)">
        <Table
          headers={["Campaign", "Visits", "Installs"]}
          rows={analytics.visits_by_campaign.map((r) => [
            r.campaign,
            r.visits,
            r.installs,
          ])}
        />
      </Section>

      <Section title="Recent Merchants">
        <Table
          headers={[
            "Email",
            "Plan",
            "UTM Source",
            "Domain",
            "Last Score",
            "Created",
          ]}
          rows={merchants.map((m) => [
            m.email,
            m.plan,
            m.utm_source ?? "—",
            m.shopify_shop_domain ?? "—",
            m.last_scan_score ?? "—",
            formatDate(m.created_at),
          ])}
        />
      </Section>

      <Section title="Recent Scans">
        <Table
          headers={["Domain", "Score", "Status", "Duration (s)", "Created"]}
          rows={scans.map((s) => [
            s.shopify_shop_domain ?? s.store_id,
            s.score ?? "—",
            s.status,
            s.duration_seconds ?? "—",
            formatDate(s.created_at),
          ])}
        />
      </Section>

      <Section title="Errors (webhook events)">
        <Table
          headers={["Topic", "Source", "Shop", "Error", "Created"]}
          rows={errors.map((e) => [
            e.topic,
            e.source,
            e.shop_domain ?? "—",
            (e.processing_error ?? "").slice(0, 120),
            formatDate(e.created_at),
          ])}
        />
      </Section>
    </div>
  );
}
