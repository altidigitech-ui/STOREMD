# Skill: Playwright Testing

> **Utilise ce skill pour écrire des tests E2E de l'app StoreMD avec Playwright.**
> **Ce skill concerne les tests de NOTRE app. Pour les scanners browser sur les stores
> des merchants, voir `.claude/skills/browser-automation/SKILL.md`.**

---

## QUAND UTILISER

- Écrire des tests E2E pour le frontend StoreMD (onboarding, dashboard, settings)
- Tester le flow OAuth Shopify en staging
- Tester l'upgrade flow (Stripe Checkout)
- Vérifier les régressions UI après un changement

---

## SETUP

```bash
# Installation (dans le répertoire frontend/)
npm install -D @playwright/test
npx playwright install chromium
```

```typescript
// playwright.config.ts

import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30000,
  retries: 1,
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:3000",
    headless: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    viewport: { width: 1280, height: 720 },
  },
  projects: [
    { name: "desktop", use: { viewport: { width: 1440, height: 900 } } },
    { name: "mobile", use: { viewport: { width: 375, height: 812 } } },
  ],
  webServer: {
    command: "npm run dev",
    port: 3000,
    reuseExistingServer: true,
  },
});
```

---

## PATTERNS DE TEST

### Page Objects

```typescript
// tests/e2e/pages/dashboard.ts

import { Page, expect } from "@playwright/test";

export class DashboardPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto("/dashboard");
  }

  async getHealthScore(): Promise<number> {
    const score = this.page.locator("[data-testid='health-score']");
    await expect(score).toBeVisible();
    return parseInt(await score.textContent() || "0");
  }

  async navigateToTab(tab: "health" | "listings" | "agentic" | "browser") {
    await this.page.click(`[data-testid='tab-${tab}']`);
    await this.page.waitForURL(`**/dashboard/${tab}`);
  }

  async getIssuesCount(): Promise<number> {
    const count = this.page.locator("[data-testid='issues-count']");
    return parseInt(await count.textContent() || "0");
  }

  async clickFirstFix() {
    await this.page.click("[data-testid='fix-button']:first-child");
  }

  async expectUpgradeModal() {
    await expect(this.page.locator("[data-testid='upgrade-modal']")).toBeVisible();
  }
}
```

### Test onboarding flow

```typescript
// tests/e2e/onboarding.spec.ts

import { test, expect } from "@playwright/test";

test.describe("Onboarding", () => {
  test("first scan starts automatically", async ({ page }) => {
    // Simuler un merchant fraîchement installé
    await page.goto("/onboarding");

    // Le scan progress doit être visible
    await expect(page.locator("[data-testid='scan-progress']")).toBeVisible();

    // Attendre que le scan termine (ou simuler)
    await expect(page.locator("[data-testid='health-score']")).toBeVisible({
      timeout: 10000,
    });

    // Le score doit être un nombre entre 0 et 100
    const score = await page.locator("[data-testid='health-score']").textContent();
    expect(parseInt(score || "0")).toBeGreaterThanOrEqual(0);
    expect(parseInt(score || "0")).toBeLessThanOrEqual(100);
  });

  test("shows 3 critical issues after scan", async ({ page }) => {
    await page.goto("/onboarding");
    await page.waitForSelector("[data-testid='issues-list']", { timeout: 15000 });

    const issues = page.locator("[data-testid='issue-card']");
    const count = await issues.count();
    expect(count).toBeGreaterThanOrEqual(1);
    expect(count).toBeLessThanOrEqual(5);
  });

  test("enable monitoring shows 3 settings", async ({ page }) => {
    await page.goto("/onboarding");
    await page.waitForSelector("[data-testid='health-score']", { timeout: 15000 });

    await page.click("[data-testid='enable-monitoring']");

    // 3 questions de config
    await expect(page.locator("[data-testid='alert-email']")).toBeVisible();
    await expect(page.locator("[data-testid='alert-threshold']")).toBeVisible();
    await expect(page.locator("[data-testid='install-pwa']")).toBeVisible();
  });
});
```

### Test dashboard navigation

