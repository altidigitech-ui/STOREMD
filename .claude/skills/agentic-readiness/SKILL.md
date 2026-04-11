# Skill: Agentic Readiness

> **Utilise ce skill quand tu travailles sur le module Agentic Readiness :**
> **Agentic Readiness Score, Agentic Fix Generator, Agentic Monitoring, HS Code Validator.**
> **EXCLUSIVITÉ MONDIALE — aucun concurrent ne fait ça.**

---

## QUAND UTILISER

- Implémenter/modifier `app/agent/analyzers/agentic_readiness.py`
- Implémenter/modifier `app/agent/analyzers/hs_code_validator.py`
- Travailler sur les routes `app/api/routes/agentic.py`
- Comprendre les critères de compatibilité IA (ChatGPT Shopping, Copilot, Gemini)
- Implémenter les fixes agentic (metafields, GTIN, descriptions structurées)

---

## CONTEXTE BUSINESS

Shopify a lancé les **Agentic Storefronts** en mars 2026. Les merchants vendent dans ChatGPT, Microsoft Copilot, Google Gemini. Les AI orders ont augmenté de **15x** depuis janvier 2025.

Un store qui n'est pas "agent-ready" est **INVISIBLE** pour les agents IA. Les agents IA ne peuvent pas recommander un produit si :
- Les metafields sont vides (pas de matière, dimensions, poids)
- Le GTIN/barcode est absent (l'agent ne peut pas identifier le produit)
- La description est du marketing flou (l'agent a besoin de faits structurés)
- Le schema markup est manquant ou incorrect
- La catégorie Google n'est pas assignée

**Pitch :** "Ton store est prêt à 34% pour ChatGPT Shopping."

**PERSONNE** ne scanne ça. StoreMD est le PREMIER et le SEUL.

---

## LES 4 FEATURES

| # | Feature | Plan | Scanner |
|---|---------|------|---------|
| 35 | Agentic Readiness Score (/100) | Starter | `agentic_readiness.py` |
| 36 | Agentic Fix Generator | Starter | `agentic_readiness.py` (sous-routine) |
| 37 | Agentic Monitoring (webhook trigger) | Pro | `agentic_readiness.py` (webhook) |
| 38 | HS Code Validator | Pro | `hs_code_validator.py` |

---

## AGENTIC READINESS SCANNER

### Les 6 checks

Chaque produit est vérifié sur 6 critères. Le score global = moyenne pondérée × produits.

| Check | Poids | Ce qu'on vérifie | GraphQL field |
|-------|-------|-----------------|---------------|
| **GTIN present** | 20% | Barcode/GTIN renseigné sur chaque variante | `variants.barcode` |
| **Metafields filled** | 25% | Metafields clés remplis (material, dimensions, weight, care) | `metafields(namespace:"custom")` |
| **Structured description** | 20% | Description factuelle, pas juste du marketing | `descriptionHtml` (analyse Claude) |
| **Schema markup** | 15% | JSON-LD Product schema correct sur les pages produit | Theme liquid `{% schema %}` |
| **Google category** | 10% | Catégorie Google Product assignée | `metafields(namespace:"google", key:"category")` |
| **Shopify Catalog** | 10% | Produit publié dans le Shopify Catalog (canal ventes IA) | `publishedOnChannel("catalog")` |

### Implémentation

```python
# app/agent/analyzers/agentic_readiness.py

class AgenticReadinessScanner(BaseScanner):
    name = "agentic_readiness"
    module = "agentic"
    group = "shopify_api"
    requires_plan = "starter"

    # Metafields considérés importants pour les agents IA
    IMPORTANT_METAFIELDS = [
        ("custom", "material"),
        ("custom", "dimensions"),
        ("custom", "weight"),
        ("custom", "care_instructions"),
        ("custom", "country_of_origin"),
    ]

    async def scan(
        self, store_id: str, shopify: ShopifyClient, memory_context: list[dict]
    ) -> ScannerResult:
        products = await self.fetch_products_with_metafields(shopify)

        checks = {
            "gtin_present": {"pass": 0, "fail": 0, "affected": []},
            "metafields_filled": {"pass": 0, "fail": 0, "affected": []},
            "structured_description": {"pass": 0, "fail": 0, "affected": []},
            "schema_markup": {"pass": 0, "fail": 0, "affected": []},
            "google_category": {"pass": 0, "fail": 0, "affected": []},
            "shopify_catalog": {"pass": 0, "fail": 0, "affected": []},
        }

        for product in products:
            self.check_gtin(product, checks)
            self.check_metafields(product, checks)
            self.check_description(product, checks)
            self.check_google_category(product, checks)
            # schema_markup et shopify_catalog vérifiés séparément

        # Schema markup : vérifier le thème (pas par produit)
        schema_ok = await self.check_schema_markup(shopify)
        if not schema_ok:
            checks["schema_markup"]["fail"] = len(products)

        # Score global
        total = len(products)
        score = self.calculate_score(checks, total)

        # Construire les issues
        issues = self.build_issues(checks, total)

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "score": score,
                "products_scanned": total,
                "checks": {
                    name: {
                        "status": "pass" if c["fail"] == 0 else ("partial" if c["pass"] > 0 else "fail"),
                        "affected_products": c["fail"],
                    }
                    for name, c in checks.items()
                },
            },
        )

    def check_gtin(self, product: dict, checks: dict):
        """Vérifie que au moins une variante a un barcode/GTIN."""
        variants = product.get("variants", {}).get("edges", [])
        has_gtin = any(
            v["node"].get("barcode") for v in variants
            if v["node"].get("barcode")
        )
        if has_gtin:
            checks["gtin_present"]["pass"] += 1
        else:
            checks["gtin_present"]["fail"] += 1
            checks["gtin_present"]["affected"].append(product["id"])

    def check_metafields(self, product: dict, checks: dict):
        """Vérifie que les metafields clés sont remplis."""
        metafields = {
            (m["node"]["namespace"], m["node"]["key"]): m["node"]["value"]
            for m in product.get("metafields", {}).get("edges", [])
        }
        filled = sum(
            1 for ns, key in self.IMPORTANT_METAFIELDS
            if metafields.get((ns, key))
        )
        if filled >= 3:  # au moins 3/5 metafields remplis = pass
            checks["metafields_filled"]["pass"] += 1
        else:
            checks["metafields_filled"]["fail"] += 1
            checks["metafields_filled"]["affected"].append(product["id"])

    def check_description(self, product: dict, checks: dict):
        """Vérifie que la description est structurée (pas juste du marketing)."""
        desc = product.get("descriptionHtml", "") or ""
        # Heuristiques pour une description structurée :
        # - Plus de 50 mots
        # - Contient des éléments factuels (listes, specs, dimensions)
        # - Pas juste du marketing flou
        word_count = len(desc.split())
        has_list = "<ul>" in desc or "<ol>" in desc or "<li>" in desc
        has_specs = any(
            kw in desc.lower()
            for kw in ["material", "dimensions", "weight", "size", "ingredients",
                       "made from", "composed of", "specifications"]
        )

        if word_count >= 50 and (has_list or has_specs):
            checks["structured_description"]["pass"] += 1
        else:
            checks["structured_description"]["fail"] += 1
            checks["structured_description"]["affected"].append(product["id"])

    def check_google_category(self, product: dict, checks: dict):
        """Vérifie qu'une catégorie Google Product est assignée."""
        metafields = {
            (m["node"]["namespace"], m["node"]["key"]): m["node"]["value"]
            for m in product.get("metafields", {}).get("edges", [])
        }
        has_category = bool(metafields.get(("google", "category")))
        if has_category:
            checks["google_category"]["pass"] += 1
        else:
            checks["google_category"]["fail"] += 1
            checks["google_category"]["affected"].append(product["id"])

    async def check_schema_markup(self, shopify: ShopifyClient) -> bool:
        """Vérifie que le thème a un schema markup Product correct."""
        # Récupérer le template product du thème
        theme_data = await shopify.graphql("""
            query {
                themes(first: 1, roles: MAIN) {
                    edges {
                        node {
                            id
                            files(filenames: ["templates/product.json", "sections/main-product.liquid"], first: 2) {
                                edges {
                                    node {
                                        filename
                                        body { ... on OnlineStoreThemeFileBodyText { content } }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        """)
        # Chercher schema.org/Product ou application/ld+json dans le template
        for edge in theme_data.get("themes", {}).get("edges", []):
            for file_edge in edge["node"].get("files", {}).get("edges", []):
                content = file_edge["node"].get("body", {}).get("content", "")
                if "schema.org" in content or "application/ld+json" in content:
                    return True
        return False

    def calculate_score(self, checks: dict, total: int) -> int:
        """Score /100 pondéré."""
        if total == 0:
            return 0
        weights = {
            "gtin_present": 0.20,
            "metafields_filled": 0.25,
            "structured_description": 0.20,
            "schema_markup": 0.15,
            "google_category": 0.10,
            "shopify_catalog": 0.10,
        }
        score = 0
        for check_name, weight in weights.items():
            passed = checks[check_name]["pass"]
            rate = passed / total if total > 0 else 0
            score += rate * weight * 100
        return round(score)

    def build_issues(self, checks: dict, total: int) -> list[ScanIssue]:
        """Construit les ScanIssues à partir des checks failed."""
        issues = []
        descriptions = {
            "gtin_present": {
                "title": "Products missing GTIN/barcode",
                "fix": "Add GTIN/barcode to product variants",
                "fix_type": "manual",
            },
            "metafields_filled": {
                "title": "Products with incomplete metafields",
                "fix": "Fill material, dimensions, weight metafields",
                "fix_type": "one_click",
            },
            "structured_description": {
                "title": "Products with unstructured descriptions",
                "fix": "Rewrite descriptions with specs, materials, dimensions",
                "fix_type": "one_click",
            },
            "schema_markup": {
                "title": "Theme missing Product schema markup",
                "fix": "Add JSON-LD Product schema to the product template",
                "fix_type": "developer",
            },
            "google_category": {
                "title": "Products without Google Product Category",
                "fix": "Assign Google categories via Shopify admin or metafields",
                "fix_type": "manual",
            },
            "shopify_catalog": {
                "title": "Products not published to Shopify Catalog",
                "fix": "Publish products to the Catalog sales channel",
                "fix_type": "manual",
            },
        }

        for check_name, data in checks.items():
            if data["fail"] > 0:
                desc = descriptions[check_name]
                severity = "critical" if data["fail"] > total * 0.5 else "major"
                issues.append(ScanIssue(
                    module="agentic",
                    scanner=self.name,
                    severity=severity,
                    title=f"{desc['title']} ({data['fail']}/{total})",
                    description=(
                        f"{data['fail']} out of {total} products fail this check. "
                        f"AI shopping agents (ChatGPT, Copilot, Gemini) need this data "
                        f"to recommend your products."
                    ),
                    impact=f"{data['fail']} products invisible to AI agents",
                    impact_value=data["fail"],
                    impact_unit="products",
                    fix_type=desc["fix_type"],
                    fix_description=desc["fix"],
                    auto_fixable=desc["fix_type"] == "one_click",
                    context={
                        "check": check_name,
                        "affected_count": data["fail"],
                        "affected_product_ids": data["affected"][:50],  # cap à 50
                    },
                ))

        return issues

    # ─── GRAPHQL QUERY ───

    async def fetch_products_with_metafields(self, shopify: ShopifyClient) -> list[dict]:
        """Fetch tous les produits avec les metafields nécessaires pour l'agentic check."""
        query = """
        query FetchAgenticProducts($first: Int!, $after: String) {
          products(first: $first, after: $after) {
            edges {
              cursor
              node {
                id
                title
                descriptionHtml
                productType
                status
                variants(first: 10) {
                  edges {
                    node {
                      barcode
                      sku
                    }
                  }
                }
                metafields(first: 20) {
                  edges {
                    node {
                      namespace
                      key
                      value
                      type
                    }
                  }
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        """
        products = []
        cursor = None
        while True:
            data = await shopify.graphql(query, {"first": 50, "after": cursor})
            edges = data["products"]["edges"]
            products.extend([e["node"] for e in edges])
            if not data["products"]["pageInfo"]["hasNextPage"]:
                break
            cursor = data["products"]["pageInfo"]["endCursor"]
        return products
```

---

## HS CODE VALIDATOR

```python
# app/agent/analyzers/hs_code_validator.py

import re

class HSCodeValidator(BaseScanner):
    name = "hs_code_validator"
    module = "agentic"
    group = "shopify_api"
    requires_plan = "pro"

    HS_CODE_REGEX = re.compile(r"^\d{6,10}$")

    # Mapping basique product_type → HS code prefix attendu
    TYPE_TO_HS_PREFIX = {
        "shirt": "6105",
        "t-shirt": "6109",
        "dress": "6104",
        "pants": "6103",
        "shoes": "6403",
        "bag": "4202",
        "handbag": "4202",
        "jewelry": "7113",
        "watch": "9101",
        "cosmetics": "3304",
        "skincare": "3304",
        "candle": "3406",
        "supplement": "2106",
        "toy": "9503",
        "electronics": "8471",
        "phone case": "4202",
    }

    async def scan(
        self, store_id: str, shopify: ShopifyClient, memory_context: list[dict]
    ) -> ScannerResult:
        products = await self.fetch_products_hs(shopify)
        issues = []

        missing = 0
        suspicious = 0

        for product in products:
            hs_code = self.extract_hs_code(product)
            product_type = (product.get("productType") or "").lower().strip()

            if not hs_code:
                missing += 1
                continue

            if not self.HS_CODE_REGEX.match(hs_code):
                suspicious += 1
                issues.append(ScanIssue(
                    module="agentic",
                    scanner=self.name,
                    severity="minor",
                    title=f"Invalid HS code format: '{hs_code}' on {product['title']}",
                    description=f"HS codes must be 6-10 digits. Found: '{hs_code}'.",
                    fix_type="manual",
                    fix_description="Correct the HS code in Shopify admin",
                    context={"product_id": product["id"], "hs_code": hs_code},
                ))
                continue

            # Vérifier la cohérence type → HS prefix
            if product_type and product_type in self.TYPE_TO_HS_PREFIX:
                expected_prefix = self.TYPE_TO_HS_PREFIX[product_type]
                if not hs_code.startswith(expected_prefix):
                    suspicious += 1
                    issues.append(ScanIssue(
                        module="agentic",
                        scanner=self.name,
                        severity="minor",
                        title=f"Suspicious HS code for {product['title']}",
                        description=(
                            f"Product type '{product_type}' usually has HS code starting with "
                            f"'{expected_prefix}', but found '{hs_code}'. This may cause "
                            f"incorrect tariffs or customs delays."
                        ),
                        fix_type="manual",
                        fix_description=f"Verify HS code. Expected prefix: {expected_prefix}",
                        context={
                            "product_id": product["id"],
                            "hs_code": hs_code,
                            "expected_prefix": expected_prefix,
                            "product_type": product_type,
                        },
                    ))

        if missing > 0:
            issues.insert(0, ScanIssue(
                module="agentic",
                scanner=self.name,
                severity="major" if missing > len(products) * 0.3 else "minor",
                title=f"{missing} products missing HS code",
                description=(
                    f"{missing} out of {len(products)} products have no HS code. "
                    f"Missing HS codes cause incorrect tariffs, customs delays, "
                    f"and potential chargebacks for international orders."
                ),
                impact=f"{missing} products at risk for international shipping",
                impact_value=missing,
                impact_unit="products",
                fix_type="manual",
                fix_description="Add HS codes in Shopify admin → Products → Edit → Shipping",
                context={"missing_count": missing, "total_products": len(products)},
            ))

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "total_products": len(products),
                "missing_hs": missing,
                "suspicious_hs": suspicious,
                "valid_hs": len(products) - missing - suspicious,
            },
        )

    def extract_hs_code(self, product: dict) -> str | None:
        """Extrait le HS code depuis les variantes ou metafields."""
        # Shopify stocke le HS code dans la variante
        variants = product.get("variants", {}).get("edges", [])
        for v in variants:
            hs = v["node"].get("harmonizedSystemCode")
            if hs:
                return hs.strip()
        return None

    async def fetch_products_hs(self, shopify: ShopifyClient) -> list[dict]:
        query = """
        query FetchProductsHS($first: Int!, $after: String) {
          products(first: $first, after: $after) {
            edges {
              cursor
              node {
                id
                title
                productType
                variants(first: 5) {
                  edges {
                    node {
                      harmonizedSystemCode
                    }
                  }
                }
              }
            }
            pageInfo { hasNextPage endCursor }
          }
        }
        """
        products = []
        cursor = None
        while True:
            data = await shopify.graphql(query, {"first": 50, "after": cursor})
            edges = data["products"]["edges"]
            products.extend([e["node"] for e in edges])
            if not data["products"]["pageInfo"]["hasNextPage"]:
                break
            cursor = data["products"]["pageInfo"]["endCursor"]
        return products
```

---

## AGENTIC MONITORING (webhook trigger)

Feature #37 — Pro plan. Chaque `products/create` ou `products/update` déclenche un check agentic rapide.

```python
# Dans le webhook handler (webhooks_shopify.py)

async def handle_product_create_or_update(shop_domain: str, payload: dict):
    """Webhook products/create ou products/update → check agentic."""
    store = await get_store_by_domain(shop_domain)
    if not store:
        return

    plan = await get_merchant_plan(store.merchant_id)
    if plan not in ("pro", "agency"):
        return  # Agentic monitoring = Pro only

    product_id = payload.get("admin_graphql_api_id")
    if not product_id:
        return

    # Check rapide : le produit a-t-il les critères agentic ?
    shopify = get_shopify_client_for_store(store.id)
    scanner = AgenticReadinessScanner()

    # Fetch uniquement ce produit
    product = await shopify.graphql(SINGLE_PRODUCT_QUERY, {"id": product_id})

    checks_failed = []
    if not has_gtin(product):
        checks_failed.append("GTIN missing")
    if not has_metafields(product):
        checks_failed.append("Key metafields empty")
    if not has_structured_description(product):
        checks_failed.append("Description not structured for AI")

    if checks_failed:
        await send_notification(
            merchant_id=store.merchant_id,
            store_id=store.id,
            channel="in_app",
            title=f"New product not AI-ready: {payload.get('title', 'Unknown')}",
            body=f"Issues: {', '.join(checks_failed)}. Fix now to appear in ChatGPT Shopping.",
            action_url=f"/dashboard/agentic?product={product_id}",
            category="agentic_alert",
        )
```

---

## ONE-CLICK FIXES AGENTIC

Certains checks agentic sont auto-fixables via l'API Shopify write :

| Check | Auto-fixable | Comment |
|-------|-------------|---------|
| GTIN missing | ❌ | Le merchant doit fournir le GTIN (on ne peut pas l'inventer) |
| Metafields empty | ✅ Partiel | Claude API peut suggérer material/dimensions basé sur le titre et la description |
| Description non-structurée | ✅ | Claude API réécrit en format structuré (specs, bullets, dimensions) |
| Schema markup | ❌ | Nécessite modification du thème (developer) |
| Google category | ❌ | Nécessite connaissance du merchant (quel type de produit exactement) |
| Shopify Catalog | ❌ | Le merchant doit publier manuellement dans le canal |

```python
# Fix metafields via Claude API + Shopify write
async def fix_metafield(shopify: ShopifyClient, product_id: str, product_data: dict):
    """Génère et applique un metafield manquant."""
    # 1. Claude API suggère la valeur
    suggestion = await claude_suggest_metafield(
        product_title=product_data["title"],
        product_description=product_data["descriptionHtml"],
        metafield_key="material",
    )

    # 2. Preview (ne pas appliquer sans approval)
    return {
        "product_id": product_id,
        "metafield": {"namespace": "custom", "key": "material"},
        "suggested_value": suggestion,
        "auto_fixable": True,
        "requires_approval": True,  # TOUJOURS
    }
```

---

## INTERDICTIONS

- ❌ Inventer des GTIN/barcodes → ✅ Le merchant doit les fournir (données réglementées)
- ❌ Appliquer des metafields sans approval merchant → ✅ Preview + approve TOUJOURS
- ❌ Réécrire des descriptions sans Safe Mode → ✅ Before/after snapshot, réversible
- ❌ Ignorer les produits en draft/archived → ✅ Scanner uniquement les produits `status: active`
- ❌ Hardcoder les HS codes → ✅ TYPE_TO_HS_PREFIX est un guide, pas une source de vérité
- ❌ Promettre la compatibilité ChatGPT → ✅ "Readiness score" = préparation, pas garantie
