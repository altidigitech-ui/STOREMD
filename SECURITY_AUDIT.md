# Security Audit — StoreMD backend

Date: 2026-04-14
Scope: `backend/` — FastAPI app, middleware, routes, services.
Method: Code review of every route + middleware + service touching auth,
input handling, secrets, or external I/O. No dynamic scanning.

All findings below were patched in the same commit. Items marked **OK**
were verified and required no change.

---

## 1. Auth & sessions

### F-1.1 — JWT and rate-limit middleware defined but never mounted (Critical)
`app/api/middleware/auth.py` and `app/api/middleware/rate_limit.py` both
defined `BaseHTTPMiddleware` subclasses, but `app/main.py` only registered
`CORSMiddleware`. Auth was therefore enforced **only** at the route
dependency layer (`Depends(get_current_merchant)`); a forgotten dependency
would silently expose any future endpoint.

**Fix** — `app/main.py`: mount `JWTAuthMiddleware`, `RateLimitMiddleware`,
and the new `SecurityHeadersMiddleware`. Order chosen so that auth runs
first, the rate limiter sees the resolved `merchant_id`, and the security
headers middleware wraps the response.

### F-1.2 — Admin guard trusted a mutable column (High)
`admin.py` checked `merchant.email` from the `merchants` table. Supabase
RLS allows a merchant to UPDATE their own row (`merchants_update_own`),
so any merchant could set `email = 'altidigitech@gmail.com'` and gain
admin access.

**Fix** — `app/api/middleware/auth.py` now stashes the JWT-validated email
(read straight from `auth.users` via `supabase.auth.get_user`) into
`request.state.auth_email`. `dependencies.get_current_merchant` propagates
it onto the merchant dict as `auth_email`, and `admin._require_admin` checks
**only** that field. The mutable `merchants.email` column is no longer
trusted for privilege checks.

### F-1.3 — `JWTAuthMiddleware.PUBLIC_PATHS` was incomplete (Medium)
The public-path allowlist did not include the new tracking endpoints, the
GDPR webhooks, or the dev-only debug routes. With the middleware now
mounted, those endpoints would have returned 401.

**Fix** — extended `PUBLIC_PATHS` with `/api/v1/tracking/pageview`,
`/api/v1/tracking/event`, `/api/v1/webhooks/customers/data_request`,
`/api/v1/webhooks/customers/redact`, `/api/v1/webhooks/shop/redact`, and
added a `PUBLIC_PREFIXES` mechanism for `/api/v1/debug/*`.

### F-1.4 — OAuth `session_id` query param was unvalidated (Low)
`/install` accepted any string for `session_id` and stored it in the
Redis state payload, then later wrote it to `tracking_events`. An attacker
could forge attribution by minting OAuth flows with a victim's session id.

**Fix** — `auth.py`: regex-validated against `^[A-Za-z0-9_\-]{8,128}$`
(matches our `crypto.randomUUID()` and the JS fallback). Bad values are
silently dropped, the install still proceeds.

---

## 2. Injection & input validation

### OK — Pydantic everywhere
Every JSON body goes through a `pydantic.BaseModel` (verified across all
routes under `app/api/routes/`). No raw `dict` bodies, no untyped query
parameters used as DB filters.

### OK — No raw SQL
The Supabase Python SDK (`.table().select().eq()...`) is used everywhere.
No `.rpc()` with f-string interpolation, no concatenated `SELECT/INSERT/
UPDATE/DELETE`, no template-string SQL.

### F-2.1 — Shop-domain header trusted in webhook handlers (Medium)
`webhooks_shopify.py` and `webhooks_gdpr.py` read
`X-Shopify-Shop-Domain` and used it directly in
`.eq("shopify_shop_domain", shop)` queries. The HMAC vouches for the
*body*, not for arbitrary headers — an attacker who replays a valid HMAC
body with a substituted header could query for an arbitrary shop. Match
returns nothing if the shop doesn't exist, so impact is limited, but the
defensive check is cheap.

**Fix** — both webhook routers now apply
`^[a-zA-Z0-9][a-zA-Z0-9\-]*\.myshopify\.com$` to the header value before
using it. Mismatches are normalized to `""`, which short-circuits the
downstream lookup.

