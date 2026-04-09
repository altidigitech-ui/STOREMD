# FEATURES.md — Spécification des 43 features StoreMD

> **Référence unique pour chaque feature.**
> **Avant d'implémenter une feature, vérifie sa spec ici.**

---

## LÉGENDE

- **Plan** : Free / Starter / Pro / Agency — plan minimum requis
- **Scanner** : fichier analyzer dans `backend/app/agent/analyzers/`
- **Endpoint** : route API qui expose les résultats
- **Composant** : composant frontend principal
- **Phase** : M1 (avril) = prioritaire / M2+ = après launch

---

## PLAN CHECKING

Avant d'exécuter une feature, TOUJOURS vérifier le plan du merchant :

```python
from app.services.billing import check_plan_access

async def run_scanner(store_id: str, feature: str):
    if not await check_plan_access(store_id, feature):
        raise AppError(
            code=ErrorCode.PLAN_REQUIRED,
            message=f"Feature '{feature}' requires {FEATURE_PLANS[feature]} plan or above",
            status_code=403,
            context={"feature": feature, "required_plan": FEATURE_PLANS[feature]},
        )
```

---

## MODULE 1 : STORE HEALTH (20 features)

---

### #1 — Health Score 24/7

| Champ | Valeur |
|-------|--------|
| Plan | Free |
| Phase | M1 |
| Scanner | `health_scorer.py` |
| Endpoint | `GET /api/v1/stores/{store_id}/health` |
| Composant | `dashboard/health/HealthScore.tsx` |

**Input :** Shopify API (theme, apps, pages), PageSpeed Insights API (mobile + desktop), scan précédent via Mem0.

**Output :**
```json
{
  "score": 58,
  "mobile_score": 43,
  "desktop_score": 72,
  "trend": "down",
  "trend_delta": -5,
  "issues_count": 7,
  "critical_count": 2,
  "scanned_at": "2026-04-09T10:00:00Z"
}
```

**Logique :** Score composite pondéré : mobile speed (30%) + desktop speed (20%) + app impact (20%) + code quality (15%) + SEO basics (15%). La pondération s'ajuste via Mem0 selon le profil du merchant (un store mobile-first pèse plus le mobile).

**Edge cases :**
- Premier scan = pas de trend, `trend` = `null`
- Store sans thème custom = baseline Dawn
- Store sans app = pas d'app impact score, redistribuer sur les autres critères
- PageSpeed API timeout = utiliser les métriques Shopify seules, flagger `partial_scan: true`

---

### #2 — Diagnostic 3 couches

| Champ | Valeur |
|-------|--------|
| Plan | Free |
| Phase | M1 |
| Scanner | `health_scorer.py` (sous-routine) |
| Endpoint | `GET /api/v1/stores/{store_id}/health/diagnostic` |
| Composant | `dashboard/health/DiagnosticFunnel.tsx` |

**Input :** Shopify analytics, Google Analytics (si connecté), scan results.

**Output :**
```json
{
  "traffic": { "score": 72, "issues": [...], "metrics": { "sessions_30d": 8200, "bot_pct": 12 } },
  "engagement": { "score": 55, "issues": [...], "metrics": { "bounce_rate": 64, "avg_session_s": 48 } },
  "purchase": { "score": 41, "issues": [...], "metrics": { "cart_rate": 3.2, "checkout_abandon": 71, "conversion": 1.1 } }
}
```

**Logique :** Funnel Traffic → Engagement → Purchase. Chaque couche a un score /100 et des recommandations spécifiques. Le diagnostic identifie OÙ le store perd des clients.

---

### #3 — Alertes régressives

| Champ | Valeur |
|-------|--------|
| Plan | Starter |
| Phase | M1 |
| Scanner | `trend_analyzer.py` |
| Endpoint | `POST /api/v1/stores/{store_id}/alerts/settings` (config), alertes via notifications |
| Composant | `dashboard/settings/AlertSettings.tsx` |

**Input :** Score actuel vs baseline du store (Mem0), seuil configurable (default : -5 points).

**Output :** Push notification + email : score avant, score après, cause probable, action recommandée 1-clic.

**Logique :** Compare le score actuel avec la baseline PERSONNALISÉE du store (pas un seuil fixe). Un store qui tourne normalement à 65/100 est alerté à 60, pas à 50. La baseline est calculée sur les 30 derniers jours de scans (Mem0).

