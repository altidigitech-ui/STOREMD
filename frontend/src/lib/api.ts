import { getSupabaseBrowserClient } from "@/lib/supabase";
import type {
  AccessibilityResponse,
  AgenticScoreResponse,
  ApiErrorShape,
  BrokenLinksResponse,
  CheckoutResponse,
  FeedbackCategory,
  FeedbackResponse,
  Fix,
  HealthResponse,
  ListingsPrioritiesResponse,
  ListingsScanResponse,
  NotificationsResponse,
  Paginated,
  Plan,
  PortalResponse,
  Scan,
  ScanDetailResponse,
  ScanModule,
  ShopifyBillingStatusResponse,
  ShopifySubscribeResponse,
  SimulationResponse,
  Store,
  StoreAppsResponse,
  UsageResponse,
  VisualDiffResponse,
  WeeklyReportResponse,
} from "@/types";

/**
 * Error thrown by the API client. Carries the backend ErrorCode so
 * UI layers can branch on it (e.g. SCAN_LIMIT_REACHED → upgrade modal).
 */
export class ApiError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(code: string, message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

interface FetchOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined | null>;
}

class ApiClient {
  private readonly baseURL: string;

  constructor() {
    this.baseURL = "";
  }

  private buildUrl(
    path: string,
    query?: FetchOptions["query"],
  ): string {
    const base = this.baseURL ? `${this.baseURL}${path}` : path;
    if (!query) return base;

    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) {
      if (value === undefined || value === null) continue;
      params.append(key, String(value));
    }
    const qs = params.toString();
    return qs ? `${base}?${qs}` : base;
  }

  private async getAuthHeader(): Promise<Record<string, string>> {
    if (typeof window === "undefined") return {};
    try {
      const supabase = getSupabaseBrowserClient();
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      return token ? { Authorization: `Bearer ${token}` } : {};
    } catch {
      return {};
    }
  }

  private async fetchWithAuth<T>(
    path: string,
    options: FetchOptions = {},
  ): Promise<T> {
    const { body, query, headers, ...init } = options;
    const url = this.buildUrl(path, query);
    const authHeader = await this.getAuthHeader();

    const response = await fetch(url, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...authHeader,
        ...(headers as Record<string, string>),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });

    if (response.status === 204) {
      return undefined as T;
    }

    const raw = await response.text();
    let parsed: unknown = null;
    if (raw) {
      try {
        parsed = JSON.parse(raw);
      } catch {
        parsed = raw;
      }
    }

    if (!response.ok) {
      const err = extractError(parsed, response.status);
      throw new ApiError(err.code, err.message, response.status);
    }

    return parsed as T;
  }

  // ────────────── Stores ──────────────
  stores = {
    get: (storeId: string): Promise<Store> =>
      this.fetchWithAuth(`/api/v1/stores/${storeId}`),
    getApps: (storeId: string): Promise<StoreAppsResponse> =>
      this.fetchWithAuth(`/api/v1/stores/${storeId}/apps`),
  };

  // ────────────── Scans ──────────────
  scans = {
    create: (storeId: string, modules: ScanModule[]): Promise<Scan> =>
      this.fetchWithAuth(`/api/v1/stores/${storeId}/scans`, {
        method: "POST",
        body: { modules },
      }),
    list: (
      storeId: string,
      cursor?: string,
      limit: number = 20,
    ): Promise<Paginated<Scan>> =>
      this.fetchWithAuth(`/api/v1/stores/${storeId}/scans`, {
        query: { cursor, limit },
      }),
    get: (storeId: string, scanId: string): Promise<ScanDetailResponse> =>
      this.fetchWithAuth(`/api/v1/stores/${storeId}/scans/${scanId}`),
    getHealth: (storeId: string): Promise<HealthResponse> =>
      this.fetchWithAuth(`/api/v1/stores/${storeId}/health`),
  };

  // ────────────── Billing ──────────────
  billing = {
    createCheckout: (plan: Plan): Promise<CheckoutResponse> =>
      this.fetchWithAuth(`/api/v1/billing/checkout`, {
        method: "POST",
        body: { plan },
      }),
    getPortal: (): Promise<PortalResponse> =>
      this.fetchWithAuth(`/api/v1/billing/portal`),
    getUsage: (): Promise<UsageResponse> =>
      this.fetchWithAuth(`/api/v1/billing/usage`),
  };

  // ────────────── Shopify Billing ──────────────
  shopifyBilling = {
    subscribe: (plan: Plan): Promise<ShopifySubscribeResponse> =>
      this.fetchWithAuth(`/api/v1/shopify-billing/subscribe`, {
        method: "POST",
        body: { plan },
      }),
    status: (): Promise<ShopifyBillingStatusResponse> =>
      this.fetchWithAuth(`/api/v1/shopify-billing/status`),
    cancel: (): Promise<{ status: string }> =>
      this.fetchWithAuth(`/api/v1/shopify-billing/cancel`, {
        method: "DELETE",
      }),
  };

  // ────────────── Notifications ──────────────
  notifications = {
    list: (
      cursor?: string,
      unreadOnly: boolean = false,
    ): Promise<NotificationsResponse> =>
      this.fetchWithAuth(`/api/v1/notifications`, {
        query: { cursor, unread_only: unreadOnly },
      }),
    markRead: (id: string): Promise<void> =>
      this.fetchWithAuth(`/api/v1/notifications/${id}/read`, {
        method: "PATCH",
      }),
  };

  // ────────────── Feedback ──────────────
  feedback = {
    create: (
      issueId: string,
      accepted: boolean,
      reason?: string,
      reasonCategory?: FeedbackCategory,
    ): Promise<FeedbackResponse> =>
      this.fetchWithAuth(`/api/v1/feedback`, {
        method: "POST",
        body: {
          issue_id: issueId,
          accepted,
          reason,
          reason_category: reasonCategory,
        },
      }),
  };

  // ────────────── Fixes ──────────────
  fixes = {
    apply: (storeId: string, fixId: string): Promise<Fix> =>
      this.fetchWithAuth(
        `/api/v1/stores/${storeId}/fixes/${fixId}/apply`,
        { method: "POST" },
      ),
    revert: (storeId: string, fixId: string): Promise<Fix> =>
      this.fetchWithAuth(
        `/api/v1/stores/${storeId}/fixes/${fixId}/revert`,
        { method: "POST" },
      ),
  };

  // ────────────── Listings ──────────────
  listings = {
    scan: (
      storeId: string,
      options: {
        cursor?: string;
        limit?: number;
        sort?: string;
      } = {},
    ): Promise<ListingsScanResponse> =>
      this.fetchWithAuth(`/api/v1/stores/${storeId}/listings/scan`, {
        query: {
          cursor: options.cursor,
          limit: options.limit,
          sort: options.sort,
        },
      }),
    priorities: (storeId: string): Promise<ListingsPrioritiesResponse> =>
      this.fetchWithAuth(`/api/v1/stores/${storeId}/listings/priorities`),
  };

  // ────────────── Agentic ──────────────
  agentic = {
    score: (storeId: string): Promise<AgenticScoreResponse> =>
      this.fetchWithAuth(`/api/v1/stores/${storeId}/agentic/score`),
  };

  // ────────────── Compliance ──────────────
  compliance = {
    accessibility: (
      storeId: string,
      live: boolean = false,
    ): Promise<AccessibilityResponse> =>
      this.fetchWithAuth(`/api/v1/stores/${storeId}/accessibility`, {
        query: { live },
      }),
    brokenLinks: (storeId: string): Promise<BrokenLinksResponse> =>
      this.fetchWithAuth(`/api/v1/stores/${storeId}/links/broken`),
  };

  // ────────────── Browser (Pro+) ──────────────
  browser = {
    visualDiff: (storeId: string): Promise<VisualDiffResponse> =>
      this.fetchWithAuth(`/api/v1/stores/${storeId}/visual/diff`),
    simulation: (storeId: string): Promise<SimulationResponse> =>
      this.fetchWithAuth(`/api/v1/stores/${storeId}/simulation`),
  };

  // ────────────── Reports ──────────────
  reports = {
    latest: (storeId: string): Promise<WeeklyReportResponse> =>
      this.fetchWithAuth(`/api/v1/stores/${storeId}/reports/latest`),
  };

  // ────────────── Admin (altidigitech@gmail.com only) ──────────────
  admin = {
    overview: (): Promise<AdminOverview> =>
      this.fetchWithAuth(`/api/v1/admin/overview`),
    merchants: (): Promise<{ merchants: AdminMerchant[] }> =>
      this.fetchWithAuth(`/api/v1/admin/merchants`),
    scans: (limit: number = 50): Promise<{ scans: AdminScan[] }> =>
      this.fetchWithAuth(`/api/v1/admin/scans`, { query: { limit } }),
    errors: (limit: number = 50): Promise<{ errors: AdminError[] }> =>
      this.fetchWithAuth(`/api/v1/admin/errors`, { query: { limit } }),
    analytics: (): Promise<AdminAnalytics> =>
      this.fetchWithAuth(`/api/v1/admin/analytics`),
  };
}

