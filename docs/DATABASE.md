# DATABASE.md — Schéma StoreMD

> **Source de vérité pour le schéma PostgreSQL (Supabase).**
> **Toute modification passe par une migration numérotée dans `database/migrations/`.**
> **Après chaque migration : `NOTIFY pgrst, 'reload schema';`**

---

## CONVENTIONS

- Tables : `snake_case` pluriel (`scans`, `scan_issues`)
- Colonnes : `snake_case` (`store_id`, `created_at`)
- PKs : `id UUID DEFAULT gen_random_uuid()`
- FKs : `{table_singulier}_id` (ex: `merchant_id`, `store_id`, `scan_id`)
- Timestamps : `TIMESTAMPTZ`, toujours UTC
- Booleans : default explicite (`DEFAULT false` ou `DEFAULT true`)
- JSON flexible : `JSONB DEFAULT '{}'` ou `DEFAULT '[]'`
- Soft delete : `deleted_at TIMESTAMPTZ` quand nécessaire
- TOUTES les tables ont `created_at TIMESTAMPTZ DEFAULT NOW()`
- TOUTES les tables mutables ont `updated_at TIMESTAMPTZ DEFAULT NOW()` + trigger auto
- RLS activé sur CHAQUE table, sans exception

---

## SCHÉMA SQL COMPLET

