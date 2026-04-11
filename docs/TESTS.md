# TESTS.md — Stratégie de Tests StoreMD

> **pytest (backend) + vitest (frontend) + Playwright (E2E).**
> **Chaque scanner, endpoint, service a des tests. Pas d'exception.**
> **Pour les tests E2E Playwright, voir `.claude/skills/playwright-testing/SKILL.md`.**

---

## PYRAMIDE DE TESTS

```
        ┌───────┐
        │  E2E  │          Playwright — parcours utilisateur complets
        │  (~5) │          Lents (~30s), fragiles, peu nombreux
        ├───────┤
        │ Integ │          pytest — endpoints API avec DB réelle (test DB)
        │ (~30) │          Moyens (~5s), testent le wiring
        ├───────┤
        │ Unit  │          pytest + vitest — scanners, services, composants
        │(~100) │          Rapides (<1s), isolés, mocks
        └───────┘
```

| Type | Outil | Scope | Vitesse | Quantité |
|------|-------|-------|---------|----------|
| Unit backend | pytest + pytest-asyncio | Scanners, services, utils | <1s/test | ~60 |
| Unit frontend | vitest + React Testing Library | Composants, hooks, utils | <1s/test | ~40 |
| Integration | pytest + httpx | Endpoints API, DB, auth | ~5s/test | ~30 |
| E2E | Playwright | Onboarding, dashboard, billing | ~30s/test | ~5 |

---

## BACKEND — PYTEST

### Setup

```bash
# backend/pyproject.toml

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
filterwarnings = ["ignore::DeprecationWarning"]
env_file = ".env.test"

[tool.pytest]
markers = [
    "unit: Unit tests (fast, no DB)",
    "integration: Integration tests (DB required)",
    "slow: Slow tests (browser, external APIs)",
]
```

```bash
# backend/.env.test

APP_ENV=test
SUPABASE_URL=http://localhost:54321           # Local Supabase (supabase start)
SUPABASE_ANON_KEY=eyJ...test
SUPABASE_SERVICE_ROLE_KEY=eyJ...test
REDIS_URL=redis://localhost:6379/1            # DB 1 pour les tests (DB 0 = dev)
SHOPIFY_API_KEY=test_key
SHOPIFY_API_SECRET=test_secret
SHOPIFY_API_VERSION=2026-01
ANTHROPIC_API_KEY=test_key                    # Mocké, jamais appelé
FERNET_KEY=test_fernet_key_32_bytes_long_xxx=
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_test_xxx
```

### Conftest

```python
# tests/conftest.py

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings

@pytest_asyncio.fixture
async def client():
    """Client HTTP pour tester les endpoints API."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def auth_headers():
    """Headers avec un JWT valide pour les tests."""
    return {"Authorization": f"Bearer {create_test_jwt('merchant-uuid-1')}"}

@pytest.fixture
def free_plan_headers():
    """Headers pour un merchant avec le plan Free."""
    return {"Authorization": f"Bearer {create_test_jwt('merchant-free-uuid')}"}

@pytest.fixture
def pro_plan_headers():
    """Headers pour un merchant avec le plan Pro."""
    return {"Authorization": f"Bearer {create_test_jwt('merchant-pro-uuid')}"}

@pytest.fixture
def mock_shopify(mocker):
    """Mock du ShopifyClient — pas d'appel API réel."""
    client = mocker.AsyncMock()
    client.shop_domain = "teststore.myshopify.com"
    return client

@pytest.fixture
def mock_claude(mocker):
    """Mock de Claude API — réponse prédéfinie."""
    mock = mocker.patch("app.services.claude.client.messages.create")
    mock.return_value = mocker.Mock(
        content=[mocker.Mock(text='{"score": 72, "trend": "up", "top_issues": []}')]
    )
    return mock

@pytest.fixture
def mock_memory(mocker):
    """Mock de StoreMemory — pas d'appel Mem0 réel."""
    memory = mocker.AsyncMock()
    memory.recall_merchant.return_value = []
    memory.recall_store.return_value = []
    memory.recall_cross_store.return_value = []
    memory.recall_for_scan.return_value = {
        "merchant": [], "store": [], "cross_store": []
    }
    return memory


def create_test_jwt(merchant_id: str) -> str:
    """Crée un JWT de test valide pour Supabase."""
    import jwt
    payload = {
        "sub": merchant_id,
        "role": "authenticated",
        "exp": 9999999999,
        "aud": "authenticated",
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
```

