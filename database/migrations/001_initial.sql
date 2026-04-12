-- ============================================================
-- StoreMD — 001_initial.sql
-- Source de verite : docs/DATABASE.md
-- NE PAS EXECUTER AUTOMATIQUEMENT — appliquer manuellement dans Supabase SQL Editor
-- ============================================================

-- ============================================================
-- EXTENSIONS
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";       -- Mem0 pgvector si self-hosted

-- ============================================================
-- FUNCTION — updated_at automatique
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- FUNCTION — Creer le profil merchant a l'inscription
-- ============================================================

CREATE OR REPLACE FUNCTION on_auth_user_created()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.merchants (id, email)
    VALUES (NEW.id, NEW.email);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, auth, pg_temp;

-- ============================================================
-- 1. MERCHANTS
-- ============================================================
-- Profil etendu de auth.users (Supabase Auth).
-- Cree automatiquement via trigger on_auth_user_created.

CREATE TABLE merchants (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    name TEXT,

    -- Shopify
    shopify_shop_domain TEXT UNIQUE,
    shopify_access_token_encrypted TEXT,
    shopify_scopes TEXT[],
    shopify_installed_at TIMESTAMPTZ,

    -- Billing
    plan TEXT NOT NULL DEFAULT 'free'
        CHECK (plan IN ('free', 'starter', 'pro', 'agency')),
    stripe_customer_id TEXT UNIQUE,
    stripe_subscription_id TEXT,

    -- Notifications
    notification_email TEXT,
    notification_push_enabled BOOLEAN DEFAULT false,
    notification_push_subscription JSONB,
    notification_max_per_week INTEGER DEFAULT 3,

    -- Preferences
    timezone TEXT DEFAULT 'UTC',
    onboarding_completed BOOLEAN DEFAULT false,
    onboarding_completed_at TIMESTAMPTZ,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_merchants_shop_domain ON merchants(shopify_shop_domain);
CREATE INDEX idx_merchants_plan ON merchants(plan);
CREATE INDEX idx_merchants_stripe_customer ON merchants(stripe_customer_id);

ALTER TABLE merchants ENABLE ROW LEVEL SECURITY;

CREATE POLICY "merchants_read_own" ON merchants
    FOR SELECT USING (id = auth.uid());
CREATE POLICY "merchants_update_own" ON merchants
    FOR UPDATE USING (id = auth.uid());

CREATE TRIGGER merchants_updated_at BEFORE UPDATE ON merchants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- 2. STORES
-- ============================================================
-- Un merchant peut avoir plusieurs stores (Agency plan).
-- Pour Free/Starter/Pro : 1/1/3 stores max, enforced cote application.

CREATE TABLE stores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,

    -- Shopify
    shopify_shop_domain TEXT NOT NULL,
    shopify_shop_id TEXT,
    name TEXT,
    primary_domain TEXT,

    -- Theme
    theme_name TEXT,
    theme_id TEXT,
    theme_role TEXT DEFAULT 'main',

    -- Store metrics (updated at each scan)
    products_count INTEGER DEFAULT 0,
    apps_count INTEGER DEFAULT 0,
    currency TEXT DEFAULT 'USD',
    country TEXT,
    shopify_plan TEXT,

    -- Status
    status TEXT DEFAULT 'active'
        CHECK (status IN ('active', 'paused', 'uninstalled')),
    uninstalled_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_stores_merchant ON stores(merchant_id);
CREATE INDEX idx_stores_domain ON stores(shopify_shop_domain);
CREATE INDEX idx_stores_status ON stores(status);

ALTER TABLE stores ENABLE ROW LEVEL SECURITY;

CREATE POLICY "merchants_own_stores" ON stores
    FOR ALL USING (merchant_id = auth.uid());

CREATE TRIGGER stores_updated_at BEFORE UPDATE ON stores
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- 3. SCANS
-- ============================================================
-- Chaque execution du scan pipeline cree un record ici.
-- Status flow : pending -> running -> completed | failed

CREATE TABLE scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,

    -- Status
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    trigger TEXT NOT NULL DEFAULT 'manual'
        CHECK (trigger IN ('manual', 'cron', 'webhook')),
    modules TEXT[] NOT NULL DEFAULT ARRAY['health'],

    -- Results (populated when status = completed)
    score INTEGER,
    mobile_score INTEGER,
    desktop_score INTEGER,
    issues_count INTEGER DEFAULT 0,
    critical_count INTEGER DEFAULT 0,

    -- Timing
    duration_ms INTEGER,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Error (if status = failed)
    error_message TEXT,
    error_code TEXT,

    -- Metadata
    partial_scan BOOLEAN DEFAULT false,
    scanner_results JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_scans_store ON scans(store_id);
CREATE INDEX idx_scans_merchant ON scans(merchant_id);
CREATE INDEX idx_scans_status ON scans(status);
CREATE INDEX idx_scans_created ON scans(created_at DESC);
CREATE INDEX idx_scans_store_created ON scans(store_id, created_at DESC);

ALTER TABLE scans ENABLE ROW LEVEL SECURITY;

CREATE POLICY "merchants_own_scans" ON scans
    FOR ALL USING (merchant_id = auth.uid());

CREATE TRIGGER scans_updated_at BEFORE UPDATE ON scans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- 4. SCAN ISSUES
-- ============================================================
-- Chaque probleme detecte par un scanner.

CREATE TABLE scan_issues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,

    -- Classification
    module TEXT NOT NULL
        CHECK (module IN ('health', 'listings', 'agentic', 'compliance', 'browser')),
    scanner TEXT NOT NULL,
    severity TEXT NOT NULL
        CHECK (severity IN ('critical', 'major', 'minor', 'info')),

    -- Content
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    impact TEXT,
    impact_value NUMERIC(10,2),
    impact_unit TEXT,

    -- Fix
    fix_type TEXT
        CHECK (fix_type IN ('one_click', 'manual', 'developer')),
    fix_description TEXT,
    auto_fixable BOOLEAN DEFAULT false,

    -- Status
    fix_applied BOOLEAN DEFAULT false,
    fix_applied_at TIMESTAMPTZ,
    dismissed BOOLEAN DEFAULT false,
    dismissed_at TIMESTAMPTZ,

    -- Context
    context JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_issues_scan ON scan_issues(scan_id);
CREATE INDEX idx_issues_store ON scan_issues(store_id);
CREATE INDEX idx_issues_merchant ON scan_issues(merchant_id);
CREATE INDEX idx_issues_severity ON scan_issues(severity);
CREATE INDEX idx_issues_module ON scan_issues(module);
CREATE INDEX idx_issues_scanner ON scan_issues(scanner);
CREATE INDEX idx_issues_fix_applied ON scan_issues(fix_applied) WHERE fix_applied = false;

ALTER TABLE scan_issues ENABLE ROW LEVEL SECURITY;

CREATE POLICY "merchants_own_issues" ON scan_issues
    FOR ALL USING (merchant_id = auth.uid());

-- ============================================================
-- 5. STORE APPS
-- ============================================================
-- Apps Shopify installees sur le store du merchant.

CREATE TABLE store_apps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,

    -- Shopify app info
    shopify_app_id TEXT,
    name TEXT NOT NULL,
    handle TEXT,
    version TEXT,
    developer TEXT,
    app_store_url TEXT,

    -- Permissions
    scopes TEXT[],

    -- Impact (mesure par app_impact scanner)
    impact_ms INTEGER,
    scripts_count INTEGER DEFAULT 0,
    scripts_size_kb NUMERIC(10,2) DEFAULT 0,
    css_size_kb NUMERIC(10,2) DEFAULT 0,

    -- Status
    status TEXT DEFAULT 'active'
        CHECK (status IN ('active', 'uninstalled', 'ghost_billing')),
    billing_amount NUMERIC(10,2),
    first_detected_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    uninstalled_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(store_id, shopify_app_id)
);

