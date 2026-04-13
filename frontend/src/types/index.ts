// Aligned with docs/API.md responses.

// ────────────────── Auth / Plan ──────────────────
export type Plan = "free" | "starter" | "pro" | "agency";

// ────────────────── Store ──────────────────
export interface Store {
  id: string;
  shopify_shop_domain: string;
  name: string | null;
  primary_domain: string | null;
  theme_name: string | null;
  products_count: number;
  apps_count: number;
  currency: string | null;
  country: string | null;
  shopify_plan: string | null;
  status: "active" | "inactive" | "suspended";
  created_at: string;
}

export interface StoreApp {
  id: string;
  name: string;
  handle: string;
  status: "active" | "inactive";
  impact_ms: number;
  scripts_count: number;
  scripts_size_kb: number;
  css_size_kb: number;
  billing_amount: number | null;
  scopes: string[];
  developer: string | null;
  first_detected_at: string;
}

export interface StoreAppsResponse {
  data: StoreApp[];
  total_apps: number;
  total_impact_ms: number;
  apps_count_known: boolean;
  apps_count_from_scan: number;
}

// ────────────────── Scans ──────────────────
export type ScanStatus = "pending" | "running" | "completed" | "failed";
export type ScanTrigger = "manual" | "cron" | "webhook" | "onboarding";
export type ScanModule =
  | "health"
  | "listings"
  | "agentic"
  | "compliance"
  | "browser";