### Mocks — Shopify responses

```python
# tests/mocks/shopify_responses.py

MOCK_SHOP_DATA = {
    "shop": {
        "name": "Test Store",
        "primaryDomain": {"url": "https://teststore.com", "host": "teststore.com"},
        "plan": {"displayName": "Shopify"},
        "currencyCode": "USD",
        "billingAddress": {"countryCodeV2": "US"},
        "productsCount": {"count": 50},
    }
}

MOCK_APPS_DATA = {
    "appInstallations": {
        "totalCount": 5,
        "edges": [
            {
                "node": {
                    "app": {
                        "id": "gid://shopify/App/1",
                        "title": "Privy",
                        "handle": "privy",
                        "developerName": "Privy Inc",
                    },
                    "accessScopes": [{"handle": "read_products"}, {"handle": "write_script_tags"}],
                }
            },
            {
                "node": {
                    "app": {
                        "id": "gid://shopify/App/2",
                        "title": "Klaviyo",
                        "handle": "klaviyo",
                        "developerName": "Klaviyo Inc",
                    },
                    "accessScopes": [{"handle": "read_products"}, {"handle": "read_customers"}],
                }
            },
        ],
    }
}

MOCK_PRODUCTS_DATA = {
    "products": {
        "edges": [
            {
                "cursor": "cursor1",
                "node": {
                    "id": "gid://shopify/Product/123",
                    "title": "Organic Face Cream",
                    "handle": "organic-face-cream",
                    "status": "ACTIVE",
                    "productType": "skincare",
                    "descriptionHtml": "<p>Nice cream.</p>",
                    "seo": {"title": None, "description": None},
                    "images": {
                        "edges": [
                            {"node": {"id": "img1", "altText": None, "url": "https://...", "width": 800, "height": 800}},
                            {"node": {"id": "img2", "altText": "Face cream", "url": "https://...", "width": 800, "height": 800}},
                        ]
                    },
                    "variants": {
                        "edges": [
                            {"node": {"id": "var1", "title": "Default", "sku": "FC001", "barcode": None, "price": "29.99", "inventoryQuantity": 42}},
                        ]
                    },
                    "metafields": {"edges": []},
                }
            },
        ],
        "pageInfo": {"hasNextPage": False, "endCursor": "cursor1"},
    }
}

MOCK_THEME_DATA = {
    "themes": {
        "edges": [
            {
                "node": {
                    "id": "gid://shopify/Theme/1",
                    "name": "Dawn",
                    "role": "MAIN",
                }
            }
        ]
    }
}

MOCK_SCRIPT_TAGS = {
    "scriptTags": {
        "edges": [
            {"node": {"id": "st1", "src": "https://privy.com/widget.js", "displayScope": "ALL"}},
            {"node": {"id": "st2", "src": "https://old-app.com/legacy.js", "displayScope": "ALL"}},
        ]
    }
}

MOCK_RECURRING_CHARGES = {
    "recurring_application_charges": [
        {"id": 1, "name": "Old SEO App", "status": "active", "price": "9.99", "created_at": "2025-11-01T00:00:00Z"},
    ]
}
```

### Mocks — Claude responses