---

### #4 — App Impact Scanner

| Champ | Valeur |
|-------|--------|
| Plan | Starter |
| Phase | M1 |
| Scanner | `app_impact.py` |
| Endpoint | `GET /api/v1/stores/{store_id}/apps/impact` |
| Composant | `dashboard/health/AppImpact.tsx` |

**Input :** Apps installées (Shopify API), assets du thème (script tags, liquid snippets, CSS), timing par ressource.

**Output :**
```json
{
  "apps": [
    {
      "name": "Privy",
      "impact_ms": 1800,
      "scripts_count": 3,
      "scripts_size_kb": 340,
      "recommendation": "uninstall_or_replace",
      "alternatives": ["Justuno (lighter)"]
    }
  ],
  "total_app_impact_ms": 3200
}
```

**Logique :** Pour chaque app installée : identifier les scripts injectés (script tags, theme app extensions, liquid snippets dans le thème), mesurer taille + impact estimé sur le load time. Trier par impact décroissant.

**Edge cases :** Apps qui injectent via theme app extensions (pas de script tag visible). Apps qui chargent des iframes (mesurer le poids de l'iframe). Apps sans impact mesurable = `impact_ms: 0`.

---

### #5 — Bot Traffic Filter

| Champ | Valeur |
|-------|--------|
| Plan | Pro |
| Phase | M1 |
| Scanner | `bot_traffic.py` |
| Endpoint | `GET /api/v1/stores/{store_id}/traffic/bots` |
| Composant | `dashboard/health/BotTraffic.tsx` |

**Input :** Shopify analytics, user agents connus, patterns de navigation.

**Output :**
```json
{
  "human_pct": 78,
  "bot_pct": 22,
  "bots": [
    { "type": "search_engine", "source": "Googlebot", "requests_24h": 342, "impact": "normal" },
    { "type": "ai_crawler", "source": "GPTBot", "requests_24h": 89, "impact": "high_bandwidth" },
    { "type": "scraper", "source": "unknown", "requests_24h": 1200, "impact": "suspicious" }
  ]
}
```

**Logique :** Classifier : bots connus (Googlebot, Bingbot), crawlers IA (GPTBot, ClaudeBot, PerplexityBot), scrapers suspicieux. Croiser avec le AI Crawler Monitor (#10).

---

### #6 — App Risk Monitor

| Champ | Valeur |
|-------|--------|
| Plan | Pro |
| Phase | M2+ (nécessite masse critique de merchants) |
| Scanner | `app_impact.py` (background Celery task) |
| Endpoint | `GET /api/v1/stores/{store_id}/apps/risks` |
| Composant | `dashboard/health/AppRisks.tsx` |

**Input :** Mem0 cross-store intelligence, corrélation app updates → régressions de score.

**Output :**
```json
{
  "risky_apps": [
    {
      "name": "Reviews+",
      "risk_level": "high",
      "reason": "Caused regressions on 47 stores after v3.2 update",
      "affected_stores_count": 47,
      "recommendation": "Monitor closely, consider alternative"
    }
  ]
}
```

**Logique :** Cross-store : si l'app X a causé des régressions sur 10+ stores après sa dernière update → alerte les stores qui l'ont installée. Nécessite masse critique de merchants. En attendant : désactivé, placeholder UI.

---

### #7 — Collection Backup auto

| Champ | Valeur |
|-------|--------|
| Plan | Starter |
| Phase | M1 |
| Scanner | N/A (trigger webhook `themes/update`) |
| Endpoint | `POST /api/v1/stores/{store_id}/backups`, `GET .../backups` |
| Composant | `dashboard/settings/Backups.tsx` |

**Input :** Webhook Shopify `themes/update`, collection data via API.

**Output :** Snapshot JSON des collections stocké dans Supabase Storage. Rétention 30 jours.

---

### #8 — Content Theft Scanner

| Champ | Valeur |
|-------|--------|
| Plan | Pro |
| Phase | **M2+ (Phase 2)** |
| Scanner | `content_theft.py` |
| Endpoint | `GET /api/v1/stores/{store_id}/content/theft` |

**Logique :** Compare descriptions produits et images du store avec le web. Nécessite API externe (Copyscape ou similaire). Non-prioritaire M1.

---

### #9 — Security Monitor

| Champ | Valeur |
|-------|--------|
| Plan | Starter |
| Phase | M1 |
| Scanner | `security_monitor.py` |
| Endpoint | `GET /api/v1/stores/{store_id}/security` |
| Composant | `dashboard/health/SecurityStatus.tsx` |

**Input :** Headers HTTP du store, SSL cert info, permissions apps (Shopify API scopes).

**Output :**
```json
{
  "ssl_valid": true,
  "ssl_expires_in_days": 47,
  "headers_score": 65,
  "missing_headers": ["Content-Security-Policy", "X-Frame-Options"],
  "app_permissions": [
    { "app": "Review App", "scopes": ["write_orders", "read_customers"], "risk_level": "high", "reason": "write_orders is excessive for a review app" }
  ]
}
```

---

### #10 — AI Crawler Monitor

| Champ | Valeur |
|-------|--------|
| Plan | Pro |
| Phase | M1 |
| Scanner | `bot_traffic.py` (sous-routine, filtré sur crawlers IA) |
| Endpoint | `GET /api/v1/stores/{store_id}/traffic/ai-crawlers` |
| Composant | `dashboard/health/AICrawlers.tsx` |

**Input :** Même data que Bot Traffic Filter, filtré sur crawlers IA connus.

**Output :**
```json
{
  "crawlers": [
    { "name": "GPTBot", "requests_24h": 89, "bandwidth_kb": 12400, "blocked_by_robots_txt": false },
    { "name": "ClaudeBot", "requests_24h": 23, "bandwidth_kb": 3200, "blocked_by_robots_txt": true }
  ],
  "recommendation": "Consider blocking GPTBot if you don't want your content used for AI training"
}
```

---

### #11 — Benchmark concurrence

| Champ | Valeur |
|-------|--------|
| Plan | Pro |
| Phase | M2+ (nécessite masse critique) |
| Scanner | `benchmark.py` |
| Endpoint | `GET /api/v1/stores/{store_id}/benchmark` |
| Composant | `dashboard/health/Benchmark.tsx` |

**Output :** `{ store_score, avg_score, percentile, top_10_avg }`. En attendant la masse critique : benchmark vs données publiques (average Shopify store metrics).

---

### #12 — Fix Generator

| Champ | Valeur |
|-------|--------|
| Plan | Free |
| Phase | M1 |
| Scanner | Intégré dans chaque analyzer via `fix_generator.py` |
| Endpoint | Inclus dans chaque scan result (`issues[].fix`) |
| Composant | `dashboard/shared/FixSuggestion.tsx` |

**Logique :** Claude API génère une recommandation en langage simple pour chaque issue. 3 niveaux :
- `one_click` : automatisable via Shopify API (alt text, redirects, code résiduel)
- `manual` : le merchant peut faire seul (config, settings)
- `developer` : nécessite un dev (code custom, thème)

Chaque fix inclut : `estimated_impact` (en secondes ou score), `steps` (instructions).

---

### #13 — Weekly Report Push

| Champ | Valeur |
|-------|--------|
| Plan | Starter |
| Phase | M1 |
| Scanner | `report_generator.py` (Celery periodic task, lundi 9h timezone merchant) |
| Endpoint | `GET /api/v1/stores/{store_id}/reports/latest` |
| Composant | Email template HTML + `dashboard/reports/WeeklyReport.tsx` |

**Output :** Score actuel, delta vs semaine précédente, top 3 issues, issues résolues, 1 recommendation prioritaire.

---

### #14 — Uninstall Residue Detector

| Champ | Valeur |
|-------|--------|
| Plan | Starter |
| Phase | M1 |
| Scanner | `residue_detector.py` |
| Endpoint | `GET /api/v1/stores/{store_id}/residue` |
| Composant | `dashboard/health/ResidueDetector.tsx` |

**Input :** Theme assets (Shopify API), liquid templates, script tags. Compare avec apps actuellement installées.

**Output :**
```json
{
  "residues": [
    {
      "app_name_guess": "Privy (uninstalled 3 months ago)",
      "file_path": "snippets/privy-popup.liquid",
      "size_kb": 12.4,
      "type": "liquid",
      "auto_removable": true
    }
  ],
  "total_residue_kb": 34.2,
  "estimated_impact_ms": 600
}
```

**Logique :** Base de signatures d'apps connues + heuristiques (noms de fichiers, commentaires dans le code, références à des domaines d'apps). Si un script/snippet référence une app qui n'est plus installée → résidu.

---

### #15 — Pixel Health Check

| Champ | Valeur |
|-------|--------|
| Plan | Starter |
| Phase | M1 |
| Scanner | `pixel_health.py` |
| Endpoint | `GET /api/v1/stores/{store_id}/pixels` |
| Composant | `dashboard/health/PixelHealth.tsx` |

**Output :**
```json
{
  "pixels": [
    { "name": "Google Analytics 4", "type": "analytics", "status": "active", "issue": null },
    { "name": "Meta Pixel", "type": "marketing", "status": "duplicate", "issue": "Found 2 instances, one via app and one manual" },
    { "name": "TikTok Pixel", "type": "marketing", "status": "missing", "issue": "TikTok channel installed but pixel not detected" }
  ]
}
```

---

### #16 — App Update Tracker

| Champ | Valeur |
|-------|--------|
| Plan | Pro |
| Phase | M1 |
| Scanner | `realtime_monitor.py` (Celery periodic task) |
| Endpoint | `GET /api/v1/stores/{store_id}/apps/updates` |
| Composant | `dashboard/health/AppUpdates.tsx` |

**Logique :** Stocke la version de chaque app dans Mem0. Compare régulièrement. Si une app se met à jour → scan rapide pour vérifier si le score change. Corrélation update → régression.

---

### #17 — Permission Monitor

| Champ | Valeur |
|-------|--------|
| Plan | Pro |
| Phase | M1 |
| Scanner | `security_monitor.py` (sous-routine) |
| Endpoint | `GET /api/v1/stores/{store_id}/apps/permissions` |
| Composant | `dashboard/health/PermissionMonitor.tsx` |

**Logique :** Flag apps avec permissions excessives. Ex : app de reviews qui demande `write_orders`. Alerte si une app change ses scopes.

---

### #18 — Code Weight Scanner

| Champ | Valeur |
|-------|--------|
| Plan | Starter |
| Phase | M1 |
| Scanner | `code_weight.py` |
| Endpoint | `GET /api/v1/stores/{store_id}/code-weight` |
| Composant | `dashboard/health/CodeWeight.tsx` |

**Output :**
```json
{
  "total_js_kb": 890,
  "total_css_kb": 210,
  "by_source": [
    { "source": "theme", "js_kb": 120, "css_kb": 85, "files_count": 4 },
    { "source": "Privy", "js_kb": 340, "css_kb": 12, "files_count": 3 },
    { "source": "Klaviyo", "js_kb": 180, "css_kb": 8, "files_count": 2 }
  ]
}
```

---

### #19 — Ghost Billing Detector

| Champ | Valeur |
|-------|--------|
| Plan | Starter |
| Phase | M1 |
| Scanner | `ghost_billing.py` |
| Endpoint | `GET /api/v1/stores/{store_id}/billing/ghosts` |
| Composant | `dashboard/health/GhostBilling.tsx` |

**Input :** Shopify recurring charges API vs apps actuellement installées.

**Output :**
```json
{
  "ghosts": [
    { "app_name": "Old SEO App", "charge_amount": 9.99, "since": "2025-11-01", "total_lost": 49.95 }
  ],
  "total_monthly_ghost": 9.99
}
```

---

### #20 — Email Domain Health Monitor

| Champ | Valeur |
|-------|--------|
| Plan | Pro |
| Phase | M1 |
| Scanner | `email_health.py` |
| Endpoint | `GET /api/v1/stores/{store_id}/email/health` |
| Composant | `dashboard/health/EmailHealth.tsx` |

**Input :** DNS lookup du domaine du store (MX, SPF, DKIM, DMARC records).

**Output :** `{ domain, spf: "pass"|"fail"|"missing", dkim: ..., dmarc: ..., deliverability_risk: "low"|"medium"|"high" }`

---

## MODULE 2 : LISTINGS (14 features)

---

### #21 — Catalogue Scan

| Champ | Valeur |
|-------|--------|
| Plan | Free (5 produits) / Starter (100) / Pro (1000) / Agency (illimité) |
| Phase | M1 |
| Scanner | `listing_analyzer.py` |
| Endpoint | `GET /api/v1/stores/{store_id}/listings/scan` |
| Composant | `dashboard/listings/CatalogueScan.tsx` |

**Input :** Products API Shopify (paginated, toutes les données produit).

**Output :**
```json
{
  "products_scanned": 847,
  "avg_score": 54,
  "products": [
    {
      "shopify_product_id": "gid://shopify/Product/123",
      "title": "Organic Face Cream",
      "score": 42,
      "issues": [
        { "element": "description", "score": 20, "suggestion": "Too short (23 words). Add benefits, ingredients, usage instructions." },
        { "element": "images", "score": 35, "suggestion": "3/5 images missing alt text" },
        { "element": "seo", "score": 60, "suggestion": "Meta description is auto-generated from product description" }
      ]
    }
  ]
}
```

**Logique :** Score /100 par listing : titre (25%) + description (25%) + images (25%) + SEO (25%). Critères titre : longueur 40-70 chars, keywords, pas de ALL CAPS. Description : >100 mots, structurée, pas de copier-coller fabricant. Images : ≥3, alt text, taille, qualité. SEO : meta title, meta description, URL handle.

---

### #22 — Priorisation par impact revenue

| Champ | Valeur |
|-------|--------|
| Plan | Starter |
| Phase | M1 |
| Scanner | `listing_analyzer.py` (sous-routine) |
| Endpoint | `GET /api/v1/stores/{store_id}/listings/priorities` |

**Logique :** Score faible + revenue élevé = priorité haute. Score élevé + revenue faible = priorité basse. Le merchant fixe d'abord ce qui rapporte le plus.

---

### #23 — Diagnostic par élément

| Champ | Valeur |
|-------|--------|
| Plan | Free |
| Phase | M1 |

Inclus dans le Catalogue Scan (#21). Chaque produit a un breakdown par élément (titre, description, images, SEO) avec score + suggestion spécifique.

---

### #24 — Rewrite ciblé

| Champ | Valeur |
|-------|--------|
| Plan | Starter |
| Phase | M1 |
| Scanner | `listing_analyzer.py` + `fix_generator.py` |
| Endpoint | `POST /api/v1/stores/{store_id}/listings/{product_id}/rewrite` |

**Logique :** Claude API réécrit UNIQUEMENT les éléments faibles. Si le titre est bon (score >75) → garde-le. Si la description est faible → réécrit. Preview avant apply. Safe Mode = toujours réversible.

---

### #25 — Bulk Import Intelligent

| Champ | Valeur |
|-------|--------|
| Plan | Pro |
| Phase | M1 |
| Endpoint | `POST /api/v1/stores/{store_id}/listings/import` |

**Input :** CSV uploadé par le merchant. **Output :** Validation + enrichissement auto (alt text, SEO, descriptions) → import dans Shopify.

---

### #26 — Dead Listing Detector

| Champ | Valeur |
|-------|--------|
| Plan | Starter |
| Phase | M1 |
| Scanner | `listing_analyzer.py` (sous-routine) |
| Endpoint | inclus dans `/listings/scan` |

**Logique :** Listings avec 0 vues ET 0 ventes depuis 90 jours. Recommandation : améliorer, archiver, ou supprimer.

---

### #27 — Image Optimizer

| Champ | Valeur |
|-------|--------|
| Plan | Starter |
| Phase | M1 |
| Scanner | `listing_analyzer.py` (sous-routine) |
| Endpoint | `POST /api/v1/stores/{store_id}/listings/images/optimize` |

**Logique :** Détection : alt text manquant, images trop lourdes, pas de WebP. Fix : générer alt text via Claude API, recommander compression. One-Click Fix pour l'alt text (write via Shopify API).

---

### #28 — Product Variant Organizer

| Champ | Valeur |
|-------|--------|
| Plan | Pro |
| Phase | M2+ |

**Logique :** Détecte variantes mal structurées (options incohérentes, noms inconsistants, ordre illogique). Recommande une restructuration.

---

### #29 — SEO Engine

| Champ | Valeur |
|-------|--------|
| Plan | Starter |
| Phase | M1 |
| Scanner | `listing_analyzer.py` (sous-routine SEO) |
| Endpoint | inclus dans `/listings/scan` + `POST .../listings/{id}/seo` |

**Logique :** Vérifie et optimise : meta title (50-60 chars, keyword), meta description (120-160 chars), URL handle (court, keyword). Claude API génère des suggestions. One-Click Fix pour appliquer.

---

### #30 — Multi-langue

| Champ | Valeur |
|-------|--------|
| Plan | Pro |
| Phase | M2+ |

**Logique :** Détecte les listings non-traduits dans les marchés activés (Shopify Markets). Alerte : "47 produits non traduits pour le marché FR."

---

### #31 — New Product Watch

| Champ | Valeur |
|-------|--------|
| Plan | Starter |
| Phase | M1 |
| Scanner | webhook trigger → `listing_analyzer.py` |
| Endpoint | utilise le système d'alertes |

**Logique :** Webhook `products/create` → analyse auto du nouveau produit → notification avec score + suggestions.

---

### #32 — Benchmark catégorie

| Champ | Valeur |
|-------|--------|
| Plan | Pro |
| Phase | M2+ |

**Logique :** Compare les listings avec les top performers du même secteur. Nécessite masse critique.

---

### #33 — Bulk Operations

| Champ | Valeur |
|-------|--------|
| Plan | Pro |
| Phase | M1 |
| Endpoint | `POST /api/v1/stores/{store_id}/listings/bulk` |

**Logique :** 50-500 listings en 1 opération : rewrite descriptions, générer alt text, optimiser SEO. Celery task (background, longue durée). Progress tracking via WebSocket ou polling.

---

### #34 — Zero Lock-in + Safe Mode

| Champ | Valeur |
|-------|--------|
| Plan | Free |
| Phase | M1 |

**Logique :** TOUTES les modifications sont réversibles. Preview avant apply. Snapshot before/after stocké en DB. Le merchant peut revert n'importe quelle modification. C'est un principe, pas une feature UI isolée — intégré dans chaque fix et rewrite.

---

## MODULE 3 : AGENTIC READINESS (4 features)

---

### #35 — Agentic Readiness Score

| Champ | Valeur |
|-------|--------|
| Plan | Starter |
| Phase | M1 |
| Scanner | `agentic_readiness.py` |
| Endpoint | `GET /api/v1/stores/{store_id}/agentic/score` |
| Composant | `dashboard/agentic/AgenticScore.tsx` |

**Input :** Products API (metafields, GTIN, categories, descriptions), theme (schema markup), Shopify Catalog status.

**Output :**
```json
{
  "score": 34,
  "checks": [
    { "name": "GTIN present", "status": "fail", "affected_products": 120, "fix": "Add GTIN for 120 products" },
    { "name": "Metafields filled", "status": "partial", "affected_products": 89, "fix": "Fill 'material' for 89 variants" },
    { "name": "Structured descriptions", "status": "fail", "affected_products": 45, "fix": "Restructure 45 descriptions for AI format" },
    { "name": "Schema markup", "status": "pass", "affected_products": 0 },
    { "name": "Google categories", "status": "fail", "affected_products": 200, "fix": "Assign Google product categories" },
    { "name": "Shopify Catalog active", "status": "pass", "affected_products": 0 }
  ]
}
```

**Pitch :** "Ton store est prêt à 34% pour ChatGPT Shopping."

---

### #36 — Agentic Fix Generator

| Champ | Valeur |
|-------|--------|
| Plan | Starter |
| Phase | M1 |
| Scanner | `agentic_readiness.py` (sous-routine) |
| Endpoint | `POST /api/v1/stores/{store_id}/agentic/fixes` |

**Logique :** Pour chaque check failed → action corrective spécifique. Auto-fixable quand possible (One-Click Fix pour metafields, descriptions via Shopify API write).

---

### #37 — Agentic Monitoring

| Champ | Valeur |
|-------|--------|
| Plan | Pro |
| Phase | M1 |
| Scanner | `agentic_readiness.py` (webhook trigger `products/create`, `products/update`) |

**Logique :** Chaque nouveau produit ou update → vérifier les critères agentic. Si non-conforme → alerte merchant.

---

### #38 — HS Code Validator

| Champ | Valeur |
|-------|--------|
| Plan | Pro |
| Phase | M1 |
| Scanner | `hs_code_validator.py` |
| Endpoint | `GET /api/v1/stores/{store_id}/products/hs-codes` |
| Composant | `dashboard/agentic/HSCodes.tsx` |

**Input :** Products API (`hs_code` field, `product_type`, tags).

**Output :**
```json
{
  "missing_count": 47,
  "suspicious_count": 12,
  "products": [
    { "id": "123", "title": "Silk Scarf", "hs_code": null, "status": "missing", "suggestion": "6214.10 (silk scarves)" },
    { "id": "456", "title": "Leather Bag", "hs_code": "9999.99", "status": "suspicious", "suggestion": "4202.21 (leather handbags)" }
  ]
}
```

**Logique :** HS code présent ? Format valide (6-10 digits) ? Cohérent avec le `product_type` ? Mauvais HS code = mauvais tarif = retard douane = chargebacks.

---

## MODULE 4 : COMPLIANCE & FIXES (3 features)

---

### #39 — Accessibility Scanner (EAA)

| Champ | Valeur |
|-------|--------|
| Plan | Starter |
| Phase | M1 |
| Scanner | `accessibility.py` (statique) + `browser/accessibility_live.py` (Pro, rendu réel) |
| Endpoint | `GET /api/v1/stores/{store_id}/accessibility` |
| Composant | `dashboard/compliance/Accessibility.tsx` |

**Output :**
```json
{
  "score": 62,
  "violations": [
    { "rule": "img-alt", "severity": "critical", "count": 23, "fix": "Add alt text to 23 images", "auto_fixable": true },
    { "rule": "color-contrast", "severity": "major", "count": 5, "fix": "Increase contrast ratio on 5 elements" },
    { "rule": "label", "severity": "major", "count": 2, "fix": "Add labels to 2 form fields" }
  ],
  "eaa_compliant": false,
  "live_test_available": true
}
```

**Logique :** WCAG 2.1 Level AA. Scan statique (HTML via Shopify API) pour Starter. Scan rendu réel (Playwright) pour Pro — vérifie boutons cliquables sur mobile, contraste, navigation clavier, ARIA.

---

### #40 — Broken Links Scanner

| Champ | Valeur |
|-------|--------|
| Plan | Starter |
| Phase | M1 |
| Scanner | `broken_links.py` |
| Endpoint | `GET /api/v1/stores/{store_id}/links/broken` |
| Composant | `dashboard/compliance/BrokenLinks.tsx` |

**Output :**
```json
{
  "broken_count": 8,
  "links": [
    { "url": "/products/old-product", "source_page": "/collections/summer", "status_code": 404, "type": "internal", "auto_fixable": true },
    { "url": "https://expired-partner.com/deal", "source_page": "/pages/about", "status_code": 0, "type": "external", "auto_fixable": false }
  ]
}
```

**Logique :** Crawl toutes les pages du store, HEAD request sur chaque lien. Internes cassés → redirect auto via One-Click Fix. Externes cassés → recommandation.

---

### #41 — One-Click Fix Engine

| Champ | Valeur |
|-------|--------|
| Plan | Starter |
| Phase | M1 |
| Scanner | N/A (transversal, utilisé par tous les modules) |
| Endpoint | `POST /api/v1/stores/{store_id}/fixes/{fix_id}/apply` |
| Composant | `dashboard/shared/OneClickFix.tsx` |

**Types de fixes auto :**
- Alt text manquant → Claude API génère + Shopify API `write_products` applique
- Broken link interne → créer redirect (Shopify API)
- Code résiduel → supprimer du thème (Shopify API `write_themes`)
- Metafields vides → remplir (Shopify API `write_products`)
- Descriptions non-structurées → réécrire pour IA (Shopify API `write_products`)

**Règles absolues :**
- TOUJOURS preview avant apply (le merchant voit avant/après)
- TOUJOURS réversible (snapshot `before_state` en DB)
- Le merchant APPROUVE avant l'action — jamais d'application silencieuse
- Snapshot before/after stocké dans la table `fixes`

---

## MODULE 5 : BROWSER AUTOMATION (2 features + 1 extension)

---

### #42 — Visual Store Test

| Champ | Valeur |
|-------|--------|
| Plan | Pro |
| Phase | M1 |
| Scanner | `browser/visual_store_test.py` |
| Endpoint | `GET /api/v1/stores/{store_id}/visual/diff` |
| Composant | `dashboard/browser/VisualDiff.tsx` |

**Input :** URL du store. Screenshots précédents (Supabase Storage).

**Output :**
```json
{
  "screenshots": {
    "mobile": { "current": "storage://screenshots/xxx-mobile.png", "previous": "storage://screenshots/yyy-mobile.png" },
    "desktop": { "current": "storage://screenshots/xxx-desktop.png", "previous": "storage://screenshots/yyy-desktop.png" }
  },
  "diff": {
    "mobile_diff_pct": 12.4,
    "desktop_diff_pct": 3.1,
    "changed_regions": [
      { "area": "hero_banner", "change": "shifted_down_120px", "probable_cause": "Reviews+ v3.2 update yesterday" }
    ]
  }
}
```

**Logique :** Playwright rend le store mobile (375px) + desktop (1440px). Pixel diff avec screenshot précédent. Si changement significatif (>5%) → identifier cause probable (corrélation temporelle avec app updates, theme changes). Celery task (lourd, 30-60s).

---

### #43 — Real User Simulation

| Champ | Valeur |
|-------|--------|
| Plan | Pro |
| Phase | M1 |
| Scanner | `browser/real_user_simulation.py` |
| Endpoint | `GET /api/v1/stores/{store_id}/simulation` |
| Composant | `dashboard/browser/UserSimulation.tsx` |

**Output :**
```json
{
  "total_time_ms": 14200,
  "steps": [
    { "name": "Homepage", "url": "/", "time_ms": 2100, "bottleneck": false },
    { "name": "Collection", "url": "/collections/all", "time_ms": 1800, "bottleneck": false },
    { "name": "Product", "url": "/products/face-cream", "time_ms": 6100, "bottleneck": true, "cause": "Privy popup loads 340KB before content" },
    { "name": "Add to Cart", "url": null, "time_ms": 800, "bottleneck": false },
    { "name": "Checkout", "url": "/checkout", "time_ms": 3400, "bottleneck": false }
  ],
  "bottleneck_step": "Product",
  "bottleneck_cause": "Privy popup injects 340KB of unminified JS before product content renders"
}
```

**Logique :** Playwright simule Homepage → Collection → Product → Add to Cart → Checkout. Mesure le temps RÉEL à chaque étape. Pas un score PageSpeed théorique — le VRAI temps vécu par un client. Celery task (lourd, 60-90s).

**Pitch :** "Parcours complet : 14.2s. Bottleneck : page produit (6.1s). Cause : popup Privy 340KB."

---

### Accessibility Live Test (extension du #39)

| Champ | Valeur |
|-------|--------|
| Plan | Pro |
| Phase | M1 |
| Scanner | `browser/accessibility_live.py` |
| Endpoint | inclus dans `GET /api/v1/stores/{store_id}/accessibility?live=true` |

**Logique :** Playwright rend la page et vérifie WCAG en conditions réelles : boutons cliquables sur mobile ? Contraste suffisant avec le rendu réel (pas les couleurs du code) ? Navigation clavier ? Formulaires labellisés ? Complète le scan statique du #39.

---

## FEATURE → PLAN MAPPING

Pour le `check_plan_access()` dans le backend :

```python
FEATURE_PLANS: dict[str, str] = {
    # Free
    "health_score": "free",
    "diagnostic": "free",
    "fix_generator": "free",
    "catalogue_scan_5": "free",
    "diagnostic_element": "free",
    "zero_lockin": "free",
    
    # Starter
    "alerts": "starter",
    "app_impact": "starter",
    "collection_backup": "starter",
    "security_monitor": "starter",
    "weekly_report": "starter",
    "residue_detector": "starter",
    "pixel_health": "starter",
    "code_weight": "starter",
    "ghost_billing": "starter",
    "catalogue_scan_100": "starter",
    "listing_priority": "starter",
    "listing_rewrite": "starter",
    "dead_listing": "starter",
    "image_optimizer": "starter",
    "seo_engine": "starter",
    "new_product_watch": "starter",
    "agentic_score": "starter",
    "agentic_fix": "starter",
    "accessibility_scan": "starter",
    "broken_links": "starter",
    "one_click_fix": "starter",
    
    # Pro
    "bot_filter": "pro",
    "app_risk": "pro",
    "content_theft": "pro",
    "ai_crawler": "pro",
    "benchmark": "pro",
    "app_update": "pro",
    "permission_monitor": "pro",
    "email_health": "pro",
    "catalogue_scan_1000": "pro",
    "bulk_import": "pro",
    "variant_organizer": "pro",
    "multi_langue": "pro",
    "benchmark_category": "pro",
    "bulk_operations": "pro",
    "agentic_monitoring": "pro",
    "hs_code": "pro",
    "visual_store_test": "pro",
    "user_simulation": "pro",
    "accessibility_live": "pro",
    
    # Agency = tout Pro + multi-stores + API + white-label
}
```
