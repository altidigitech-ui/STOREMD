import { getSupabaseBrowserClient } from "@/lib/supabase";
import type {
  ApiErrorShape,
  CheckoutResponse,
  FeedbackCategory,
  FeedbackResponse,
  Fix,
  HealthResponse,
  NotificationsResponse,
  Paginated,
  Plan,
  PortalResponse,
  Scan,
  ScanDetailResponse,
  ScanModule,
  Store,
  StoreAppsResponse,
  UsageResponse,
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
    this.baseURL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "";
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
