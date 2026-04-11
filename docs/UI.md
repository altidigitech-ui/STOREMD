# UI.md — Design System & Interface StoreMD

> **Toutes les règles UI/UX. Couleurs, typo, composants, layout, responsive.**
> **StoreMD est une app Shopify embedded → Polaris guidelines + shadcn/ui.**

---

## PRINCIPES DESIGN

1. **Polaris-compatible** — Le merchant est dans le Shopify Admin. L'app doit se fondre dans l'écosystème, pas ressembler à un site externe.
2. **Score-first** — Le health score est la première chose que le merchant voit. Toujours visible, toujours clair.
3. **Action-oriented** — Chaque écran montre des actions, pas juste des données. "Fix this" > "Here's a problem".
4. **Progressive disclosure** — Score → top issues → détails → fix. Pas de surcharge d'informations.
5. **Mobile-ready** — PWA installable. Le merchant consulte son score sur mobile entre deux réunions.

---

## STACK UI

```
shadcn/ui           → Composants de base (Button, Card, Dialog, Toast, Skeleton, Table)
Tailwind CSS        → Utility classes, responsive, dark mode ready
Shopify Polaris     → Guidelines de design (pas la librairie React Polaris)
Lucide React        → Icônes (cohérent avec shadcn/ui)
Recharts            → Graphiques (score history, trend charts)
```

### Pourquoi shadcn/ui et pas Polaris React

Polaris React est conçu pour les apps Shopify Admin. Mais :
- Il impose un design system rigide difficile à customiser
- shadcn/ui est plus flexible et mieux intégré avec Tailwind
- On suit les **guidelines visuelles** Polaris (espacements, couleurs, patterns) sans utiliser la librairie React

---

## COULEURS

### Palette principale

```css
/* Tailwind config — couleurs StoreMD */
:root {
  /* Brand */
  --storemd-primary: #2563eb;         /* Blue 600 — actions, CTAs */
  --storemd-primary-hover: #1d4ed8;   /* Blue 700 */

  /* Scores */
  --score-excellent: #16a34a;         /* Green 600 — score 80-100 */
  --score-good: #65a30d;              /* Lime 600 — score 60-79 */
  --score-warning: #ca8a04;           /* Yellow 600 — score 40-59 */
  --score-poor: #ea580c;              /* Orange 600 — score 20-39 */
  --score-critical: #dc2626;          /* Red 600 — score 0-19 */

  /* Severity */
  --severity-critical: #dc2626;       /* Red 600 */
  --severity-major: #ea580c;          /* Orange 600 */
  --severity-minor: #ca8a04;          /* Yellow 600 */
  --severity-info: #2563eb;           /* Blue 600 */

  /* Status */
  --status-success: #16a34a;          /* Green 600 */
  --status-warning: #ca8a04;          /* Yellow 600 */
  --status-error: #dc2626;            /* Red 600 */
  --status-pending: #6b7280;          /* Gray 500 */

  /* Backgrounds */
  --bg-primary: #ffffff;
  --bg-secondary: #f9fafb;           /* Gray 50 */
  --bg-card: #ffffff;
  --bg-muted: #f3f4f6;               /* Gray 100 */

  /* Text */
  --text-primary: #111827;           /* Gray 900 */
  --text-secondary: #6b7280;         /* Gray 500 */
  --text-muted: #9ca3af;             /* Gray 400 */

  /* Borders */
  --border-default: #e5e7eb;         /* Gray 200 */
  --border-focus: #2563eb;           /* Blue 600 */
}
```

### Score → couleur mapping

```typescript
function getScoreColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-lime-600";
  if (score >= 40) return "text-yellow-600";
  if (score >= 20) return "text-orange-600";
  return "text-red-600";
}

function getScoreBg(score: number): string {
  if (score >= 80) return "bg-green-50";
  if (score >= 60) return "bg-lime-50";
  if (score >= 40) return "bg-yellow-50";
  if (score >= 20) return "bg-orange-50";
  return "bg-red-50";
}

function getSeverityColor(severity: string): string {
  const map: Record<string, string> = {
    critical: "text-red-600 bg-red-50 border-red-200",
    major: "text-orange-600 bg-orange-50 border-orange-200",
    minor: "text-yellow-600 bg-yellow-50 border-yellow-200",
    info: "text-blue-600 bg-blue-50 border-blue-200",
  };
  return map[severity] || map.info;
}
```