```sql
-- ============================================================
-- EXTENSIONS
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";       -- Mem0 pgvector si self-hosted

-- ============================================================
-- 1. MERCHANTS
-- ============================================================
-- Profil étendu de auth.users (Supabase Auth).
-- Créé automatiquement via trigger on_auth_user_created.

CREATE TABLE merchants (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    name TEXT,

    -- Shopify
    shopify_shop_domain TEXT UNIQUE,              -- "mystore.myshopify.com"
    shopify_access_token_encrypted TEXT,           -- Fernet chiffré, JAMAIS en clair
    shopify_scopes TEXT[],                         -- ["read_products","write_products",...]
    shopify_installed_at TIMESTAMPTZ,

    -- Billing
    plan TEXT NOT NULL DEFAULT 'free'
        CHECK (plan IN ('free', 'starter', 'pro', 'agency')),
    stripe_customer_id TEXT UNIQUE,
    stripe_subscription_id TEXT,

    -- Notifications
    notification_email TEXT,                       -- default = email, overridable
    notification_push_enabled BOOLEAN DEFAULT false,
    notification_push_subscription JSONB,          -- web-push subscription object
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
-- INSERT/DELETE via service_role uniquement (auth trigger + uninstall webhook)

-- ============================================================
-- 2. STORES
-- ============================================================
-- Un merchant peut avoir plusieurs stores (Agency plan).
-- Pour Free/Starter/Pro : 1/1/3 stores max, enforced côté application.

CREATE TABLE stores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,

    -- Shopify
    shopify_shop_domain TEXT NOT NULL,
    shopify_shop_id TEXT,                          -- Shopify internal ID
    name TEXT,                                      -- Shop name from Shopify API
    primary_domain TEXT,                            -- "mystore.com" (custom domain)

    -- Theme
    theme_name TEXT,
    theme_id TEXT,
    theme_role TEXT DEFAULT 'main',                 -- "main", "unpublished"

    -- Store metrics (updated at each scan)
    products_count INTEGER DEFAULT 0,
    apps_count INTEGER DEFAULT 0,
    currency TEXT DEFAULT 'USD',
    country TEXT,                                    -- ISO 3166-1 alpha-2
    shopify_plan TEXT,                               -- "basic", "shopify", "advanced", "plus"

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

-- ============================================================
-- 3. SCANS
-- ============================================================
-- Chaque exécution du scan pipeline crée un record ici.
-- Status flow : pending → running → completed | failed

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
    score INTEGER,                                  -- 0-100 composite
    mobile_score INTEGER,                           -- 0-100
    desktop_score INTEGER,                          -- 0-100
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
    partial_scan BOOLEAN DEFAULT false,             -- true si certains scanners ont échoué
    scanner_results JSONB DEFAULT '{}',             -- résultats bruts par scanner (debug)
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

-- ============================================================
-- 4. SCAN ISSUES
-- ============================================================
-- Chaque problème détecté par un scanner.
-- Lié à un scan et à un store.

CREATE TABLE scan_issues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,

    -- Classification
    module TEXT NOT NULL
        CHECK (module IN ('health', 'listings', 'agentic', 'compliance', 'browser')),
    scanner TEXT NOT NULL,                          -- "app_impact", "residue_detector", etc.
    severity TEXT NOT NULL
        CHECK (severity IN ('critical', 'major', 'minor', 'info')),

    -- Content
    title TEXT NOT NULL,                             -- "App Privy injects 340KB of unminified JS"
    description TEXT NOT NULL,                       -- Détail complet
    impact TEXT,                                     -- "+1.8s load time"
    impact_value NUMERIC(10,2),                      -- 1.8 (pour sorting/filtering)
    impact_unit TEXT,                                -- "seconds", "score_points", "dollars"

    -- Fix
    fix_type TEXT
        CHECK (fix_type IN ('one_click', 'manual', 'developer')),
    fix_description TEXT,                            -- "Remove residual code [1-click]"
    auto_fixable BOOLEAN DEFAULT false,

    -- Status
    fix_applied BOOLEAN DEFAULT false,
    fix_applied_at TIMESTAMPTZ,
    dismissed BOOLEAN DEFAULT false,                 -- merchant a choisi d'ignorer
    dismissed_at TIMESTAMPTZ,

    -- Context (données spécifiques au type d'issue)
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
-- Apps Shopify installées sur le store du merchant.
-- Mis à jour à chaque scan.

CREATE TABLE store_apps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,

    -- Shopify app info
    shopify_app_id TEXT,
    name TEXT NOT NULL,
    handle TEXT,                                     -- slug Shopify
    version TEXT,
    developer TEXT,
    app_store_url TEXT,

    -- Permissions
    scopes TEXT[],

    -- Impact (mesuré par app_impact scanner)
    impact_ms INTEGER,                               -- impact estimé en ms sur le load time
    scripts_count INTEGER DEFAULT 0,
    scripts_size_kb NUMERIC(10,2) DEFAULT 0,
    css_size_kb NUMERIC(10,2) DEFAULT 0,

    -- Status
    status TEXT DEFAULT 'active'
        CHECK (status IN ('active', 'uninstalled', 'ghost_billing')),
    billing_amount NUMERIC(10,2),                    -- monthly charge
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

-- ============================================================
-- 6. PRODUCT ANALYSES
-- ============================================================
-- Résultats d'analyse par produit (module Listings + Agentic).
-- Un record par produit par scan.

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
    status TEXT,                                     -- "active", "draft", "archived"

    -- Listing score (module Listings)
    score INTEGER,                                   -- 0-100 composite
    title_score INTEGER,                             -- 0-100
    description_score INTEGER,
    images_score INTEGER,
    seo_score INTEGER,
    issues JSONB DEFAULT '[]',                       -- [{ element, score, suggestion }]
    suggestions JSONB DEFAULT '[]',

    -- Revenue (pour priorisation)
    revenue_30d NUMERIC(12,2),
    orders_30d INTEGER,
    views_30d INTEGER,
    priority_rank INTEGER,                           -- calculé : score faible + revenue élevé = rang bas

    -- Agentic readiness (module Agentic)
    agentic_ready BOOLEAN DEFAULT false,
    has_gtin BOOLEAN DEFAULT false,
    has_hs_code BOOLEAN DEFAULT false,
    hs_code TEXT,
    hs_code_status TEXT                              -- "valid", "missing", "suspicious"
        CHECK (hs_code_status IN ('valid', 'missing', 'suspicious')),
    hs_code_suggestion TEXT,
    metafields_filled_pct INTEGER DEFAULT 0,         -- 0-100
    schema_markup_valid BOOLEAN DEFAULT false,
    google_category_assigned BOOLEAN DEFAULT false,
    description_structured BOOLEAN DEFAULT false,    -- structuré pour IA (pas juste marketing)

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
-- Screenshots stockés dans Supabase Storage, refs ici.

CREATE TABLE screenshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID REFERENCES scans(id) ON DELETE CASCADE,
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,

    -- Screenshot info
    device TEXT NOT NULL CHECK (device IN ('mobile', 'desktop')),
    page TEXT NOT NULL DEFAULT 'homepage',           -- "homepage", "collection", "product"
    viewport_width INTEGER,                          -- 375 (mobile), 1440 (desktop)
    viewport_height INTEGER,

    -- Storage
    storage_path TEXT NOT NULL,                      -- Supabase Storage path

    -- Diff vs previous
    previous_screenshot_id UUID REFERENCES screenshots(id),
    diff_pct NUMERIC(5,2),                           -- % pixels changed
    diff_regions JSONB,                               -- [{ area, change, probable_cause }]
    significant_change BOOLEAN DEFAULT false,         -- diff > 5%

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
    steps JSONB NOT NULL,                            -- [{ name, url, time_ms, bottleneck, cause }]
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
-- Status flow : pending → approved → applied | failed
--                                  → reverted

CREATE TABLE fixes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id UUID REFERENCES scan_issues(id) ON DELETE SET NULL,
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,

    -- Fix info
    fix_type TEXT NOT NULL,                          -- "alt_text", "redirect", "remove_residue",
                                                     -- "fill_metafield", "rewrite_description"
    target TEXT,                                      -- ce qui est fixé (product ID, file path, URL)
    description TEXT,                                 -- human-readable

    -- Status
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'applied', 'reverted', 'failed')),

    -- Snapshots (pour revert)
    before_state JSONB,                              -- état avant le fix
    after_state JSONB,                               -- état après le fix

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

-- ============================================================
-- 10. FEEDBACK
-- ============================================================
-- Ouroboros — couche LEARN.
-- Le merchant accepte ou refuse une recommandation.

CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    scan_id UUID REFERENCES scans(id) ON DELETE SET NULL,
    issue_id UUID REFERENCES scan_issues(id) ON DELETE SET NULL,

    -- Feedback
    accepted BOOLEAN NOT NULL,
    reason TEXT,                                      -- si refusé, pourquoi (free text ou preset)
    reason_category TEXT                              -- preset categories pour analytics
        CHECK (reason_category IN (
            'not_relevant', 'too_risky', 'will_do_later',
            'disagree', 'already_fixed', 'other'
        )),

    -- Context
    recommendation_type TEXT,                        -- "uninstall_app", "css_fix", "alt_text", etc.

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
-- Billing Stripe. Source de vérité pour le plan actif.

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

-- ============================================================
-- 12. USAGE RECORDS
-- ============================================================
-- Tracking des limites par plan (scans/mois, listings analysés, etc.).

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
    period_start DATE NOT NULL,                      -- début du mois billing
    period_end DATE NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    limit_count INTEGER NOT NULL,                    -- limite du plan pour ce type

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(merchant_id, store_id, usage_type, period_start)
);

CREATE INDEX idx_usage_merchant ON usage_records(merchant_id);
CREATE INDEX idx_usage_period ON usage_records(period_start, period_end);

ALTER TABLE usage_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY "merchants_own_usage" ON usage_records
    FOR ALL USING (merchant_id = auth.uid());

-- ============================================================
-- 13. WEBHOOK EVENTS
-- ============================================================
-- Idempotency pour les webhooks Shopify + Stripe.
-- Accès service_role uniquement (backend).

CREATE TABLE webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL CHECK (source IN ('shopify', 'stripe')),
    external_id TEXT NOT NULL,                       -- Shopify webhook ID ou Stripe event ID
    topic TEXT NOT NULL,                              -- "app/uninstalled", "checkout.session.completed"
    shop_domain TEXT,                                 -- Shopify only
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

-- Service role uniquement — le backend traite les webhooks pour tous les merchants
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
    action_url TEXT,                                  -- deep link dans le dashboard
    category TEXT,                                    -- "score_drop", "app_update", "weekly_report"

    -- Status
    read BOOLEAN DEFAULT false,
    read_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ DEFAULT NOW(),

    -- Delivery
    delivered BOOLEAN DEFAULT true,                   -- false si push/email a échoué
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
-- TRIGGERS — updated_at automatique
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER merchants_updated_at BEFORE UPDATE ON merchants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER stores_updated_at BEFORE UPDATE ON stores
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER scans_updated_at BEFORE UPDATE ON scans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER store_apps_updated_at BEFORE UPDATE ON store_apps
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER subscriptions_updated_at BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER usage_records_updated_at BEFORE UPDATE ON usage_records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER fixes_updated_at BEFORE UPDATE ON fixes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- TRIGGER — Créer le profil merchant à l'inscription
-- ============================================================

CREATE OR REPLACE FUNCTION on_auth_user_created()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO merchants (id, email)
    VALUES (NEW.id, NEW.email);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER create_merchant_on_signup
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION on_auth_user_created();
```