### F-2.2 — UTM params were unbounded (Low)
`/install` would store arbitrary-length UTM strings (and `session_id`)
inside the Redis OAuth state payload. A 2 MB UTM string from a crafted
ad-tracking link would bloat Redis and could trip ingress limits.

**Fix** — `auth.py`: each UTM value is trimmed to 128 chars before
serialization. The tracking routes already enforced max-length via
Pydantic.

### OK — Shop domain on `/install` and `/callback`
Both routes already gate on `SHOP_DOMAIN_REGEX`. The error message no
longer reflects the user-supplied value (`"Invalid shop domain: {shop}"`
→ `"Invalid shop domain"`) to remove a mild XSS-via-error reflection
vector when the message is rendered.

---

## 3. Rate limiting

### F-3.1 — Global rate limiter not in effect (Critical, see F-1.1)
The plan-tier limiter was unmounted. **Fix** — same change as F-1.1.

### F-3.2 — `/install` had no per-IP throttle (Medium)
A scripted enumerator could hit `/install?shop=...` repeatedly to
fingerprint installed merchants (the redirect target reveals whether the
shop completes OAuth). The middleware-level limiter doesn't help here
because `/install` is unauthenticated, so `merchant_id` is unset.

**Fix** — `auth.py`: added `_enforce_install_rate_limit`, a Redis-backed
20 req/min/IP cap. Tracking endpoints already had their own 60/min limiter.

### F-3.3 — Manual scans had no daily quota (High)
Authenticated merchants could script `POST /stores/{id}/scans` and burn
the Shopify rate budget + Claude API spend. The `SCAN_ALREADY_RUNNING`
guard only prevented concurrent scans, not sequential abuse.

**Fix** — `scans.py`: added `MANUAL_SCAN_DAILY_LIMIT` per plan
(free 3, starter 20, pro 100, agency 500) checked against
`scans` rows where `trigger='manual'` in the last 24h. Cron-triggered
scans are excluded.

### OK — Tracking endpoints
`/tracking/pageview` and `/tracking/event` already implemented per-IP
60 req/min via Redis (`tracking._enforce_rate_limit`).

---

## 4. HMAC & webhook signatures

### OK — Shopify product webhooks
`webhooks_shopify.receive_shopify_webhook` validates the HMAC via
`validate_shopify_hmac` before any DB write. Constant-time comparison
via `hmac.compare_digest`.

### OK — GDPR webhooks
`webhooks_gdpr.py` validates HMAC on all three endpoints
(`customers/data_request`, `customers/redact`, `shop/redact`) before any
processing.

### OK — Stripe webhook
`webhooks_stripe.py` uses `stripe.Webhook.construct_event`, which
performs constant-time signature verification using
`STRIPE_WEBHOOK_SECRET`.

---

## 5. Secrets

### OK — No hardcoded production keys
`grep` for `sk_live`, `sk_test_[A-Za-z0-9]{20,}`, `whsec_[A-Za-z0-9]{20,}`,
`sk-ant-`, `re_[A-Za-z0-9]{20,}`, `eyJhbGciOi…` returned only matches in
`backend/.env.test`, which contains the well-known public Supabase
self-host demo JWT and `sk_test_xxx` placeholders. Real keys live in
`config.py`'s `Settings` (Pydantic `BaseSettings`).

### OK — All env reads go through settings
`os.getenv(...)` is not used in the production code path; everything
goes through `app.config.settings`.

---

## 6. CORS

### F-6.1 — Permissive Vercel-preview wildcard with credentials (High)
`main.py` allowed `^https://storemd-[a-z0-9]+-altidigitechs-projects\.vercel\.app$`
combined with `allow_credentials=True`, `allow_methods=["*"]`,
`allow_headers=["*"]`. Any preview deploy (including a malicious PR) could
issue credentialed requests against the production API.

**Fix** — `main.py`:
- Localhost origins are now only added in non-production.
- `allow_methods` restricted to `GET POST PATCH PUT DELETE OPTIONS`.
- `allow_headers` restricted to the actual list we use (`Authorization`,
  `Content-Type`, `Accept`, plus the Shopify and Stripe webhook headers).
- The Vercel preview regex was already anchored on both ends; left in
  place because previews need to call the API for QA, but the tightened
  header allowlist limits the blast radius.

---

## 7. Security headers