---

## TYPOGRAPHIE

```css
/* Tailwind — font stack */
font-sans: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
font-mono: "JetBrains Mono", "Fira Code", Consolas, monospace;
```

| Élément | Classe Tailwind | Taille |
|---------|----------------|--------|
| Page title | `text-2xl font-bold` | 24px |
| Section title | `text-lg font-semibold` | 18px |
| Card title | `text-base font-medium` | 16px |
| Body text | `text-sm` | 14px |
| Caption / help | `text-xs text-gray-500` | 12px |
| Score (hero) | `text-5xl font-bold` | 48px |
| Score (card) | `text-3xl font-bold` | 30px |
| Badge | `text-xs font-medium` | 12px |

---

## LAYOUT — DASHBOARD

### Structure globale

```
┌─────────────────────────────────────────────────────────┐
│  SHOPIFY ADMIN HEADER (App Bridge)                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  TAB BAR                                          │   │
│  │  [ Health ] [ Listings ] [ AI Ready ] [ Browser ] │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  SCORE HERO                                       │   │
│  │                                                    │   │
│  │  ┌─────────┐                                      │   │
│  │  │   67    │  /100        ↗ +9 since last week   │   │
│  │  │  ████░  │              Mobile: 52 | Desktop: 81│   │
│  │  └─────────┘                                      │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  ISSUES LIST                                      │   │
│  │                                                    │   │
│  │  🔴 Critical: App Privy injects 340KB     [Fix →] │   │
│  │  🔴 Critical: 3 ghost scripts              [Fix →] │   │
│  │  🟡 Major: 12 products missing alt text   [Fix →] │   │
│  │  🟢 Minor: Meta description auto-generated        │   │
│  │                                                    │   │
│  │  [Show all 7 issues]                              │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  TREND CHART (7 jours)                            │   │
│  │  ┌────────────────────────────────┐               │   │
│  │  │    67                          │               │   │
│  │  │   /  \        63              │               │   │
│  │  │  58   61    /    \  67        │               │   │
│  │  │ /                  \/         │               │   │
│  │  └────────────────────────────────┘               │   │
│  │  Mon  Tue  Wed  Thu  Fri  Sat  Sun               │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌────────────────────┐  ┌────────────────────────┐     │
│  │  APPS IMPACT       │  │  QUICK STATS           │     │
│  │  Privy: 1.8s       │  │  Products: 847         │     │
│  │  Klaviyo: 0.9s     │  │  Apps: 14              │     │
│  │  Reviews+: 0.5s    │  │  Theme: Dawn 15.0      │     │
│  │  [See all apps]    │  │  Last scan: 2h ago     │     │
│  └────────────────────┘  └────────────────────────┘     │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Onglets dashboard

| Onglet | Route | Contenu | Plan minimum |
|--------|-------|---------|-------------|
| **Health** | `/dashboard/health` | Score hero, issues list, trend chart, apps impact, quick stats | Free |
| **Listings** | `/dashboard/listings` | Catalogue scan results, product list triable, priorities | Free (5 produits) |
| **AI Ready** | `/dashboard/agentic` | Agentic score, 6 checks, HS codes, compliance (accessibility, broken links) | Starter |
| **Browser** | `/dashboard/browser` | Visual diff, user simulation, accessibility live | Pro |
| **Settings** | `/dashboard/settings` | Alertes, notifications, plan, billing | Free |

L'onglet Browser est **grisé** pour les plans Free/Starter avec un badge "Pro".

### Layout responsive

```
Desktop (>1024px)    : 2 colonnes, cards côte à côte
Tablet (768-1024px)  : 1 colonne, cards pleine largeur
Mobile (<768px)      : 1 colonne, score compact, issues empilées
```

```tsx
// Layout pattern
<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
  <Card>Apps Impact</Card>
  <Card>Quick Stats</Card>
</div>
```

---

## COMPOSANTS PRINCIPAUX

### ScoreHero

Le composant le plus important. Première chose que le merchant voit.

```tsx
interface ScoreHeroProps {
  score: number;
  mobileScore: number;
  desktopScore: number;
  trend: "up" | "down" | "stable";
  trendDelta: number;
  lastScanAt: string;
}

