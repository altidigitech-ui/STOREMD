-- ============================================================
-- StoreMD — 004_shopify_billing.sql
-- Add Shopify Billing API support (parallel to Stripe).
-- ============================================================

ALTER TABLE merchants ADD COLUMN IF NOT EXISTS billing_provider text DEFAULT null;
ALTER TABLE merchants ADD COLUMN IF NOT EXISTS shopify_subscription_id text DEFAULT null;

ALTER TABLE merchants DROP CONSTRAINT IF EXISTS merchants_billing_provider_check;
ALTER TABLE merchants ADD CONSTRAINT merchants_billing_provider_check
    CHECK (billing_provider IS NULL OR billing_provider IN ('shopify', 'stripe'));

NOTIFY pgrst, 'reload schema';