```python
# tests/mocks/claude_responses.py

MOCK_ANALYSIS_RESPONSE = '''{
    "score": 67,
    "mobile_score": 52,
    "desktop_score": 81,
    "trend": "up",
    "summary": "Your store health has improved. 3 issues remain.",
    "top_issues": [
        {
            "title": "App Privy injects 340KB of unminified JS",
            "severity": "critical",
            "impact": "+1.8s load time",
            "impact_value": 1.8,
            "impact_unit": "seconds",
            "scanner": "app_impact",
            "recommendation": "Replace Privy with a lighter alternative",
            "fix_type": "manual",
            "alternative": null
        }
    ]
}'''

MOCK_FIX_RESPONSE = '''{
    "fix_description": "Remove the residual code left by the uninstalled app",
    "fix_type": "one_click",
    "estimated_impact": "Save 0.6 seconds of load time",
    "steps": null,
    "auto_fixable": true
}'''
```

---

## TESTS PAR CATÉGORIE

### 1. Tests scanners (unit)

Chaque scanner a au minimum 3 tests :

```python
# tests/test_analyzers/test_ghost_billing.py

import pytest
from app.agent.analyzers.ghost_billing import GhostBillingDetector
from tests.mocks.shopify_responses import MOCK_APPS_DATA, MOCK_RECURRING_CHARGES

@pytest.fixture
def scanner():
    return GhostBillingDetector()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detects_ghost_billing(scanner, mock_shopify):
    """Happy path : détecte une app qui facture sans être installée."""
    mock_shopify.graphql.return_value = MOCK_APPS_DATA
    mock_shopify.rest_get.return_value = MOCK_RECURRING_CHARGES

    result = await scanner.scan("store-1", mock_shopify, [])

    assert len(result.issues) == 1
    assert result.issues[0].scanner == "ghost_billing"
    assert result.issues[0].severity == "major"
    assert "Old SEO App" in result.issues[0].title
    assert result.metrics["ghost_charges"] == 1
    assert result.metrics["total_ghost_monthly"] == 9.99


@pytest.mark.unit
@pytest.mark.asyncio
async def test_no_ghosts(scanner, mock_shopify):
    """Pas de ghost billing — toutes les charges correspondent à des apps installées."""
    mock_shopify.graphql.return_value = MOCK_APPS_DATA
    mock_shopify.rest_get.return_value = {
        "recurring_application_charges": [
            {"id": 1, "name": "Privy", "status": "active", "price": "29.99", "created_at": "2026-01-01T00:00:00Z"},
        ]
    }

    result = await scanner.scan("store-1", mock_shopify, [])

    assert len(result.issues) == 0
    assert result.metrics["ghost_charges"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shopify_api_error(scanner, mock_shopify):
    """Shopify API échoue — le scanner raise ShopifyError."""
    from app.core.exceptions import ShopifyError, ErrorCode

    mock_shopify.graphql.side_effect = ShopifyError(
        code=ErrorCode.SHOPIFY_API_UNAVAILABLE,
        message="Shopify down",
        status_code=503,
    )

    with pytest.raises(ShopifyError):
        await scanner.scan("store-1", mock_shopify, [])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_should_run_plan(scanner):
    """Vérifie should_run selon le plan et le module."""
    assert await scanner.should_run(["health"], "starter") is True
    assert await scanner.should_run(["health"], "pro") is True
    assert await scanner.should_run(["health"], "free") is False  # requires starter
    assert await scanner.should_run(["listings"], "pro") is False  # wrong module
```

### Pattern pour chaque scanner

```
test_{scanner}_detects_issues          → Happy path, issues trouvées
test_{scanner}_no_issues               → Clean, pas de problème
test_{scanner}_shopify_error           → API Shopify échoue
test_{scanner}_should_run_plan         → Plan checking
test_{scanner}_empty_data              → Store sans données (0 produits, 0 apps)
test_{scanner}_edge_case               → Cas spécifique au scanner
```

### 2. Tests endpoints API (integration)