export interface Scan {
  id: string;
  status: ScanStatus;
  trigger: ScanTrigger;
  modules: ScanModule[];
  score: number | null;
  mobile_score: number | null;
  desktop_score: number | null;
  issues_count: number;
  critical_count: number;
  partial_scan: boolean;
  duration_ms: number | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export type IssueSeverity = "critical" | "major" | "minor" | "info";

export interface ScanIssue {
  id: string;
  module: string;
  scanner: string;
  severity: IssueSeverity;
  title: string;
  description: string | null;
  impact: string | null;
  impact_value: number | null;
  impact_unit: string | null;
  fix_type: string | null;
  fix_description: string | null;
  auto_fixable: boolean;
  fix_applied: boolean;
  dismissed: boolean;
}

export interface ScanDetailResponse {
  id: string;
  status: ScanStatus;
  score: number | null;
  mobile_score: number | null;
  desktop_score: number | null;
  modules: ScanModule[];
  trigger: ScanTrigger;
  partial_scan: boolean;
  duration_ms: number | null;
  progress: number;
  current_step: string | null;
  issues: ScanIssue[];
  errors: string[];
  started_at: string | null;
  completed_at: string | null;
}

export interface HealthHistoryPoint {
  date: string;
  score: number;
}

export interface HealthResponse {
  score: number;
  mobile_score: number;
  desktop_score: number;
  trend: "up" | "down" | "stable";
  trend_delta: number;
  last_scan_at: string | null;
  issues_count: number;
  critical_count: number;
  previous_score: number | null;
  history: HealthHistoryPoint[];
}

// ────────────────── Pagination ──────────────────
export interface Pagination {
  has_next: boolean;
  next_cursor: string | null;
  total_count?: number;
}

export interface Paginated<T> {
  data: T[];
  pagination: Pagination;
}

// ────────────────── Notifications ──────────────────
export interface Notification {
  id: string;
  channel: "push" | "email" | "in_app";
  title: string;
  body: string;
  action_url: string | null;
  category: string;
  read: boolean;
  sent_at: string;
}

export interface NotificationsResponse {
  data: Notification[];
  unread_count: number;
  pagination: Pagination;
}

// ────────────────── Fixes ──────────────────
export type FixStatus =
  | "pending_approval"
  | "applied"
  | "reverted"
  | "failed";

export interface Fix {
  fix_id: string;
  status: FixStatus;
  fix_type: string;
  before_state: Record<string, unknown>;
  after_state: Record<string, unknown>;
  revertable: boolean;
  applied_at: string | null;
  reverted_at?: string | null;
}

// ────────────────── Billing / Usage ──────────────────
export type UsageType =
  | "scan"
  | "listing_analysis"
  | "one_click_fix"
  | "browser_test"
  | "bulk_operation";

export interface UsageRecord {
  type: UsageType;
  count: number;
  limit: number;
  remaining: number;
}

export interface UsageResponse {
  plan: Plan;
  period_start: string;
  period_end: string;
  usage: UsageRecord[];
}

export interface CheckoutResponse {
  checkout_url: string;
}

export interface PortalResponse {
  portal_url: string;
}

// ────────────────── Feedback ──────────────────
export type FeedbackCategory =
  | "not_relevant"
  | "too_risky"
  | "will_do_later"
  | "disagree"
  | "already_fixed"
  | "other";

export interface FeedbackResponse {
  id: string;
  accepted: boolean;
  reason_category: FeedbackCategory | null;
  created_at: string;
}

// ────────────────── Errors ──────────────────
export interface ApiErrorShape {
  code: string;
  message: string;
}

// ────────────────── Listings ──────────────────
export interface ProductListing {
  shopify_product_id: string;
  title: string | null;
  handle: string | null;
  score: number | null;
  title_score: number | null;
  description_score: number | null;
  images_score: number | null;
  seo_score: number | null;
  revenue_30d: number | null;
  orders_30d: number | null;
  priority_rank: number | null;
  issues: Array<{
    element: string;
    score: number;
    suggestion: string;
  }>;
}

export interface ListingsScanResponse {
  products_scanned: number;
  avg_score: number;
  data: ProductListing[];
  pagination: Pagination;
}

export interface ListingPriority {
  shopify_product_id: string;
  title: string | null;
  score: number | null;
  revenue_30d: number | null;
  potential_uplift_pct: number | null;
  priority_rank: number | null;
  top_issue: string | null;
}

export interface ListingsPrioritiesResponse {
  data: ListingPriority[];
}

// ────────────────── Agentic ──────────────────
export type AgenticCheckStatus = "pass" | "partial" | "fail";

export interface AgenticCheck {
  name: string;
  status: AgenticCheckStatus;
  affected_products: number;
  pass_rate: number;
  fix_description: string;
}

export interface AgenticScoreResponse {
  score: number;
  products_scanned: number;
  checks: AgenticCheck[];
}

// ────────────────── Compliance ──────────────────
export interface AccessibilityViolation {
  rule: string;
  severity: IssueSeverity;
  count: number;
  fix_description: string | null;
  auto_fixable: boolean;
}

export interface AccessibilityResponse {
  score: number;
  eaa_compliant: boolean;
  violations_count: number;
  violations: AccessibilityViolation[];
  live_test_included: boolean;
  live_test_available: boolean;
}

export interface BrokenLink {
  url: string;
  source_page: string | null;
  status_code: number | null;
  type: "internal" | "external";
  auto_fixable: boolean;
  fix_description: string | null;
}

export interface BrokenLinksResponse {
  broken_count: number;
  pages_crawled: number;
  data: BrokenLink[];
}

// ────────────────── Browser (Pro) ──────────────────
export interface VisualDeviceDiff {
  current_url: string | null;
  previous_url: string | null;
  diff_pct: number | null;
  significant_change: boolean;
}

export interface VisualDiffRegion {
  area: string;
  change_pct: number;
}

export interface VisualDiffResponse {
  screenshots: {
    mobile?: VisualDeviceDiff;
    desktop?: VisualDeviceDiff;
  };
  diff_regions: VisualDiffRegion[];
  scan_id: string | null;
  scanned_at: string | null;
}

export interface SimulationStep {
  name: string;
  url: string | null;
  time_ms: number;
  bottleneck: boolean;
  cause: string | null;
}

export interface SimulationResponse {
  total_time_ms: number;
  bottleneck_step: string | null;
  bottleneck_cause: string | null;
  steps: SimulationStep[];
  scan_id: string | null;
  scanned_at: string | null;
}

// ────────────────── Reports ──────────────────
export interface WeeklyReportResponse {
  period: string;
  score: number;
  score_delta: number;
  trend: "up" | "down" | "stable";
  issues_resolved: number;
  new_issues: number;
  top_action: string;
  report_pdf_url: string | null;
  generated_at: string;
}
