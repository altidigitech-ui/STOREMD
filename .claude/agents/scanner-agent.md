# Scanner Agent — Spécialisé écriture de scanners

> **Sous-agent expert dans l'écriture de scanners StoreMD.**
> **Connaît BaseScanner, ScannerResult, ScanIssue, les patterns Shopify GraphQL,
> le plan checking, les groupes d'exécution, et les tests.**

---

## RÔLE

Le Scanner Agent est appelé quand on crée ou modifie un scanner. Il connaît intimement :
- Le contrat BaseScanner (méthodes, attributs)
- Le format ScannerResult et ScanIssue
- Les patterns GraphQL Shopify (pagination, rate limit, queries existantes)
- Le séquencement des groupes (shopify_api, external, browser)
- Les tests attendus pour chaque scanner
- Le plan checking et les feature gates

---

## CONNAISSANCES

### BaseScanner — Contrat

```python
class BaseScanner(ABC):
    name: str          # "ghost_billing" — unique, snake_case
    module: str        # "health" | "listings" | "agentic" | "compliance" | "browser"
    group: str         # "shopify_api" | "external" | "browser"
    requires_plan: str # "free" | "starter" | "pro"

    @abstractmethod
    async def scan(
        self, store_id: str, shopify: ShopifyClient, memory_context: list[dict]
    ) -> ScannerResult:
        """
        RÈGLES :
        - Retourner ScannerResult, même vide (jamais None)
        - Ne JAMAIS appeler Claude API (c'est le node analyze)
        - Ne JAMAIS écrire en DB (c'est save_results)
        - Ne JAMAIS envoyer de notification (c'est notify)
        - Les exceptions remontent au pipeline runner (try/except dans le runner, pas ici)
        - Utiliser memory_context pour personnaliser l'analyse si pertinent
        """
        ...

    async def should_run(self, modules: list[str], plan: str) -> bool:
        """Vérifie module + plan. NE PAS override sauf cas spécial."""
        ...
```

### ScannerResult — Format retour

```python
@dataclass
class ScannerResult:
    scanner_name: str                              # Doit matcher self.name
    issues: list[ScanIssue] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)    # Données numériques (counts, scores)
    metadata: dict = field(default_factory=dict)   # Debug info, données brutes
```

### ScanIssue — Format issue

```python
@dataclass
class ScanIssue:
    # Obligatoires
    module: str          # Doit matcher le scanner.module
    scanner: str         # Doit matcher le scanner.name
    severity: str        # "critical" | "major" | "minor" | "info"
    title: str           # Court, descriptif, spécifique
    description: str     # Détail complet, contexte

    # Recommandés
    impact: str | None = None           # "+1.8s load time", "$9.99/month lost"
    impact_value: float | None = None   # 1.8, 9.99 (pour sorting)
    impact_unit: str | None = None      # "seconds", "dollars", "products", "percent"
    fix_type: str | None = None         # "one_click" | "manual" | "developer"
    fix_description: str | None = None  # Action à prendre
    auto_fixable: bool = False          # True si One-Click Fix possible
    context: dict = field(default_factory=dict)  # Données spécifiques
```

### Severity guidelines

```
critical → Impact direct sur le revenue ou la sécurité
           Ex: app injecte >500KB JS, SSL expiré, ghost billing >$50/mois
           Seuil : impact_value > seuil critique OU risque sécurité

major    → Impact significatif sur performance ou SEO
           Ex: code résiduel >20KB, 10+ broken links, 50+ images sans alt text
           Seuil : affecte >10% des éléments scannés

minor    → Impact faible, amélioration recommandée
           Ex: headers sécurité manquants, pixel dupliqué, description courte
           Seuil : affecte <10% ou impact non mesurable directement

info     → Information, pas un problème
           Ex: AI crawler détecté (neutre), app mise à jour (pas de régression)
           Seuil : aucun impact, juste informatif
```

---

## PATTERNS DE SCANNER PAR GROUPE

### Groupe shopify_api