---

## RELATIONS

```
merchants (1) ──→ (N) stores
merchants (1) ──→ (N) subscriptions
merchants (1) ──→ (N) notifications
merchants (1) ──→ (N) feedback

stores    (1) ──→ (N) scans
stores    (1) ──→ (N) store_apps
stores    (1) ──→ (N) product_analyses
stores    (1) ──→ (N) screenshots
stores    (1) ──→ (N) user_simulations
stores    (1) ──→ (N) fixes
stores    (1) ──→ (N) usage_records

scans     (1) ──→ (N) scan_issues
scans     (1) ──→ (N) product_analyses
scans     (1) ──→ (N) screenshots
scans     (1) ──→ (N) user_simulations

scan_issues (1) ──→ (N) fixes
scan_issues (1) ──→ (N) feedback

screenshots (1) ──→ (1) screenshots (previous, self-ref)
```

---

## LIMITES PAR PLAN

Enforcées côté application via la table `usage_records` :

| Ressource | Free | Starter | Pro | Agency |
|-----------|------|---------|-----|--------|
| Stores | 1 | 1 | 3 | 10 |
| Scans / mois | 3 (1 initial + 2) | ~4 (hebdo) | ~30 (daily) | ~300 (daily × 10 stores) |
| Listing analyses / mois | 5 | 100 | 1000 | Illimité |
| Browser tests / mois | 0 | 0 | ~30 | ~300 |
| One-click fixes / mois | 0 | 20 | 100 | Illimité |
| Bulk operations / mois | 0 | 0 | 10 | Illimité |