CREATE INDEX idx_store_apps_store ON store_apps(store_id);
CREATE INDEX idx_store_apps_status ON store_apps(status);
CREATE INDEX idx_store_apps_impact ON store_apps(impact_ms DESC NULLS LAST);

ALTER TABLE store_apps ENABLE ROW LEVEL SECURITY;

CREATE POLICY "merchants_own_apps" ON store_apps
    FOR ALL USING (merchant_id = auth.uid());

CREATE TRIGGER store_apps_updated_at BEFORE UPDATE ON store_apps
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- 6. PRODUCT ANALYSES
-- ============================================================
-- Resultats d'analyse par produit (module Listings + Agentic).

CREATE TABLE product_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID REFERENCES scans(id) ON DELETE CASCADE,
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,

    -- Shopify product
    shopify_product_id TEXT NOT NULL,
    title TEXT,
    handle TEXT,
    product_type TEXT,
    vendor TEXT,
    status TEXT,

    -- Listing score (module Listings)
    score INTEGER,
    title_score INTEGER,
    description_score INTEGER,
    images_score INTEGER,
    seo_score INTEGER,
    issues JSONB DEFAULT '[]',
    suggestions JSONB DEFAULT '[]',

    -- Revenue (pour priorisation)
    revenue_30d NUMERIC(12,2),
    orders_30d INTEGER,
    views_30d INTEGER,
    priority_rank INTEGER,

    -- Agentic readiness (module Agentic)
    agentic_ready BOOLEAN DEFAULT false,
    has_gtin BOOLEAN DEFAULT false,
    has_hs_code BOOLEAN DEFAULT false,
    hs_code TEXT,
    hs_code_status TEXT
        CHECK (hs_code_status IN ('valid', 'missing', 'suspicious')),
    hs_code_suggestion TEXT,
    metafields_filled_pct INTEGER DEFAULT 0,
    schema_markup_valid BOOLEAN DEFAULT false,
    google_category_assigned BOOLEAN DEFAULT false,
    description_structured BOOLEAN DEFAULT false,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_products_scan ON product_analyses(scan_id);