// Layout :
// ┌─────────────────────────────────────┐
// │  ┌─────────┐                        │
// │  │   67    │  /100                  │
// │  │  ████░  │  ↗ +9 since last week │
// │  └─────────┘  Mobile: 52 | Desk: 81│
// │                Last scan: 2h ago    │
// │               [Scan now]            │
// └─────────────────────────────────────┘
```

Le score utilise un cercle SVG animé :

```tsx
function ScoreCircle({ score }: { score: number }) {
  const circumference = 2 * Math.PI * 45; // r=45
  const offset = circumference - (score / 100) * circumference;

  return (
    <svg className="w-32 h-32" viewBox="0 0 100 100">
      {/* Background circle */}
      <circle cx="50" cy="50" r="45" fill="none" stroke="#e5e7eb" strokeWidth="8" />
      {/* Score circle */}
      <circle
        cx="50" cy="50" r="45" fill="none"
        stroke={getScoreStroke(score)}
        strokeWidth="8"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform="rotate(-90 50 50)"
        className="transition-all duration-1000 ease-out"
      />
      {/* Score number */}
      <text x="50" y="50" textAnchor="middle" dominantBaseline="central"
            className="text-3xl font-bold fill-gray-900">
        {score}
      </text>
    </svg>
  );
}
```

### IssueCard

```tsx
interface IssueCardProps {
  issue: ScanIssue;
  onFix: (issueId: string) => void;
  onDismiss: (issueId: string) => void;
}

// Layout :
// ┌─────────────────────────────────────────────┐
// │ 🔴 Critical                                  │
// │                                               │
// │ App 'Privy' injects 340KB of unminified JS   │
// │ Impact: +1.8s load time                       │
// │                                               │
// │ Consider replacing Privy with a lighter...    │
// │                                               │
// │ [Fix →]  [Dismiss]  [Details]                │
// └─────────────────────────────────────────────┘

// Severity indicator : bande de couleur à gauche
// Critical = red, Major = orange, Minor = yellow, Info = blue
```

```tsx
function IssueCard({ issue, onFix, onDismiss }: IssueCardProps) {
  return (
    <div className={cn(
      "rounded-lg border p-4 flex gap-4",
      getSeverityBorderColor(issue.severity),
    )}>
      {/* Severity badge */}
      <div className="flex-shrink-0">
        <span className={cn("text-xs font-medium px-2 py-1 rounded-full",
          getSeverityColor(issue.severity))}>
          {issue.severity}
        </span>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <h4 className="text-sm font-medium text-gray-900">{issue.title}</h4>
        {issue.impact && (
          <p className="text-xs text-gray-500 mt-1">Impact: {issue.impact}</p>
        )}
        {issue.fix_description && (
          <p className="text-sm text-gray-600 mt-2">{issue.fix_description}</p>
        )}
      </div>

      {/* Actions */}
      <div className="flex-shrink-0 flex flex-col gap-2">
        {issue.auto_fixable && (
          <Button size="sm" onClick={() => onFix(issue.id)}>Fix →</Button>
        )}
        <Button size="sm" variant="ghost" onClick={() => onDismiss(issue.id)}>
          Dismiss
        </Button>
      </div>
    </div>
  );
}
```

### TrendChart

```tsx
interface TrendChartProps {
  data: { date: string; score: number }[];
  height?: number;
}

// Utilise Recharts
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

function TrendChart({ data, height = 200 }: TrendChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data}>
        <XAxis dataKey="date" tick={{ fontSize: 12 }} tickFormatter={formatDate} />
        <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
        <Tooltip />
        <Line
          type="monotone"
          dataKey="score"
          stroke="#2563eb"
          strokeWidth={2}
          dot={{ fill: "#2563eb", r: 4 }}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

### ScanProgress

Affiché pendant le scan (onboarding + scan manuel).

```tsx
interface ScanProgressProps {
  status: "pending" | "running" | "completed";
  progress: number; // 0-100
  currentStep: string;
  completedSteps: string[];
  facts: string[]; // "Did you know?" facts
}

// Layout :
// ┌──────────────────────────────────────────┐
// │  🔍 Scanning your store...               │
// │                                           │
// │  ████████████░░░░░░░░  62%               │
// │                                           │
// │  ✅ Theme analyzed (Dawn 15.0)           │
// │  ✅ 12 apps detected                     │
// │  ✅ 847 products scanned                 │
// │  ⏳ Checking app impact on speed...      │
// │                                           │
// │  💡 Did you know? The average Shopify    │
// │     store has 14 apps, each adding       │
// │     200-500ms to load time.              │
// └──────────────────────────────────────────┘
```