```python
# tests/test_api/test_scans.py

import pytest
from httpx import AsyncClient

@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_scan_success(client: AsyncClient, auth_headers):
    """POST /scans — créer un scan avec succès."""
    response = await client.post(
        "/api/v1/stores/store-1/scans",
        json={"modules": ["health"]},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["modules"] == ["health"]
    assert "id" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_scan_plan_required(client: AsyncClient, free_plan_headers):
    """POST /scans avec module browser — plan Free → 403."""
    response = await client.post(
        "/api/v1/stores/store-1/scans",
        json={"modules": ["browser"]},
        headers=free_plan_headers,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTH_PLAN_REQUIRED"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_scan_invalid_module(client: AsyncClient, auth_headers):
    """POST /scans avec module invalide → 422."""
    response = await client.post(
        "/api/v1/stores/store-1/scans",
        json={"modules": ["invalid_module"]},
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_scan_no_auth(client: AsyncClient):
    """POST /scans sans JWT → 401."""
    response = await client.post(
        "/api/v1/stores/store-1/scans",
        json={"modules": ["health"]},
    )
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_health_score(client: AsyncClient, auth_headers):
    """GET /health — retourne le score actuel."""
    response = await client.get(
        "/api/v1/stores/store-1/health",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "score" in data
    assert "mobile_score" in data
    assert "trend" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_scan_not_found(client: AsyncClient, auth_headers):
    """GET /scans/{id} — scan inexistant → 404."""
    response = await client.get(
        "/api/v1/stores/store-1/scans/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert response.status_code == 404
```

### Pattern pour chaque endpoint

```
test_{endpoint}_success                → 200/201, données correctes
test_{endpoint}_plan_required          → 403 avec plan insuffisant
test_{endpoint}_no_auth                → 401 sans JWT
test_{endpoint}_not_found              → 404 ressource inexistante
test_{endpoint}_validation_error       → 422 input invalide
test_{endpoint}_store_access_denied    → 404 store d'un autre merchant
```

### 3. Tests services (unit)

```python
# tests/test_services/test_billing.py

import pytest
from app.services.stripe_billing import StripeBillingService

@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_plan_access_pro_feature(mock_supabase):
    """Pro feature accessible avec plan Pro."""
    billing = StripeBillingService(mock_supabase)
    mock_supabase.table("merchants").select().eq().single().execute.return_value.data = {
        "id": "merchant-1", "plan": "pro"
    }
    assert await billing.check_plan_access("merchant-1", "visual_store_test") is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_plan_access_denied(mock_supabase):
    """Pro feature inaccessible avec plan Free."""
    billing = StripeBillingService(mock_supabase)
    mock_supabase.table("merchants").select().eq().single().execute.return_value.data = {
        "id": "merchant-1", "plan": "free"
    }
    assert await billing.check_plan_access("merchant-1", "visual_store_test") is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_usage_limit_exceeded(mock_supabase):
    """Increment usage au-delà de la limite."""
    billing = StripeBillingService(mock_supabase)
    result = await billing.increment_usage("merchant-1", "store-1", "scan")
    assert "exceeded" in result
```

### 4. Tests webhooks (integration)