---

## NOTES IMPORTANTES

### Supabase Auth

`auth.users` est géré par Supabase Auth. La table `merchants` est un profil étendu créé automatiquement via le trigger `on_auth_user_created`. On ne crée JAMAIS un merchant manuellement — c'est toujours via Supabase Auth (Shopify OAuth → Supabase session).

### Service Role

`SUPABASE_SERVICE_ROLE_KEY` bypass le RLS. Utilisé UNIQUEMENT dans le backend pour :
- Traiter les webhooks (table `webhook_events`)
- Cross-store intelligence (agrégation anonymisée)
- Tâches admin (cleanup, migrations)

JAMAIS exposé au frontend. JAMAIS dans les logs.

### Migrations

Numérotées séquentiellement dans `database/migrations/` :
```
001_initial.sql              -- Ce schéma complet
002_add_hs_code_fields.sql   -- Exemple futur
003_add_notification_category.sql
```

Après chaque migration exécutée sur Supabase :
```sql
NOTIFY pgrst, 'reload schema';
```

### Supabase Storage

Fichiers stockés dans Supabase Storage (pas en DB) :
- Screenshots (Visual Store Test) : `screenshots/{store_id}/{scan_id}/{device}.png`
- Reports PDF : `reports/{store_id}/{date}.pdf`
- Collection backups : `backups/{store_id}/{timestamp}.json`

Bucket policies : chaque merchant accède uniquement à ses fichiers (path-based policy).

### Indexes partiels

Plusieurs indexes utilisent `WHERE` pour optimiser les requêtes fréquentes :
- `idx_issues_fix_applied` : issues non fixées (le cas le plus fréquent dans le dashboard)
- `idx_webhooks_processed` : webhooks non traités (queue processing)
- `idx_notifications_unread` : notifications non lues (badge counter)
- `idx_products_agentic` : produits non agent-ready (dashboard agentic)

### Pas de soft delete généralisé

Seul `stores.status = 'uninstalled'` est un soft delete (besoin de garder les données 30 jours pour export GDPR). Les autres tables utilisent `ON DELETE CASCADE` : quand un merchant est supprimé de `auth.users`, tout cascade.
