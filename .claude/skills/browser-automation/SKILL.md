# Skill: Browser Automation

> **Utilise ce skill quand tu travailles sur les 3 features Playwright :**
> **Visual Store Test, Real User Simulation, Accessibility Live Test.**
> **Module Browser Automation — Pro plan only.**

---

## QUAND UTILISER

- Implémenter/modifier `app/agent/browser/visual_store_test.py`
- Implémenter/modifier `app/agent/browser/real_user_simulation.py`
- Implémenter/modifier `app/agent/browser/accessibility_live.py`
- Configurer Playwright dans le Celery worker (Dockerfile.worker)
- Débugger un test browser qui timeout ou échoue

---

## ARCHITECTURE

Les 3 scanners browser tournent dans le **Celery worker** (pas dans l'API).
Playwright est installé UNIQUEMENT dans `Dockerfile.worker`.
Exécution **séquentielle** (1 browser à la fois — Playwright est lourd).

```
Celery worker (Railway service storemd-worker)
    │
    ├── Playwright Chromium (headless)
    │   ├── visual_store_test.py      → Screenshots + diff
    │   ├── real_user_simulation.py   → Parcours achat complet
    │   └── accessibility_live.py     → WCAG rendu réel
    │
    └── Résultats → Supabase DB + Supabase Storage (screenshots)
```

---

## DOCKERFILE.WORKER — PLAYWRIGHT INSTALL

```dockerfile
# Dockerfile.worker
FROM python:3.12-slim

WORKDIR /app

# System deps pour Playwright Chromium
RUN apt-get update && apt-get install -y \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxrandr2 libgbm1 libpango-1.0-0 libcairo2 \
    libasound2 libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installer Playwright + Chromium
RUN pip install playwright && playwright install chromium

COPY . .

CMD ["celery", "-A", "tasks.celery_app", "worker", "--beat", "--loglevel=info", "--concurrency=2"]
```

`--concurrency=2` : max 2 tasks simultanées sur le worker (Playwright est gourmand en RAM).

---

## BASE BROWSER SCANNER

```python
# app/agent/browser/base.py

from playwright.async_api import async_playwright, Browser, Page
from app.agent.analyzers.base import BaseScanner

class BaseBrowserScanner(BaseScanner):
    """Base pour les scanners browser. Gère le lifecycle Playwright."""

    group = "browser"
    requires_plan = "pro"

    async def scan(
        self, store_id: str, shopify: ShopifyClient, memory_context: list[dict]
    ) -> ScannerResult:
        store_url = await self.get_store_url(store_id, shopify)

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",    # Railway containers
                    "--disable-gpu",
                    "--single-process",
                ],
            )
            try:
                result = await self.run_test(browser, store_url, store_id, memory_context)
                return result
            finally:
                await browser.close()

    async def get_store_url(self, store_id: str, shopify: ShopifyClient) -> str:
        """Récupère l'URL publique du store (custom domain ou myshopify.com)."""
        data = await shopify.graphql("""
            query { shop { primaryDomain { url } } }
        """)
        return data["shop"]["primaryDomain"]["url"]

    async def create_page(self, browser: Browser, device: str = "desktop") -> Page:
        """Crée une page avec le bon viewport."""
        viewports = {
            "mobile": {"width": 375, "height": 812, "user_agent": MOBILE_UA},
            "desktop": {"width": 1440, "height": 900, "user_agent": DESKTOP_UA},
        }
        vp = viewports[device]
        context = await browser.new_context(
            viewport={"width": vp["width"], "height": vp["height"]},
            user_agent=vp["user_agent"],
        )
        page = await context.new_page()
        page.set_default_timeout(30000)  # 30s par action
        return page

    @abstractmethod
    async def run_test(
        self, browser: Browser, store_url: str,
        store_id: str, memory_context: list[dict]
    ) -> ScannerResult:
        ...

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
DESKTOP_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
```

---

## FEATURE #42 — VISUAL STORE TEST

Screenshots mobile + desktop, diff pixel avec le scan précédent.

```python
# app/agent/browser/visual_store_test.py

from PIL import Image, ImageChops
import io

class VisualStoreTest(BaseBrowserScanner):
    name = "visual_store_test"
    module = "browser"

    async def run_test(
        self, browser: Browser, store_url: str,
        store_id: str, memory_context: list[dict]
    ) -> ScannerResult:
        issues = []
        screenshots_data = {}

        for device in ["mobile", "desktop"]:
            page = await self.create_page(browser, device)
            try:
                # 1. Navigate et attendre le rendu complet
                await page.goto(store_url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(2000)  # Attendre les animations/lazy load

                # 2. Screenshot full page
                screenshot_bytes = await page.screenshot(full_page=True, type="png")

                # 3. Stocker dans Supabase Storage
                path = f"screenshots/{store_id}/{device}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.png"
                storage_url = await self.upload_screenshot(path, screenshot_bytes)
                screenshots_data[device] = {"path": path, "url": storage_url}

                # 4. Comparer avec le screenshot précédent
                previous = await self.get_previous_screenshot(store_id, device)
                if previous:
                    diff_pct, diff_regions = self.compute_diff(
                        previous["bytes"], screenshot_bytes
                    )
                    screenshots_data[device]["diff_pct"] = diff_pct
                    screenshots_data[device]["diff_regions"] = diff_regions

                    if diff_pct > 5.0:  # >5% de changement = significatif
                        probable_cause = await self.guess_cause(
                            store_id, diff_regions, memory_context
                        )
                        issues.append(ScanIssue(
                            module="browser",
                            scanner=self.name,
                            severity="major" if diff_pct > 15 else "minor",
                            title=f"Visual change detected on {device} ({diff_pct:.1f}% changed)",
                            description=(
                                f"Significant visual changes detected on {device} view. "
                                f"Probable cause: {probable_cause}."
                            ),
                            impact=f"{diff_pct:.1f}% of page changed",
                            impact_value=diff_pct,
                            impact_unit="percent",
                            fix_type="manual",
                            fix_description=f"Review the changes: {probable_cause}",
                            context={
                                "device": device,
                                "diff_pct": diff_pct,
                                "diff_regions": diff_regions,
                                "probable_cause": probable_cause,
                            },
                        ))
            finally:
                await page.close()

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={"screenshots": screenshots_data},
        )

    def compute_diff(self, prev_bytes: bytes, curr_bytes: bytes) -> tuple[float, list[dict]]:
        """Compare deux screenshots pixel par pixel."""
        prev_img = Image.open(io.BytesIO(prev_bytes))
        curr_img = Image.open(io.BytesIO(curr_bytes))

        # Resize au même format si nécessaire
        if prev_img.size != curr_img.size:
            curr_img = curr_img.resize(prev_img.size)

        diff = ImageChops.difference(prev_img, curr_img)
        diff_pixels = sum(1 for px in diff.getdata() if sum(px[:3]) > 30)
        total_pixels = prev_img.size[0] * prev_img.size[1]
        diff_pct = (diff_pixels / total_pixels) * 100

        # Identifier les régions changées (simplification : top/middle/bottom)
        regions = self.identify_regions(diff, prev_img.size)

        return diff_pct, regions

    def identify_regions(self, diff_img: Image, size: tuple) -> list[dict]:
        """Identifie les zones de changement (heuristique par tiers vertical)."""
        w, h = size
        thirds = [
            ("top (header/hero)", 0, h // 3),
            ("middle (content)", h // 3, 2 * h // 3),
            ("bottom (footer)", 2 * h // 3, h),
        ]
        regions = []
        for name, y_start, y_end in thirds:
            crop = diff_img.crop((0, y_start, w, y_end))
            changed = sum(1 for px in crop.getdata() if sum(px[:3]) > 30)
            total = w * (y_end - y_start)
            pct = (changed / total) * 100
            if pct > 3:
                regions.append({"area": name, "change_pct": round(pct, 1)})
        return regions

    async def guess_cause(
        self, store_id: str, diff_regions: list[dict], memory_context: list[dict]
    ) -> str:
        """Devine la cause probable via corrélation temporelle."""
        # Chercher dans Mem0 : app update récente ? theme change ?
        for mem in memory_context:
            content = mem.get("memory", mem.get("content", ""))
            if "updated" in content.lower() or "changed" in content.lower():
                return content
        # Fallback
        areas = ", ".join(r["area"] for r in diff_regions)
        return f"Visual changes in {areas} — check recent app updates or theme changes"
```

---

## FEATURE #43 — REAL USER SIMULATION

Parcours achat complet Homepage → Collection → Product → Add to Cart → Checkout.

```python
# app/agent/browser/real_user_simulation.py

class RealUserSimulation(BaseBrowserScanner):
    name = "real_user_simulation"
    module = "browser"

    async def run_test(
        self, browser: Browser, store_url: str,
        store_id: str, memory_context: list[dict]
    ) -> ScannerResult:
        page = await self.create_page(browser, "mobile")  # Mobile-first
        steps = []
        bottleneck_step = None
        bottleneck_cause = None

        try:
            # Step 1 — Homepage
            step = await self.time_navigation(page, store_url, "Homepage")
            steps.append(step)

            # Step 2 — Collection (trouver un lien collection)
            collection_url = await self.find_collection_link(page, store_url)
            if collection_url:
                step = await self.time_navigation(page, collection_url, "Collection")
                steps.append(step)

            # Step 3 — Product (premier produit de la collection)
            product_url = await self.find_product_link(page, store_url)
            if product_url:
                step = await self.time_navigation(page, product_url, "Product")
                steps.append(step)

                # Step 4 — Add to Cart
                step = await self.time_add_to_cart(page)
                steps.append(step)

            # Step 5 — Checkout (navigate to cart/checkout)
            step = await self.time_navigation(page, f"{store_url}/cart", "Cart/Checkout")
            steps.append(step)

        except Exception as exc:
            logger.warning("simulation_step_failed", error=str(exc))
            steps.append({
                "name": "Error",
                "url": page.url,
                "time_ms": 0,
                "bottleneck": False,
                "cause": str(exc),
            })
        finally:
            await page.close()

        # Identifier le bottleneck
        total_ms = sum(s["time_ms"] for s in steps)
        if steps:
            slowest = max(steps, key=lambda s: s["time_ms"])
            if slowest["time_ms"] > 3000:  # >3s = bottleneck
                slowest["bottleneck"] = True
                bottleneck_step = slowest["name"]
                bottleneck_cause = await self.diagnose_bottleneck(
                    slowest, memory_context
                )

        issues = []
        if total_ms > 10000:  # >10s total = problème
            issues.append(ScanIssue(
                module="browser",
                scanner=self.name,
                severity="critical" if total_ms > 20000 else "major",
                title=f"Slow user journey: {total_ms/1000:.1f}s total",
                description=(
                    f"Full purchase path takes {total_ms/1000:.1f}s. "
                    f"Bottleneck: {bottleneck_step or 'none'} "
                    f"({bottleneck_cause or 'unknown cause'})."
                ),
                impact=f"{total_ms/1000:.1f}s total journey time",
                impact_value=total_ms / 1000,
                impact_unit="seconds",
                fix_type="manual",
                fix_description=f"Optimize {bottleneck_step}: {bottleneck_cause}",
                context={
                    "total_time_ms": total_ms,
                    "steps": steps,
                    "bottleneck_step": bottleneck_step,
                    "bottleneck_cause": bottleneck_cause,
                },
            ))

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "total_time_ms": total_ms,
                "steps": steps,
                "bottleneck_step": bottleneck_step,
            },
        )

    async def time_navigation(self, page: Page, url: str, name: str) -> dict:
        """Navigue vers une URL et mesure le temps réel."""
        start = time.monotonic()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass  # Timeout partiel OK — on mesure quand même
        elapsed_ms = int((time.monotonic() - start) * 1000)

        return {
            "name": name,
            "url": url,
            "time_ms": elapsed_ms,
            "bottleneck": False,
            "cause": None,
        }

    async def time_add_to_cart(self, page: Page) -> dict:
        """Clique Add to Cart et mesure le temps."""
        start = time.monotonic()
        try:
            # Chercher le bouton ATC (patterns Shopify courants)
            atc_selectors = [
                "button[name='add']",
                "button.product-form__submit",
                "[data-action='add-to-cart']",
                "button:has-text('Add to cart')",
                "button:has-text('Add to Cart')",
            ]
            for selector in atc_selectors:
                btn = page.locator(selector).first
                if await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(2000)  # Attendre le cart update
                    break
        except Exception:
            pass
        elapsed_ms = int((time.monotonic() - start) * 1000)

        return {
            "name": "Add to Cart",
            "url": None,
            "time_ms": elapsed_ms,
            "bottleneck": False,
            "cause": None,
        }

    async def find_collection_link(self, page: Page, base_url: str) -> str | None:
        """Trouve un lien vers une collection sur la page."""
        links = await page.locator("a[href*='/collections/']").all()
        for link in links[:5]:
            href = await link.get_attribute("href")
            if href and "/collections/" in href and href != "/collections/all":
                return href if href.startswith("http") else f"{base_url}{href}"
        # Fallback
        return f"{base_url}/collections/all"

    async def find_product_link(self, page: Page, base_url: str) -> str | None:
        """Trouve un lien vers un produit sur la page."""
        links = await page.locator("a[href*='/products/']").all()
        for link in links[:5]:
            href = await link.get_attribute("href")
            if href and "/products/" in href:
                return href if href.startswith("http") else f"{base_url}{href}"
        return None
```

---

## ACCESSIBILITY LIVE TEST (extension #39)

```python
# app/agent/browser/accessibility_live.py

class AccessibilityLiveTest(BaseBrowserScanner):
    name = "accessibility_live"
    module = "browser"

    async def run_test(
        self, browser: Browser, store_url: str,
        store_id: str, memory_context: list[dict]
    ) -> ScannerResult:
        page = await self.create_page(browser, "mobile")
        issues = []

        try:
            await page.goto(store_url, wait_until="networkidle", timeout=30000)

            # 1. Inject axe-core pour les checks WCAG
            await page.add_script_tag(url="https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.1/axe.min.js")
            axe_results = await page.evaluate("() => axe.run()")

            for violation in axe_results.get("violations", []):
                severity_map = {"critical": "critical", "serious": "major",
                                "moderate": "minor", "minor": "info"}
                issues.append(ScanIssue(
                    module="browser",
                    scanner=self.name,
                    severity=severity_map.get(violation["impact"], "minor"),
                    title=f"Accessibility: {violation['help']}",
                    description=violation.get("description", ""),
                    impact=f"{len(violation['nodes'])} elements affected",
                    impact_value=len(violation["nodes"]),
                    impact_unit="elements",
                    fix_type="developer",
                    fix_description=violation.get("helpUrl", ""),
                    context={
                        "rule_id": violation["id"],
                        "wcag_tags": violation.get("tags", []),
                        "nodes_count": len(violation["nodes"]),
                    },
                ))

            # 2. Checks manuels Playwright (ce que axe ne détecte pas)

            # Boutons assez grands pour le mobile ? (48x48px minimum)
            buttons = await page.locator("button, a.btn, [role='button']").all()
            small_buttons = 0
            for btn in buttons[:20]:
                box = await btn.bounding_box()
                if box and (box["width"] < 44 or box["height"] < 44):
                    small_buttons += 1
            if small_buttons > 0:
                issues.append(ScanIssue(
                    module="browser",
                    scanner=self.name,
                    severity="major",
                    title=f"{small_buttons} buttons too small for mobile (< 44px)",
                    description="Touch targets should be at least 44x44px for accessibility.",
                    fix_type="developer",
                    fix_description="Increase button size to minimum 44x44px",
                    auto_fixable=False,
                    context={"small_buttons_count": small_buttons},
                ))

            # Navigation clavier possible ?
            await page.keyboard.press("Tab")
            focused = await page.evaluate("() => document.activeElement?.tagName")
            if not focused or focused == "BODY":
                issues.append(ScanIssue(
                    module="browser",
                    scanner=self.name,
                    severity="major",
                    title="Keyboard navigation broken — no focusable elements",
                    description="Pressing Tab does not move focus to any interactive element.",
                    fix_type="developer",
                    fix_description="Ensure interactive elements have proper tabindex",
                    auto_fixable=False,
                ))

        finally:
            await page.close()

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "violations_count": len(issues),
                "axe_version": "4.9.1",
            },
        )
```

---

## SUPABASE STORAGE — SCREENSHOTS

```python
async def upload_screenshot(self, path: str, data: bytes) -> str:
    """Upload screenshot vers Supabase Storage."""
    supabase = get_supabase_service()
    result = supabase.storage.from_("screenshots").upload(
        path, data, {"content-type": "image/png"}
    )
    return supabase.storage.from_("screenshots").get_public_url(path)

async def get_previous_screenshot(self, store_id: str, device: str) -> dict | None:
    """Récupère le screenshot précédent pour la comparaison."""
    result = await supabase.table("screenshots").select("*").eq(
        "store_id", store_id
    ).eq("device", device).order(
        "created_at", desc=True
    ).limit(1).maybe_single().execute()

    if not result.data:
        return None

    # Télécharger le fichier depuis Storage
    file_bytes = supabase.storage.from_("screenshots").download(result.data["storage_path"])
    return {"bytes": file_bytes, **result.data}
```

---

## TIMEOUTS ET LIMITES

| Paramètre | Valeur | Pourquoi |
|-----------|--------|----------|
| Navigation timeout | 30s | Stores lents, lazy load |
| Network idle wait | 15s | Attendre que tout charge |
| Post-load wait | 2s | Animations, popups différés |
| Screenshot timeout | 10s | Full page peut être long |
| Total par scanner | 90s | Hard limit dans le pipeline |
| Concurrency worker | 2 | RAM limitée (Playwright ~300MB/browser) |

---

## INTERDICTIONS

- ❌ Playwright dans l'API (Dockerfile) → ✅ Uniquement dans le worker (Dockerfile.worker)
- ❌ Lancer le browser sans `--no-sandbox` → ✅ Requis dans les containers Railway
- ❌ Screenshots sans cleanup → ✅ Rétention 90 jours dans Supabase Storage
- ❌ Simuler un achat réel (paiement) → ✅ S'arrêter au cart/checkout, JAMAIS soumettre un paiement
- ❌ Se connecter au store admin → ✅ Naviguer uniquement sur le storefront public
- ❌ Plus de 2 tests browser simultanés → ✅ `--concurrency=2` sur le worker