### OneClickFix

Preview avant/après + bouton apply.

```tsx
interface OneClickFixProps {
  fix: Fix;
  onApply: (fixId: string) => void;
  onRevert: (fixId: string) => void;
}

// Layout :
// ┌──────────────────────────────────────────┐
// │  Fix: Generate alt text for product image │
// │                                           │
// │  Before:  (no alt text)                   │
// │  After:   "Organic face cream in glass    │
// │            jar with natural ingredients"   │
// │                                           │
// │  [Preview on store]  [Apply fix →]        │
// └──────────────────────────────────────────┘
// Après apply :
// │  ✅ Applied  [Undo]                       │
```

### UpgradeModal

Affiché quand une feature nécessite un plan supérieur.

```tsx
interface UpgradeModalProps {
  feature: string;
  requiredPlan: "starter" | "pro" | "agency";
  currentPlan: string;
}

// Layout :
// ┌──────────────────────────────────────────┐
// │  🔒 Visual Store Test requires Pro       │
// │                                           │
// │  Upgrade to Pro ($99/month) to unlock:    │
// │  ✓ Daily scans                           │
// │  ✓ Visual Store Test                     │
// │  ✓ Real User Simulation                  │
// │  ✓ 1000 product analyses                 │
// │  ✓ Bulk operations                       │
// │                                           │
// │  [Upgrade to Pro →]    [Maybe later]      │
// └──────────────────────────────────────────┘
```

Pas de popup agressif. Pas de countdown timer. Juste les faits.

---

## PAGES

### Landing page (`/`) — SSR pour SEO

```
┌─────────────────────────────────────────────┐
│  HERO                                        │
│  "Your Shopify store health score            │
│   in 60 seconds. Free."                      │
│                                              │
│  [Add to Shopify — Free]                     │
│                                              │
├─────────────────────────────────────────────┤
│  3 FEATURES CARDS                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │ Health   │ │ Listings │ │ AI Ready │    │
│  │ Score    │ │ Optimize │ │ ChatGPT  │    │
│  │ 24/7     │ │ 1-click  │ │ Shopping │    │
│  └──────────┘ └──────────┘ └──────────┘    │
│                                              │
├─────────────────────────────────────────────┤
│  HOW IT WORKS (3 steps)                      │
│  1. Install (0 seconds)                      │
│  2. Get your score (60 seconds)              │
│  3. Fix issues (1-click)                     │
│                                              │
├─────────────────────────────────────────────┤
│  SOCIAL PROOF                                │
│  "Analyzed 530+ app reviews to build         │
│   the most accurate scanner"                 │
│                                              │
├─────────────────────────────────────────────┤
│  PRICING TABLE                               │
│  Free | Starter $39 | Pro $99 | Agency $249 │
│                                              │
├─────────────────────────────────────────────┤
│  FAQ (accordion)                             │
│                                              │
├─────────────────────────────────────────────┤
│  FOOTER CTA                                  │
│  [Add to Shopify — Free]                     │
└─────────────────────────────────────────────┘
```

### Onboarding (`/onboarding`)

Voir `docs/ONBOARDING.md` pour le flow détaillé. Résumé :
1. ScanProgress (auto-start)
2. ScoreHero + top 3 issues
3. Enable monitoring (3 questions)
4. Redirect → dashboard

### Pricing (`/pricing`)

4 colonnes, feature comparison table, CTA par plan.

### Settings (`/dashboard/settings`)

- Alert preferences (email, seuil, push on/off)
- Notification settings (max push/week)
- Plan & billing (current plan, usage, upgrade/downgrade via Stripe Portal)
- Store info (domain, theme, apps count)
- PWA install prompt

---

## ÉTATS UI

Chaque composant qui charge des données gère 4 états :

```tsx
function ScanResults({ storeId }: { storeId: string }) {
  const { data, isLoading, error } = useScan(storeId);

  // 1. Loading
  if (isLoading) return <ScanResultsSkeleton />;

  // 2. Error
  if (error) return <ErrorState message={error.message} onRetry={refetch} />;

  // 3. Empty
  if (!data || data.issues.length === 0) return <EmptyState message="No issues found" />;

  // 4. Loaded
  return <IssuesList issues={data.issues} />;
}
```

### Skeleton pattern