```python
# tests/test_api/test_webhooks.py

import hmac
import hashlib
import base64
import json
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_shopify_webhook_valid_hmac(client: AsyncClient):
    """Webhook Shopify avec HMAC valide → 200."""
    payload = json.dumps({"id": 123}).encode()
    computed_hmac = base64.b64encode(
        hmac.new(b"test_secret", payload, hashlib.sha256).digest()
    ).decode()

    response = await client.post(
        "/api/v1/webhooks/shopify",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Hmac-Sha256": computed_hmac,
            "X-Shopify-Topic": "products/create",
            "X-Shopify-Shop-Domain": "teststore.myshopify.com",
            "X-Shopify-Webhook-Id": "webhook-1",
        },
    )
    assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_shopify_webhook_invalid_hmac(client: AsyncClient):
    """Webhook Shopify avec HMAC invalide → 401."""
    response = await client.post(
        "/api/v1/webhooks/shopify",
        content=b'{"id": 123}',
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Hmac-Sha256": "invalid_hmac",
            "X-Shopify-Topic": "products/create",
            "X-Shopify-Shop-Domain": "teststore.myshopify.com",
            "X-Shopify-Webhook-Id": "webhook-2",
        },
    )
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_shopify_webhook_idempotency(client: AsyncClient):
    """Même webhook envoyé 2 fois → deuxième retourne already_processed."""
    payload = json.dumps({"id": 456}).encode()
    computed_hmac = base64.b64encode(
        hmac.new(b"test_secret", payload, hashlib.sha256).digest()
    ).decode()
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Hmac-Sha256": computed_hmac,
        "X-Shopify-Topic": "products/create",
        "X-Shopify-Shop-Domain": "teststore.myshopify.com",
        "X-Shopify-Webhook-Id": "webhook-3",
    }

    # Premier appel
    r1 = await client.post("/api/v1/webhooks/shopify", content=payload, headers=headers)
    assert r1.status_code == 200
    assert r1.json()["status"] == "accepted"

    # Deuxième appel (même webhook_id)
    r2 = await client.post("/api/v1/webhooks/shopify", content=payload, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["status"] == "already_processed"
```

### 5. Tests agent (unit)

```python
# tests/test_agent/test_orchestrator.py

import pytest
from app.agent.orchestrator import ScanOrchestrator
from app.agent.state import AgentState

@pytest.mark.unit
@pytest.mark.asyncio
async def test_full_scan_pipeline(mock_shopify, mock_memory, mock_claude):
    """Test le pipeline complet : detect → analyze → act → save."""
    orchestrator = ScanOrchestrator(
        memory=mock_memory,
        shopify=mock_shopify,
        supabase=mock_supabase,
    )
    graph = orchestrator.build_graph()
    result = await graph.ainvoke(AgentState(
        store_id="store-1",
        merchant_id="merchant-1",
        scan_id="scan-1",
        modules=["health"],
        trigger="manual",
    ))

    assert result.score > 0
    assert result.scan_id == "scan-1"
    assert mock_memory.recall_for_scan.called
    assert mock_claude.called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_continues_on_scanner_failure(mock_shopify, mock_memory):
    """Un scanner qui échoue ne bloque pas les autres."""
    # Faire échouer un scanner spécifique
    mock_shopify.graphql.side_effect = [
        Exception("Scanner 1 failed"),  # Premier appel échoue
        MOCK_APPS_DATA,                 # Les suivants réussissent
        MOCK_PRODUCTS_DATA,
    ]

    orchestrator = ScanOrchestrator(memory=mock_memory, shopify=mock_shopify, supabase=mock_supabase)
    graph = orchestrator.build_graph()
    result = await graph.ainvoke(AgentState(
        store_id="store-1", merchant_id="merchant-1",
        scan_id="scan-1", modules=["health"], trigger="manual",
    ))

    # Le scan a continué malgré l'échec d'un scanner
    assert len(result.errors) > 0
    assert len(result.scanner_results) > 0  # D'autres scanners ont réussi


# tests/test_agent/test_learner.py

@pytest.mark.unit
@pytest.mark.asyncio
async def test_feedback_stored_in_memory(mock_memory):
    """Le feedback merchant est stocké dans Mem0."""
    learner = OuroborosLearner(memory=mock_memory)
    await learner.process_feedback(
        merchant_id="merchant-1",
        issue_id="issue-1",
        accepted=False,
        reason="I need this app",
        reason_category="disagree",
    )
    assert mock_memory.remember_merchant.called
    call_args = mock_memory.remember_merchant.call_args
    assert "REJECTED" in call_args[0][1]
    assert "disagree" in call_args[0][1] or "I need this app" in call_args[0][1]
```

---

## FRONTEND — VITEST

