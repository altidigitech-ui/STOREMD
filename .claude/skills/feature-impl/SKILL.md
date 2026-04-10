# Skill: Feature Implementation

> **Utilise ce skill CHAQUE FOIS que tu ajoutes une feature à StoreMD.**
> **Checklist end-to-end : DB → Scanner → Service → API → Frontend → Tests.**
> **Ne skip AUCUNE étape. L'ordre compte.**

---

## QUAND UTILISER

- Implémenter une nouvelle feature listée dans `docs/FEATURES.md`
- Ajouter un nouveau scanner au pipeline
- Créer un nouvel endpoint API avec son composant frontend
- Toute modification qui traverse plusieurs couches du stack

---

## ÉTAPE 0 — LIRE LES SPECS

Avant d'écrire une seule ligne de code :

1. Ouvrir `docs/FEATURES.md` → trouver la feature par son numéro (#1-#43)
2. Vérifier : **Plan** (free/starter/pro), **Phase** (M1/M2+), **Scanner**, **Endpoint**, **Composant**
3. Ouvrir `docs/DATABASE.md` → vérifier si les tables nécessaires existent
4. Ouvrir `context.md` → comprendre POURQUOI cette feature existe (quel problème merchant)

Si la feature n'est pas dans FEATURES.md → l'ajouter AVANT de coder.

---

## ÉTAPE 1 — DATABASE

### 1.1 Vérifier les tables existantes

La plupart des features utilisent les tables existantes (`scans`, `scan_issues`, `product_analyses`, etc.). Vérifier dans `docs/DATABASE.md`.

### 1.2 Si nouvelle table nécessaire

Créer une migration numérotée :

```sql
-- database/migrations/XXX_add_feature_name.sql

-- 1. Table
CREATE TABLE new_table (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    -- ... colonnes spécifiques
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Indexes
CREATE INDEX idx_new_table_store ON new_table(store_id);

-- 3. RLS (OBLIGATOIRE)
ALTER TABLE new_table ENABLE ROW LEVEL SECURITY;
CREATE POLICY "merchants_own_new_table" ON new_table
    FOR ALL USING (merchant_id = auth.uid());

-- 4. Trigger updated_at
CREATE TRIGGER new_table_updated_at BEFORE UPDATE ON new_table
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- 5. Reload schema
NOTIFY pgrst, 'reload schema';
```

### 1.3 Si nouvelle colonne sur table existante

```sql
-- database/migrations/XXX_add_column_to_table.sql

ALTER TABLE existing_table ADD COLUMN new_column TEXT;

-- Index si filtrage fréquent
CREATE INDEX idx_existing_new_column ON existing_table(new_column);

NOTIFY pgrst, 'reload schema';
```

### 1.4 Mettre à jour DATABASE.md

Après la migration, mettre à jour `docs/DATABASE.md` avec la nouvelle table/colonne. DATABASE.md est la source de vérité.

---

## ÉTAPE 2 — SCANNER (si feature = scan)

La majorité des features StoreMD sont des scanners. Suivre le pattern `BaseScanner`.

### 2.1 Créer le fichier scanner

```python
# app/agent/analyzers/new_scanner.py

from app.agent.analyzers.base import BaseScanner, ScannerResult
from app.models.scan import ScanIssue

class NewScanner(BaseScanner):
    name = "new_scanner"
    module = "health"              # ou "listings", "agentic", "compliance", "browser"
    group = "shopify_api"          # ou "external", "browser"
    requires_plan = "starter"      # ou "free", "pro"

    async def scan(
        self, store_id: str, shopify: ShopifyClient, memory_context: list[dict]
    ) -> ScannerResult:
        # 1. Récupérer les données (Shopify API, DNS, HTTP, etc.)
        data = await shopify.graphql(MY_QUERY)

        # 2. Analyser
        issues = []
        for item in data:
            if self.is_problematic(item):
                issues.append(ScanIssue(
                    module=self.module,
                    scanner=self.name,
                    severity="major",          # critical/major/minor/info
                    title="Short description",
                    description="Detailed explanation",
                    impact="+0.5s load time",
                    impact_value=0.5,
                    impact_unit="seconds",
                    fix_type="one_click",       # one_click/manual/developer
                    fix_description="How to fix this",
                    auto_fixable=True,
                    context={"relevant": "data"},
                ))

        # 3. Retourner les résultats
        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={"items_checked": len(data), "issues_found": len(issues)},
        )
```

### 2.2 Enregistrer dans le ScannerRegistry

```python
# app/agent/analyzers/__init__.py

from app.agent.analyzers.new_scanner import NewScanner

class ScannerRegistry:
    def __init__(self):
        self._scanners = [
            # ... scanners existants ...
            NewScanner(),    # ← AJOUTER ICI
        ]
```

### 2.3 Vérifier le groupe

| Si le scanner... | Groupe | Exécution |
|-----------------|--------|-----------|
| Appelle l'API Shopify | `shopify_api` | Parallèle, semaphore partagé |
| Fait des HTTP/DNS externes | `external` | Parallèle, pas de rate limit |
| Utilise Playwright | `browser` | Séquentiel, Pro only |

---

## ÉTAPE 3 — SERVICE

Si la feature a une logique métier au-delà du scan (ex: One-Click Fix, bulk operation) :

```python
# app/services/new_feature.py

class NewFeatureService:
    def __init__(self, supabase: SupabaseClient, shopify: ShopifyClient):
        self.supabase = supabase
        self.shopify = shopify

    async def execute(self, store_id: str, params: NewFeatureParams) -> NewFeatureResult:
        # 1. Vérifier les préconditions
        # 2. Exécuter la logique
        # 3. Persister le résultat
        # 4. Logger
        logger.info("new_feature_executed", store_id=store_id, result=result)
        return result
```

Ajouter le DI dans `app/dependencies.py` :

```python
async def get_new_feature_service(
    supabase: SupabaseClient = Depends(get_supabase),
    shopify: ShopifyClient = Depends(get_shopify_client),
) -> NewFeatureService:
    return NewFeatureService(supabase, shopify)
```

---

## ÉTAPE 4 — ENDPOINT API

### 4.1 Route

```python
# app/api/routes/relevant_module.py

from app.models.schemas import NewFeatureRequest, NewFeatureResponse

@router.get("/stores/{store_id}/new-feature")
async def get_new_feature(
    store_id: str,
    store: Store = Depends(get_current_store),
    service: NewFeatureService = Depends(get_new_feature_service),
):
    await check_plan_access(store.merchant_id, "new_feature")
    result = await service.get_results(store.id)
    return NewFeatureResponse.model_validate(result)
```

### 4.2 Schemas Pydantic

```python
# app/models/schemas.py

class NewFeatureResponse(BaseModel):
    items_count: int
    issues: list[IssueSchema]
    score: int | None = None

    model_config = ConfigDict(from_attributes=True)
```

### 4.3 Plan checking

```python
# Ajouter dans FEATURE_PLANS (app/config.py ou docs/FEATURES.md)
"new_feature": "starter",
```

---

## ÉTAPE 5 — FRONTEND

### 5.1 Types

```typescript
// types/new-feature.ts
export interface NewFeatureResult {
  items_count: number;
  issues: Issue[];
  score: number | null;
}
```

### 5.2 API client

```typescript
// lib/api.ts — ajouter la méthode
newFeature: {
  get: (storeId: string) => fetchApi<NewFeatureResult>(`/stores/${storeId}/new-feature`),
},
```

### 5.3 Hook

```typescript
// hooks/use-new-feature.ts
import useSWR from "swr";
import { api } from "@/lib/api";

export function useNewFeature(storeId: string) {
  return useSWR(
    storeId ? `/stores/${storeId}/new-feature` : null,
    () => api.newFeature.get(storeId),
  );
}
```

### 5.4 Composant

```tsx
// components/dashboard/NewFeature.tsx

interface NewFeatureProps {
  storeId: string;
}

export function NewFeature({ storeId }: NewFeatureProps) {
  const { data, isLoading, error } = useNewFeature(storeId);

  if (isLoading) return <Skeleton className="h-48" />;
  if (error) return <ErrorState message={error.message} />;
  if (!data) return null;

  return (
    <div>
      {/* Render results */}
    </div>
  );
}
```

### 5.5 Page (si nécessaire)

Intégrer dans l'onglet dashboard approprié :
- Module Health → `app/dashboard/health/page.tsx`
- Module Listings → `app/dashboard/listings/page.tsx`
- Module Agentic → `app/dashboard/agentic/page.tsx`
- Module Browser → `app/dashboard/browser/page.tsx`

---

## ÉTAPE 6 — TESTS

### 6.1 Test scanner (backend)

```python
# tests/test_analyzers/test_new_scanner.py

import pytest
from app.agent.analyzers.new_scanner import NewScanner
from tests.mocks.shopify_responses import MOCK_PRODUCTS

@pytest.fixture
def scanner():
    return NewScanner()

@pytest.fixture
def mock_shopify(mocker):
    client = mocker.AsyncMock()
    client.graphql.return_value = MOCK_PRODUCTS
    return client

@pytest.mark.asyncio
async def test_scan_detects_issues(scanner, mock_shopify):
    """Happy path : le scanner détecte les issues."""
    result = await scanner.scan("store-123", mock_shopify, [])
    assert len(result.issues) > 0
    assert result.issues[0].severity in ("critical", "major", "minor", "info")
    assert result.issues[0].module == scanner.module

@pytest.mark.asyncio
async def test_scan_no_issues(scanner, mock_shopify):
    """Cas nominal : pas de problème détecté."""
    mock_shopify.graphql.return_value = CLEAN_DATA
    result = await scanner.scan("store-123", mock_shopify, [])
    assert len(result.issues) == 0

@pytest.mark.asyncio
async def test_scan_shopify_error(scanner, mock_shopify):
    """Error case : Shopify API échoue."""
    mock_shopify.graphql.side_effect = ShopifyError(
        code=ErrorCode.SHOPIFY_API_UNAVAILABLE,
        message="Shopify down",
        status_code=503,
    )
    with pytest.raises(ShopifyError):
        await scanner.scan("store-123", mock_shopify, [])

@pytest.mark.asyncio
async def test_should_run_plan_check(scanner):
    """Vérifier que should_run respecte le plan."""
    assert await scanner.should_run(["health"], "pro") is True
    assert await scanner.should_run(["health"], "free") is (scanner.requires_plan == "free")
    assert await scanner.should_run(["listings"], "pro") is (scanner.module == "listings")
```

### 6.2 Test endpoint (backend)

```python
# tests/test_api/test_new_feature.py

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_new_feature_success(client: AsyncClient, auth_headers):
    response = await client.get(
        "/api/v1/stores/store-123/new-feature",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items_count" in data
    assert "issues" in data

@pytest.mark.asyncio
async def test_get_new_feature_plan_required(client: AsyncClient, free_plan_headers):
    response = await client.get(
        "/api/v1/stores/store-123/new-feature",
        headers=free_plan_headers,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTH_PLAN_REQUIRED"
```

---

## ÉTAPE 7 — VÉRIFICATION FINALE

Checklist avant de considérer la feature comme "done" :

```
[ ] Feature spec dans docs/FEATURES.md (plan, scanner, endpoint, composant)
[ ] Migration DB créée (si nécessaire) + RLS + indexes + NOTIFY pgrst
[ ] docs/DATABASE.md mis à jour (si nouvelle table/colonne)
[ ] Scanner créé + enregistré dans ScannerRegistry
[ ] Service créé (si logique métier complexe)
[ ] Endpoint API créé avec Pydantic schemas
[ ] Plan checking dans l'endpoint
[ ] Frontend : types + API client + hook + composant
[ ] Composant intégré dans la bonne page dashboard
[ ] Test scanner : happy path + no issues + error case
[ ] Test endpoint : success + plan required
[ ] Logging structlog dans le service/scanner
[ ] Pas de `any` en TypeScript
[ ] Pas de `HTTPException` directe (AppError)
[ ] Pas de secret dans les logs
```

---

## RACCOURCIS

| Si la feature est... | Skip ces étapes |
|---------------------|----------------|
| Un scanner simple (données dans scan_issues) | Étape 1 (DB existe), Étape 3 (pas de service custom) |
| Un endpoint read-only (GET) | Étape 1 (pas de nouvelle table) |
| Backend only (webhook handler) | Étape 5 (pas de frontend) |
| Frontend only (UI change) | Étapes 1-4 (pas de backend) |

Mais JAMAIS skip les tests (Étape 6) ni la vérification finale (Étape 7).