```tsx
function ScanResultsSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-32 w-full rounded-lg" />
      <Skeleton className="h-20 w-full rounded-lg" />
      <Skeleton className="h-20 w-full rounded-lg" />
    </div>
  );
}
```

### ErrorState pattern

```tsx
function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
      <p className="text-sm text-red-600">{message}</p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} className="mt-4">
          Try again
        </Button>
      )}
    </div>
  );
}
```

### EmptyState pattern

```tsx
function EmptyState({ message, action }: { message: string; action?: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center">
      <p className="text-sm text-gray-500">{message}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
```

---

## DATA-TESTID CONVENTION

Pour les tests Playwright E2E (voir `.claude/skills/playwright-testing/SKILL.md`).

```tsx
// Toujours utiliser data-testid sur les éléments interactifs et les données clés
<div data-testid="health-score">{score}</div>
<button data-testid="fix-button">Fix →</button>
<div data-testid="issue-card">...</div>
<div data-testid="scan-progress">...</div>
<button data-testid="enable-monitoring">Enable monitoring</button>
<input data-testid="alert-email" />
<input data-testid="alert-threshold" />
<button data-testid="install-pwa">Add to home screen</button>
<div data-testid="tab-health">Health</div>
<div data-testid="tab-listings">Listings</div>
<div data-testid="tab-agentic">AI Ready</div>
<div data-testid="tab-browser">Browser</div>
<button data-testid="scan-now">Scan now</button>
<div data-testid="upgrade-modal">...</div>
<button data-testid="mobile-menu-toggle">☰</button>
<nav data-testid="mobile-nav">...</nav>
<div data-testid="issues-count">{count}</div>
<div data-testid="issues-list">...</div>
```

---

## TOAST NOTIFICATIONS

```tsx
import { useToast } from "@/components/ui/toast";

const { toast } = useToast();

// Succès
toast({ title: "Fix applied", description: "Alt text added to 12 images." });

// Erreur
toast({ title: "Fix failed", description: error.message, variant: "destructive" });

// Info
toast({ title: "Scan started", description: "Results in about 60 seconds." });

// Warning (plan)
toast({ title: "Scan limit reached", description: "Upgrade for more scans." });
```

Position : bottom-right. Auto-dismiss : 5 secondes. Max 3 visibles simultanément.

---

## ANIMATIONS

Minimales et fonctionnelles :

```css
/* Score circle fill — on load */
.transition-all.duration-1000.ease-out

/* Card hover */
.hover:shadow-md.transition-shadow

/* Issue card expand */
.transition-all.duration-200

/* Skeleton pulse */
.animate-pulse

/* Page transitions */
/* Pas de page transition — chargement instantané avec loading states */
```

Pas de :
- ❌ Animations au scroll (parallax, fade-in)
- ❌ Transitions de page (le Shopify Admin ne le fait pas)
- ❌ Confetti, particles, effets spectaculaires
- ❌ Animations qui retardent l'accès au contenu

---

## DARK MODE

StoreMD supporte le dark mode (le Shopify Admin le supporte). Utiliser les CSS variables Tailwind :

```tsx
// tailwind.config.ts
module.exports = {
  darkMode: "class", // ou "media" pour suivre l'OS
  // ...
};
```

```tsx
// Composants — toujours utiliser les classes dark:
<div className="bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
  ...
</div>

// Cards
<div className="bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700">
  ...
</div>
```

Pas de priorité M1, mais structurer le code pour que l'ajout soit trivial.

---

## INTERDICTIONS

- ❌ CSS inline ou CSS modules → ✅ Tailwind classes uniquement
- ❌ Polaris React components → ✅ shadcn/ui + Polaris guidelines visuelles
- ❌ Animations spectaculaires → ✅ Transitions fonctionnelles minimales
- ❌ Popup aggressif (countdown, fullscreen) → ✅ UpgradeModal discret, contextuel
- ❌ Dashboard vide au premier load → ✅ ScanProgress auto-start + facts
- ❌ Score sans contexte → ✅ Toujours trend + delta + mobile/desktop breakdown
- ❌ Issue sans action → ✅ Chaque issue a un fix_description et un bouton
- ❌ Sélecteurs CSS dans les tests → ✅ data-testid uniquement
- ❌ `console.log` pour le debug UI → ✅ React DevTools + structuré
- ❌ Couleurs hardcodées → ✅ CSS variables ou Tailwind config