CREATE INDEX idx_products_store ON product_analyses(store_id);
CREATE INDEX idx_products_shopify_id ON product_analyses(shopify_product_id);
CREATE INDEX idx_products_score ON product_analyses(score);
CREATE INDEX idx_products_agentic ON product_analyses(agentic_ready) WHERE agentic_ready = false;
CREATE INDEX idx_products_priority ON product_analyses(priority_rank);

ALTER TABLE product_analyses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "merchants_own_products" ON product_analyses
    FOR ALL USING (merchant_id = auth.uid());

-- ============================================================
-- 7. SCREENSHOTS
-- ============================================================
-- Module Browser Automation — Visual Store Test.

CREATE TABLE screenshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID REFERENCES scans(id) ON DELETE CASCADE,
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,

    -- Screenshot info
    device TEXT NOT NULL CHECK (device IN ('mobile', 'desktop')),
    page TEXT NOT NULL DEFAULT 'homepage',
    viewport_width INTEGER,
    viewport_height INTEGER,

    -- Storage
    storage_path TEXT NOT NULL,

    -- Diff vs previous
    previous_screenshot_id UUID REFERENCES screenshots(id),
    diff_pct NUMERIC(5,2),
    diff_regions JSONB,
    significant_change BOOLEAN DEFAULT false,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_screenshots_store ON screenshots(store_id);
CREATE INDEX idx_screenshots_scan ON screenshots(scan_id);
CREATE INDEX idx_screenshots_device ON screenshots(store_id, device, created_at DESC);

ALTER TABLE screenshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "merchants_own_screenshots" ON screenshots
    FOR ALL USING (merchant_id = auth.uid());

-- ============================================================
-- 8. USER SIMULATIONS
-- ============================================================
-- Module Browser Automation — Real User Simulation.

CREATE TABLE user_simulations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID REFERENCES scans(id) ON DELETE CASCADE,
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,

    -- Results
    total_time_ms INTEGER NOT NULL,
    steps JSONB NOT NULL,
    bottleneck_step TEXT,
    bottleneck_cause TEXT,
    steps_count INTEGER,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_simulations_store ON user_simulations(store_id);

ALTER TABLE user_simulations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "merchants_own_simulations" ON user_simulations
    FOR ALL USING (merchant_id = auth.uid());

-- ============================================================
-- 9. FIXES
-- ============================================================
-- One-Click Fix tracking.
-- Status flow : pending -> approved -> applied | failed -> reverted

CREATE TABLE fixes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id UUID REFERENCES scan_issues(id) ON DELETE SET NULL,
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,

    -- Fix info
    fix_type TEXT NOT NULL,
    target TEXT,
    description TEXT,

    -- Status
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'applied', 'reverted', 'failed')),

    -- Snapshots (pour revert)
    before_state JSONB,
    after_state JSONB,

    -- Timestamps
    approved_at TIMESTAMPTZ,
    applied_at TIMESTAMPTZ,
    reverted_at TIMESTAMPTZ,

    -- Error
    error_message TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_fixes_store ON fixes(store_id);
CREATE INDEX idx_fixes_status ON fixes(status);
CREATE INDEX idx_fixes_issue ON fixes(issue_id);

ALTER TABLE fixes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "merchants_own_fixes" ON fixes
    FOR ALL USING (merchant_id = auth.uid());

CREATE TRIGGER fixes_updated_at BEFORE UPDATE ON fixes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- 10. FEEDBACK
-- ============================================================
-- Ouroboros — couche LEARN.

CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    scan_id UUID REFERENCES scans(id) ON DELETE SET NULL,
    issue_id UUID REFERENCES scan_issues(id) ON DELETE SET NULL,

    -- Feedback
    accepted BOOLEAN NOT NULL,
    reason TEXT,
    reason_category TEXT
        CHECK (reason_category IN (
            'not_relevant', 'too_risky', 'will_do_later',
            'disagree', 'already_fixed', 'other'
        )),

    -- Context
    recommendation_type TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_feedback_merchant ON feedback(merchant_id);
CREATE INDEX idx_feedback_type ON feedback(recommendation_type);
CREATE INDEX idx_feedback_accepted ON feedback(accepted);

ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "merchants_own_feedback" ON feedback
    FOR ALL USING (merchant_id = auth.uid());

-- ============================================================
-- 11. SUBSCRIPTIONS
-- ============================================================
-- Billing Stripe. Source de verite pour le plan actif.

CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,

    -- Stripe
    stripe_subscription_id TEXT UNIQUE NOT NULL,
    stripe_customer_id TEXT NOT NULL,
    stripe_price_id TEXT,

    -- Plan
    plan TEXT NOT NULL CHECK (plan IN ('free', 'starter', 'pro', 'agency')),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'past_due', 'canceled', 'trialing', 'incomplete')),

    -- Period
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT false,
    canceled_at TIMESTAMPTZ,

    -- Trial
    trial_start TIMESTAMPTZ,
    trial_end TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_subs_merchant ON subscriptions(merchant_id);
CREATE INDEX idx_subs_stripe ON subscriptions(stripe_subscription_id);
CREATE INDEX idx_subs_status ON subscriptions(status);

ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "merchants_own_subs" ON subscriptions
    FOR ALL USING (merchant_id = auth.uid());

CREATE TRIGGER subscriptions_updated_at BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- 12. USAGE RECORDS
-- ============================================================
-- Tracking des limites par plan.

CREATE TABLE usage_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,

    -- Usage
    usage_type TEXT NOT NULL
        CHECK (usage_type IN (
            'scan', 'listing_analysis', 'browser_test',
            'one_click_fix', 'bulk_operation'
        )),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    limit_count INTEGER NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(merchant_id, store_id, usage_type, period_start)
);

CREATE INDEX idx_usage_merchant ON usage_records(merchant_id);
CREATE INDEX idx_usage_period ON usage_records(period_start, period_end);

ALTER TABLE usage_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY "merchants_own_usage" ON usage_records
    FOR ALL USING (merchant_id = auth.uid());

CREATE TRIGGER usage_records_updated_at BEFORE UPDATE ON usage_records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- 13. WEBHOOK EVENTS
-- ============================================================
-- Idempotency pour les webhooks Shopify + Stripe.
-- Acces service_role uniquement (backend).

CREATE TABLE webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL CHECK (source IN ('shopify', 'stripe')),
    external_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    shop_domain TEXT,
    payload JSONB NOT NULL,

    -- Processing
    processed BOOLEAN DEFAULT false,
    processed_at TIMESTAMPTZ,
    processing_error TEXT,
    retry_count INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(source, external_id)
);

CREATE INDEX idx_webhooks_external ON webhook_events(source, external_id);
CREATE INDEX idx_webhooks_processed ON webhook_events(processed) WHERE processed = false;
CREATE INDEX idx_webhooks_topic ON webhook_events(topic);

ALTER TABLE webhook_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_only" ON webhook_events
    FOR ALL USING (auth.role() = 'service_role');

-- ============================================================
-- 14. NOTIFICATIONS
-- ============================================================

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    store_id UUID REFERENCES stores(id) ON DELETE CASCADE,

    -- Content
    channel TEXT NOT NULL CHECK (channel IN ('push', 'email', 'in_app')),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    action_url TEXT,
    category TEXT,

    -- Status
    read BOOLEAN DEFAULT false,
    read_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ DEFAULT NOW(),

    -- Delivery
    delivered BOOLEAN DEFAULT true,
    delivery_error TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_notifications_merchant ON notifications(merchant_id);
CREATE INDEX idx_notifications_unread ON notifications(merchant_id, read) WHERE read = false;
CREATE INDEX idx_notifications_sent ON notifications(sent_at DESC);

ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "merchants_own_notifications" ON notifications
    FOR ALL USING (merchant_id = auth.uid());

-- ============================================================
-- TRIGGER — Creer le profil merchant a l'inscription
-- ============================================================

CREATE TRIGGER create_merchant_on_signup
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION on_auth_user_created();

-- ============================================================
-- RELOAD SCHEMA
-- ============================================================

NOTIFY pgrst, 'reload schema';