```typescript
// tests/e2e/dashboard.spec.ts

import { test, expect } from "@playwright/test";
import { DashboardPage } from "./pages/dashboard";

test.describe("Dashboard", () => {
  let dashboard: DashboardPage;

  test.beforeEach(async ({ page }) => {
    // Auth setup (injecter un JWT valide)
    await page.goto("/dashboard");
    dashboard = new DashboardPage(page);
  });

  test("displays health score", async () => {
    const score = await dashboard.getHealthScore();
    expect(score).toBeGreaterThanOrEqual(0);
    expect(score).toBeLessThanOrEqual(100);
  });

  test("tabs navigate correctly", async ({ page }) => {
    await dashboard.navigateToTab("listings");
    await expect(page).toHaveURL(/\/dashboard\/listings/);

    await dashboard.navigateToTab("agentic");
    await expect(page).toHaveURL(/\/dashboard\/agentic/);
  });

  test("upgrade modal appears on Pro feature (Free plan)", async ({ page }) => {
    // Simuler un plan Free
    await dashboard.navigateToTab("browser");
    await dashboard.expectUpgradeModal();
  });
});
```

### Test responsive (mobile)

```typescript
// tests/e2e/mobile.spec.ts

import { test, expect } from "@playwright/test";

test.describe("Mobile", () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test("dashboard renders on mobile", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.locator("[data-testid='health-score']")).toBeVisible();
  });

  test("navigation menu is accessible", async ({ page }) => {
    await page.goto("/dashboard");
    // Mobile : menu hamburger
    await page.click("[data-testid='mobile-menu-toggle']");
    await expect(page.locator("[data-testid='mobile-nav']")).toBeVisible();
  });
});
```

---

## AUTH EN TEST

Pour les tests E2E, injecter un JWT valide via le localStorage ou les cookies :

```typescript
// tests/e2e/helpers/auth.ts

import { Page } from "@playwright/test";

export async function loginAsMerchant(page: Page, plan: string = "pro") {
  // Option 1 : Injecter le token Supabase directement
  await page.evaluate((token) => {
    localStorage.setItem("supabase.auth.token", JSON.stringify({
      access_token: token,
      token_type: "bearer",
    }));
  }, TEST_TOKENS[plan]);

  // Option 2 : Utiliser un endpoint test-only (staging)
  // await page.goto(`/api/test/login?plan=${plan}`);
}

// Tokens de test (valides uniquement en staging)
const TEST_TOKENS: Record<string, string> = {
  free: process.env.E2E_TOKEN_FREE || "",
  starter: process.env.E2E_TOKEN_STARTER || "",
  pro: process.env.E2E_TOKEN_PRO || "",
  agency: process.env.E2E_TOKEN_AGENCY || "",
};
```

---

## CONVENTIONS

### Fichiers

```
frontend/
├── tests/
│   └── e2e/
│       ├── pages/               # Page Objects
│       │   ├── dashboard.ts
│       │   ├── onboarding.ts
│       │   └── pricing.ts
│       ├── helpers/
│       │   └── auth.ts
│       ├── onboarding.spec.ts
│       ├── dashboard.spec.ts
│       ├── billing.spec.ts
│       └── mobile.spec.ts
├── playwright.config.ts
```

### Data-testid

Toujours utiliser `data-testid` pour les sélecteurs de test — jamais des classes CSS ou du texte :

```tsx
// ✅ BON
<div data-testid="health-score">{score}</div>
<button data-testid="fix-button">Apply Fix</button>

// ❌ MAUVAIS
// page.click(".btn-primary")  → fragile, le CSS change
// page.click("text=Apply Fix")  → fragile, le texte change
```

### Assertions

```typescript
// Visible
await expect(page.locator("[data-testid='x']")).toBeVisible();

// Texte
await expect(page.locator("[data-testid='x']")).toHaveText("expected");

// URL
await expect(page).toHaveURL(/\/dashboard/);

// Count
const items = page.locator("[data-testid='issue-card']");
await expect(items).toHaveCount(3);

// Pas visible (feature Pro sur plan Free)
await expect(page.locator("[data-testid='browser-tab']")).not.toBeVisible();
```

---

## EXÉCUTION

```bash
# Tous les tests
npx playwright test

# Un fichier
npx playwright test tests/e2e/dashboard.spec.ts

# Mode headed (voir le browser)
npx playwright test --headed

# Un seul project (mobile)
npx playwright test --project=mobile

# Debug mode
npx playwright test --debug

# Report HTML
npx playwright show-report
```

---

## INTERDICTIONS

- ❌ Sélecteurs CSS fragiles (`.btn-primary`) → ✅ `data-testid`
- ❌ `page.waitForTimeout(5000)` fixe → ✅ `page.waitForSelector()` ou `expect().toBeVisible()`
- ❌ Tests qui dépendent de l'ordre d'exécution → ✅ Chaque test est indépendant
- ❌ Tests E2E sur des données de production → ✅ Staging ou mocks uniquement
- ❌ Hardcoder des tokens dans le code → ✅ Env vars `E2E_TOKEN_*`
- ❌ Tests E2E qui testent la logique backend → ✅ Les tests backend sont dans pytest