### Setup

```typescript
// frontend/vitest.config.ts

import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    globals: true,
    css: false,
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

```typescript
// frontend/tests/setup.ts

import "@testing-library/jest-dom";

// Mock fetch
global.fetch = vi.fn();

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/dashboard",
  useSearchParams: () => new URLSearchParams(),
}));
```

### Tests composants

```typescript
// tests/components/ScoreHero.test.tsx

import { render, screen } from "@testing-library/react";
import { ScoreHero } from "@/components/dashboard/ScoreHero";

describe("ScoreHero", () => {
  it("displays the score", () => {
    render(
      <ScoreHero score={67} mobileScore={52} desktopScore={81}
                 trend="up" trendDelta={9} lastScanAt="2026-04-09T10:00:00Z" />
    );
    expect(screen.getByTestId("health-score")).toHaveTextContent("67");
  });

  it("shows positive trend", () => {
    render(
      <ScoreHero score={67} mobileScore={52} desktopScore={81}
                 trend="up" trendDelta={9} lastScanAt="2026-04-09T10:00:00Z" />
    );
    expect(screen.getByText(/\+9/)).toBeInTheDocument();
  });

  it("shows negative trend", () => {
    render(
      <ScoreHero score={58} mobileScore={43} desktopScore={72}
                 trend="down" trendDelta={-5} lastScanAt="2026-04-09T10:00:00Z" />
    );
    expect(screen.getByText(/-5/)).toBeInTheDocument();
  });

  it("applies correct color for low score", () => {
    render(
      <ScoreHero score={25} mobileScore={20} desktopScore={30}
                 trend="down" trendDelta={-10} lastScanAt="2026-04-09T10:00:00Z" />
    );
    const scoreEl = screen.getByTestId("health-score");
    expect(scoreEl.className).toContain("text-orange");
  });
});
```

```typescript
// tests/components/IssueCard.test.tsx

import { render, screen, fireEvent } from "@testing-library/react";
import { IssueCard } from "@/components/dashboard/IssueCard";

const mockIssue = {
  id: "issue-1",
  module: "health",
  scanner: "app_impact",
  severity: "critical" as const,
  title: "App Privy injects 340KB",
  description: "...",
  impact: "+1.8s load time",
  fix_type: "manual" as const,
  fix_description: "Replace with lighter alternative",
  auto_fixable: false,
};

describe("IssueCard", () => {
  it("renders issue title and impact", () => {
    render(<IssueCard issue={mockIssue} onFix={vi.fn()} onDismiss={vi.fn()} />);
    expect(screen.getByText("App Privy injects 340KB")).toBeInTheDocument();
    expect(screen.getByText(/1\.8s/)).toBeInTheDocument();
  });

  it("shows severity badge", () => {
    render(<IssueCard issue={mockIssue} onFix={vi.fn()} onDismiss={vi.fn()} />);
    expect(screen.getByText("critical")).toBeInTheDocument();
  });

  it("calls onDismiss when dismiss clicked", () => {
    const onDismiss = vi.fn();
    render(<IssueCard issue={mockIssue} onFix={vi.fn()} onDismiss={onDismiss} />);
    fireEvent.click(screen.getByText("Dismiss"));
    expect(onDismiss).toHaveBeenCalledWith("issue-1");
  });

  it("shows fix button only when auto_fixable", () => {
    const fixableIssue = { ...mockIssue, auto_fixable: true };
    render(<IssueCard issue={fixableIssue} onFix={vi.fn()} onDismiss={vi.fn()} />);
    expect(screen.getByText("Fix →")).toBeInTheDocument();
  });
});
```

### Tests hooks

```typescript
// tests/hooks/use-scan.test.ts

import { renderHook, waitFor } from "@testing-library/react";
import { useScan } from "@/hooks/use-scan";