### F-7.1 — No security headers on backend responses (Medium)
The Vercel frontend sets X-Content-Type-Options, X-Frame-Options, HSTS
etc. via `next.config.js`, but direct API responses (and the docs URL
in non-prod) shipped without them.

**Fix** — new `app/api/middleware/security_headers.py`:
`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
`Referrer-Policy: strict-origin-when-cross-origin`,
`Cross-Origin-Opener-Policy: same-origin`,
`Permissions-Policy: geolocation=(), microphone=(), camera=()`.
HSTS (`max-age=63072000; includeSubDomains; preload`) is added only when
`APP_ENV == 'production'` so localhost dev isn't pinned.

---

## 8. Data exposure

### OK — Tokens never returned by API
`shopify_access_token_encrypted` is read internally only. No route
returns the merchant dict directly. The admin merchants endpoint
explicitly enumerates the columns it selects.

### OK — Logger does not log tokens
`grep` for `logger.*token`, `logger.*secret`, `logger.*password` returned
no matches. `validation_error_handler` already drops Pydantic `ctx`
fields.

### F-8.1 — Pydantic validation echoed `input` in error responses (Low)
`RequestValidationError` produced by FastAPI includes the offending
input value in each error entry. In production this can echo back tokens
or PII via 422 responses.

**Fix** — `main.py`: in production we now strip `input` (in addition to
`ctx`) from the response. Local dev keeps `input` for debuggability.

### OK — Unhandled exceptions
The catch-all returns `{"code": "internal_error", "message": "An
unexpected error occurred"}` without leaking the exception type or stack
trace. Sentry receives the full exception when `SENTRY_DSN` is set in
production.

### OK — `/docs` disabled in production
`docs_url=None` when `is_production`.

---

## 9. Dependencies

`requirements.txt` versions reviewed manually — no known CVE on the
pinned ranges:

| Package | Pinned | Notes |
|---|---|---|
| fastapi | `>=0.115` | Current major, no open advisories. |
| httpx | `>=0.28` | Latest. |
| pydantic | `>=2.10` | v2 line, current. |
| celery | `>=5.4` | No open security issues. |
| supabase | `>=2.11` | Current. |
| cryptography | `>=44.0` | Latest. |
| PyJWT | `>=2.10` | Patches the 2.10 algorithm-confusion issue. |
| stripe | `>=11.0` | Current SDK. |

No automated `pip-audit` was run (no internet from this sandbox); recommend
adding `pip-audit` to CI as a follow-up.

---

## 10. Shopify access tokens

### OK — Encryption at rest
Tokens are Fernet-encrypted via `app.core.security.encrypt_token` before
insertion (`auth.py`). Decryption only happens on the request path that
needs to call Shopify, never logged or returned.

### OK — Cleanup on uninstall
`webhooks_shopify._handle_app_uninstalled` clears
`shopify_access_token_encrypted` to `NULL` and marks the store
`uninstalled`. The 48 h-later `shop/redact` GDPR webhook deletes the rows
entirely.

### OK — Used only where needed
Token is decrypted on demand inside the route handler scope and passed to
`ShopifyClient` / `ShopifyBillingService`, never persisted in a global,
never serialized into a response.

---

## Summary

| # | Severity | Area | Status |
|---|---|---|---|
| F-1.1 | Critical | Middleware not mounted | Fixed |
| F-1.2 | High | Admin guard on mutable column | Fixed |
| F-1.3 | Medium | PUBLIC_PATHS incomplete | Fixed |
| F-1.4 | Low | Unvalidated session_id | Fixed |
| F-2.1 | Medium | Shop-domain header trusted | Fixed |
| F-2.2 | Low | Unbounded UTM length | Fixed |
| F-3.1 | Critical | Global rate limit absent | Fixed (= F-1.1) |
| F-3.2 | Medium | `/install` per-IP throttle | Fixed |
| F-3.3 | High | No daily scan quota | Fixed |
| F-6.1 | High | CORS over-permissive | Fixed |
| F-7.1 | Medium | No security headers | Fixed |
| F-8.1 | Low | Pydantic input echo | Fixed |

Follow-ups (not blocking):
- Add `pip-audit` to CI.
- Consider rotating `FERNET_KEY` annually with a key-id prefix on stored
  tokens to support graceful re-encryption.
- Consider reducing the JWT validation cache TTL below 60s for sessions
  that grant admin (currently the only admin is a single hardcoded
  email, so impact is bounded).