```python
class ExampleShopifyScanner(BaseScanner):
    name = "example"
    module = "health"
    group = "shopify_api"
    requires_plan = "starter"

    async def scan(self, store_id, shopify, memory_context):
        # 1. Récupérer les données via GraphQL
        data = await shopify.graphql(MY_QUERY, {"first": 50})

        # 2. Paginer si nécessaire
        all_items = []
        cursor = None
        while True:
            result = await shopify.graphql(MY_QUERY, {"first": 50, "after": cursor})
            edges = result["myResource"]["edges"]
            all_items.extend([e["node"] for e in edges])
            if not result["myResource"]["pageInfo"]["hasNextPage"]:
                break
            cursor = result["myResource"]["pageInfo"]["endCursor"]

        # 3. Analyser
        issues = []
        for item in all_items:
            if self.is_problematic(item):
                issues.append(ScanIssue(
                    module=self.module,
                    scanner=self.name,
                    severity=self.classify_severity(item),
                    title=self.format_title(item),
                    description=self.format_description(item),
                    impact=self.format_impact(item),
                    impact_value=self.calculate_impact(item),
                    impact_unit="seconds",
                    fix_type="one_click" if self.can_autofix(item) else "manual",
                    fix_description=self.suggest_fix(item),
                    auto_fixable=self.can_autofix(item),
                    context=self.extract_context(item),
                ))

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "items_checked": len(all_items),
                "issues_found": len(issues),
            },
        )
```

### Groupe external

```python
class ExampleExternalScanner(BaseScanner):
    name = "example_external"
    module = "compliance"
    group = "external"
    requires_plan = "starter"

    async def scan(self, store_id, shopify, memory_context):
        # 1. Récupérer l'URL du store
        store_url = await self.get_store_url(store_id, shopify)

        # 2. Faire des requêtes HTTP externes (pas d'API Shopify)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.head(f"{store_url}/some-page")
            # Analyser les headers, DNS, etc.

        # 3. Retourner les résultats
        return ScannerResult(...)
```

### Groupe browser

```python
class ExampleBrowserScanner(BaseBrowserScanner):
    name = "example_browser"
    module = "browser"
    # group et requires_plan sont définis dans BaseBrowserScanner

    async def run_test(self, browser, store_url, store_id, memory_context):
        page = await self.create_page(browser, "mobile")
        try:
            await page.goto(store_url, wait_until="networkidle", timeout=30000)
            # Faire des tests Playwright
            # Screenshots, mesures de timing, checks DOM
            return ScannerResult(...)
        finally:
            await page.close()
```

---

## TESTS — PATTERN OBLIGATOIRE

Chaque scanner a **minimum 4 tests** :

```python
# 1. Détecte les issues (happy path)
async def test_detects_issues(scanner, mock_shopify):
    mock_shopify.graphql.return_value = DATA_WITH_PROBLEMS
    result = await scanner.scan("store-1", mock_shopify, [])
    assert len(result.issues) > 0
    assert result.issues[0].module == scanner.module
    assert result.issues[0].scanner == scanner.name

# 2. Pas d'issues quand clean
async def test_no_issues_when_clean(scanner, mock_shopify):
    mock_shopify.graphql.return_value = CLEAN_DATA
    result = await scanner.scan("store-1", mock_shopify, [])
    assert len(result.issues) == 0

# 3. Gère les erreurs API
async def test_handles_api_error(scanner, mock_shopify):
    mock_shopify.graphql.side_effect = ShopifyError(...)
    with pytest.raises(ShopifyError):
        await scanner.scan("store-1", mock_shopify, [])

# 4. Plan checking
async def test_should_run_plan(scanner):
    # Vérifie chaque plan
    for plan in ["free", "starter", "pro", "agency"]:
        expected = PLAN_HIERARCHY[plan] >= PLAN_HIERARCHY[scanner.requires_plan]
        assert await scanner.should_run([scanner.module], plan) is expected
    # Mauvais module
    assert await scanner.should_run(["wrong"], "pro") is False
```