describe("useScan", () => {
  it("fetches scan data", async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ score: 67, issues: [] }),
    });

    const { result } = renderHook(() => useScan("scan-1"));

    await waitFor(() => {
      expect(result.current.data).toBeDefined();
      expect(result.current.data?.score).toBe(67);
    });
  });

  it("handles error", async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: false,
      json: () => Promise.resolve({ error: { code: "SCAN_NOT_FOUND", message: "Not found" } }),
    });

    const { result } = renderHook(() => useScan("invalid-id"));

    await waitFor(() => {
      expect(result.current.error).toBeDefined();
    });
  });
});
```

---

## EXÉCUTION

### Commandes

```bash
# === Backend ===

# Tous les tests
cd backend && pytest

# Tests unitaires seulement (rapide)
pytest -m unit

# Tests intégration (nécessite DB + Redis)
pytest -m integration

# Un fichier
pytest tests/test_analyzers/test_ghost_billing.py

# Un test
pytest tests/test_analyzers/test_ghost_billing.py::test_detects_ghost_billing

# Verbose + stop au premier échec
pytest -xvs

# Coverage
pytest --cov=app --cov-report=html

# === Frontend ===

# Tous les tests
cd frontend && npm test

# Watch mode
npm test -- --watch

# Coverage
npm test -- --coverage

# Un fichier
npm test -- tests/components/ScoreHero.test.tsx

# === E2E ===

# Tous les tests Playwright
cd frontend && npx playwright test

# Headed (voir le browser)
npx playwright test --headed

# Un fichier
npx playwright test tests/e2e/onboarding.spec.ts
```

### CI (GitHub Actions)

```yaml
# .github/workflows/test.yml

name: Tests

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7
        ports: [6379:6379]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: cd backend && pip install -r requirements.txt
      - run: cd backend && pip install pytest pytest-asyncio pytest-cov
      - run: cd backend && pytest -m "unit or integration" --cov=app
        env:
          APP_ENV: test
          REDIS_URL: redis://localhost:6379/1

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: cd frontend && npm ci
      - run: cd frontend && npm test -- --coverage
```

---

## CONVENTIONS

### Nommage fichiers test

```
Backend :
  tests/test_analyzers/test_{scanner_name}.py
  tests/test_api/test_{route_module}.py
  tests/test_services/test_{service_name}.py
  tests/test_agent/test_{component}.py

Frontend :
  tests/components/{ComponentName}.test.tsx
  tests/hooks/{hook-name}.test.ts
  tests/lib/{module}.test.ts
  tests/e2e/{flow}.spec.ts
```

### Nommage tests

```python
# Backend — descriptif, snake_case
def test_detects_ghost_billing()
def test_no_issues_when_clean()
def test_returns_403_when_plan_insufficient()
def test_feedback_stored_in_memory()
```

```typescript
// Frontend — descriptif, sentence case
it("displays the score")
it("shows fix button only when auto_fixable")
it("handles error state")
```

### Markers pytest

```
@pytest.mark.unit          → Pas de DB, pas de network, mocks only
@pytest.mark.integration   → DB + Redis nécessaires
@pytest.mark.slow          → >10s (Playwright, gros datasets)
```

---

## INTERDICTIONS

- ❌ Code sans tests → ✅ Chaque scanner, endpoint, service a des tests
- ❌ Tests qui appellent les APIs réelles (Shopify, Claude, Stripe) → ✅ Mocks
- ❌ Tests qui dépendent de l'ordre d'exécution → ✅ Chaque test est indépendant
- ❌ Tests flaky (passent parfois, échouent parfois) → ✅ Fixer ou supprimer
- ❌ `time.sleep()` dans les tests → ✅ `pytest-asyncio` + async mocks
- ❌ Données de production dans les tests → ✅ Fixtures et mocks
- ❌ Tests qui modifient la DB sans cleanup → ✅ Transaction rollback ou DB test isolée
- ❌ Skip un test sans justification → ✅ `@pytest.mark.skip(reason="...")` avec raison
