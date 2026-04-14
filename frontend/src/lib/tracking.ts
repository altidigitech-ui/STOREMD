"use client";

/**
 * Built-in tracking client for the StoreMD landing page.
 *
 * - session_id: random UUID per browser session (sessionStorage)
 * - UTM params: captured from the URL on first visit, persisted in
 *   localStorage so they survive navigation and the redirect to Shopify
 * - pageview: POSTed fire-and-forget on every navigation
 * - trackEvent: free-form event helper for CTA clicks etc.
 *
 * No external SDKs. No GA4. Everything goes to /api/v1/tracking/*.
 */

const SESSION_KEY = "storemd_session_id";
const UTM_KEY = "storemd_utm";

const UTM_FIELDS = [
  "utm_source",
  "utm_medium",
  "utm_campaign",
  "utm_content",
  "utm_term",
] as const;

export type UtmField = (typeof UTM_FIELDS)[number];
export type UtmPayload = Partial<Record<UtmField, string>>;

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

export function getSessionId(): string {
  if (!isBrowser()) return "";
  let id = window.sessionStorage.getItem(SESSION_KEY);
  if (!id) {
    id =
      typeof window.crypto?.randomUUID === "function"
        ? window.crypto.randomUUID()
        : `s_${Date.now().toString(36)}_${Math.random().toString(36).slice(2)}`;
    window.sessionStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

export function getUtm(): UtmPayload {
  if (!isBrowser()) return {};
  try {
    const raw = window.localStorage.getItem(UTM_KEY);
    return raw ? (JSON.parse(raw) as UtmPayload) : {};
  } catch {
    return {};
  }
}

function persistUtm(utm: UtmPayload): void {
  if (!isBrowser()) return;
  try {
    window.localStorage.setItem(UTM_KEY, JSON.stringify(utm));
  } catch {
    // localStorage may be disabled — silently ignore.
  }
}

export function captureUtmFromUrl(): UtmPayload {
  if (!isBrowser()) return {};
  const params = new URLSearchParams(window.location.search);
  const fresh: UtmPayload = {};
  for (const field of UTM_FIELDS) {
    const v = params.get(field);
    if (v) fresh[field] = v;
  }
  if (Object.keys(fresh).length > 0) {
    persistUtm(fresh);
    return fresh;
  }
  return getUtm();
}

interface UaInfo {
  device: string;
  browser: string;
  os: string;
}

function parseUserAgent(ua: string): UaInfo {
  const lower = ua.toLowerCase();
  let device = "desktop";
  if (/ipad|tablet/.test(lower)) device = "tablet";
  else if (/mobi|android|iphone|ipod/.test(lower)) device = "mobile";

  let browser = "other";
  if (/edg\//.test(lower)) browser = "edge";
  else if (/chrome\//.test(lower) && !/edg\//.test(lower)) browser = "chrome";
  else if (/safari\//.test(lower) && !/chrome\//.test(lower)) browser = "safari";
  else if (/firefox\//.test(lower)) browser = "firefox";

  let os = "other";
  if (/windows/.test(lower)) os = "windows";
  else if (/mac os x/.test(lower)) os = "macos";
  else if (/android/.test(lower)) os = "android";
  else if (/iphone|ipad|ios/.test(lower)) os = "ios";
  else if (/linux/.test(lower)) os = "linux";

  return { device, browser, os };
}

function send(path: string, body: Record<string, unknown>): void {
  if (!isBrowser()) return;
  const url = `/api/v1/tracking/${path}`;
  // Best-effort — never await, never throw, never log errors visibly.
  try {
    void fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      keepalive: true,
    }).catch(() => {});
  } catch {
    // ignore
  }
}

export function trackPageview(path?: string): void {
  if (!isBrowser()) return;
  const utm = getUtm();
  const ua = parseUserAgent(window.navigator.userAgent || "");
  send("pageview", {
    session_id: getSessionId(),
    path: path ?? window.location.pathname + window.location.search,
    referrer: document.referrer || null,
    ...utm,
    ...ua,
    screen_width: window.screen?.width ?? null,
  });
}

export function trackEvent(
  name: string,
  data: Record<string, unknown> = {},
): void {
  if (!isBrowser()) return;
  const utm = getUtm();
  send("event", {
    session_id: getSessionId(),
    event_name: name,
    event_data: data,
    utm_source: utm.utm_source ?? null,
    utm_medium: utm.utm_medium ?? null,
    utm_campaign: utm.utm_campaign ?? null,
  });
}

/**
 * Append session_id + persisted UTM as query params to a URL.
 * Used to enrich the install link so the OAuth callback can attribute
 * the install to its source.
 */
export function withTrackingParams(href: string): string {
  if (!isBrowser()) return href;
  try {
    const url = new URL(href, window.location.origin);
    const utm = getUtm();
    for (const field of UTM_FIELDS) {
      const v = utm[field];
      if (v && !url.searchParams.has(field)) {
        url.searchParams.set(field, v);
      }
    }
    if (!url.searchParams.has("session_id")) {
      url.searchParams.set("session_id", getSessionId());
    }
    return url.toString();
  } catch {
    return href;
  }
}

export function initTracking(): void {
  if (!isBrowser()) return;
  getSessionId();
  captureUtmFromUrl();
  trackPageview();
}