export interface AdminOverview {
  total_merchants: number;
  total_stores: number;
  total_scans: number;
  scans_today: number;
  scans_this_week: number;
  active_subscriptions: number;
  mrr: number;
  avg_health_score: number | null;
  visits_today: number;
  visits_this_week: number;
  visits_this_month: number;
  unique_visitors_today: number;
  installs_today: number;
  conversion_rate: number;
}

export interface AdminMerchant {
  id: string;
  email: string;
  plan: string;
  billing_provider: string | null;
  utm_source: string | null;
  utm_medium: string | null;
  utm_campaign: string | null;
  shopify_shop_domain: string | null;
  created_at: string;
  last_scan_score?: number | null;
}

export interface AdminScan {
  id: string;
  store_id: string;
  status: string;
  score: number | null;
  duration_ms: number | null;
  duration_seconds?: number | null;
  created_at: string;
  shopify_shop_domain?: string | null;
}

export interface AdminError {
  id: string;
  source: string;
  topic: string;
  shop_domain: string | null;
  processing_error: string | null;
  retry_count: number;
  created_at: string;
}

export interface AdminAnalytics {
  visits_by_day: { date: string; visits: number; unique_visitors: number }[];
  visits_by_source: { source: string; visits: number; installs: number }[];
  visits_by_campaign: { campaign: string; visits: number; installs: number }[];
  visits_by_device: { device: string; visits: number }[];
  top_pages: { path: string; visits: number }[];
  funnel: {
    landing_visits: number;
    cta_clicks: number;
    install_starts: number;
    install_completes: number;
    paid_conversions: number;
    installs_total: number;
  };
}

function extractError(parsed: unknown, status: number): ApiErrorShape {
  if (
    parsed &&
    typeof parsed === "object" &&
    "error" in parsed &&
    parsed.error &&
    typeof parsed.error === "object"
  ) {
    const err = parsed.error as Record<string, unknown>;
    const code = typeof err.code === "string" ? err.code : "UNKNOWN_ERROR";
    const message =
      typeof err.message === "string" ? err.message : "Unknown error";
    return { code, message };
  }
  return {
    code: status >= 500 ? "INTERNAL_ERROR" : "UNKNOWN_ERROR",
    message: `Request failed with status ${status}`,
  };
}

export const api = new ApiClient();