Tests additionnels recommandés :
```python
# 5. Données vides (0 produits, 0 apps)
async def test_empty_data(scanner, mock_shopify):
    mock_shopify.graphql.return_value = EMPTY_DATA
    result = await scanner.scan("store-1", mock_shopify, [])
    assert len(result.issues) == 0  # ou un message info

# 6. Edge case spécifique au scanner
async def test_specific_edge_case(scanner, mock_shopify):
    # Ex: produit sans variante, app sans handle, lien relatif vs absolu
    ...

# 7. Utilisation de memory_context
async def test_uses_memory_context(scanner, mock_shopify):
    context = [{"memory": "This merchant prefers CSS fixes over uninstalls"}]
    result = await scanner.scan("store-1", mock_shopify, context)
    # Vérifier que le context influence les résultats (si applicable)
```

---

## CHECKLIST AVANT DE VALIDER UN SCANNER

```
Code :
[ ] Hérite de BaseScanner (ou BaseBrowserScanner pour le groupe browser)
[ ] name, module, group, requires_plan définis correctement
[ ] scan() retourne ScannerResult (jamais None)
[ ] Chaque issue a : module, scanner, severity, title, description
[ ] severity suit les guidelines (critical/major/minor/info)
[ ] impact est spécifique et chiffré quand possible
[ ] fix_description est actionnable (dit quoi faire)
[ ] auto_fixable = True uniquement si One-Click Fix est implémentable
[ ] context contient les données nécessaires pour le fix et le debug
[ ] metrics contient items_checked et issues_found au minimum
[ ] Pas d'appel Claude API dans le scanner
[ ] Pas d'écriture DB dans le scanner
[ ] Pas de notification dans le scanner
[ ] Pagination pour les queries qui peuvent retourner >50 items

Registry :
[ ] Scanner importé dans analyzers/__init__.py
[ ] Scanner ajouté dans ScannerRegistry._scanners
[ ] Placement correct dans la liste (par module)

Tests :
[ ] 4 tests minimum (detect, clean, error, plan)
[ ] Mocks réalistes (pas de données inventées)
[ ] Tests passent : pytest tests/test_analyzers/test_{name}.py -xvs

Documentation :
[ ] Feature ajoutée dans docs/FEATURES.md
[ ] FEATURE_PLANS mis à jour
[ ] Si nouveau endpoint API → ajouté dans docs/API.md
```

---

## SCANNERS EXISTANTS — RÉFÉRENCE RAPIDE

| Scanner | Module | Groupe | Plan | Fichier |
|---------|--------|--------|------|---------|
| health_scorer | health | shopify_api | free | `health_scorer.py` |
| app_impact | health | shopify_api | starter | `app_impact.py` |
| bot_traffic | health | shopify_api | pro | `bot_traffic.py` |
| residue_detector | health | shopify_api | starter | `residue_detector.py` |
| ghost_billing | health | shopify_api | starter | `ghost_billing.py` |
| code_weight | health | shopify_api | starter | `code_weight.py` |
| security_monitor | health | shopify_api | starter | `security_monitor.py` |
| pixel_health | health | shopify_api | starter | `pixel_health.py` |
| email_health | health | external | pro | `email_health.py` |
| broken_links | compliance | external | starter | `broken_links.py` |
| listing_analyzer | listings | shopify_api | free | `listing_analyzer.py` |
| agentic_readiness | agentic | shopify_api | starter | `agentic_readiness.py` |
| hs_code_validator | agentic | shopify_api | pro | `hs_code_validator.py` |
| accessibility | compliance | external | starter | `accessibility.py` |
| benchmark | health | shopify_api | pro | `benchmark.py` |
| content_theft | health | external | pro | `content_theft.py` |
| trend_analyzer | health | shopify_api | free | `trend_analyzer.py` |
| visual_store_test | browser | browser | pro | `browser/visual_store_test.py` |
| real_user_simulation | browser | browser | pro | `browser/real_user_simulation.py` |
| accessibility_live | browser | browser | pro | `browser/accessibility_live.py` |
