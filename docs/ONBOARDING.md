# ONBOARDING.md — Parcours Utilisateur StoreMD

> **Les 6 étapes du parcours merchant, de la découverte à l'utilisation quotidienne.**
> **Règle #1 : Le merchant voit de la VALEUR en moins de 90 secondes.**
> **Pour les textes exacts, voir `docs/COPY.md`.**
> **Pour le design des écrans, voir `docs/UI.md`.**

---

## STAT CLÉ

**77% des utilisateurs quittent une app dans les 3 premiers jours.**
Si l'agent ne prouve pas sa valeur en 90 secondes, c'est mort.

---

## CE QU'ON NE FAIT JAMAIS

- ❌ Formulaire d'inscription séparé (Shopify Auth gère tout)
- ❌ Tutoriel de 7 écrans avant de pouvoir utiliser l'app
- ❌ Dashboard vide au premier lancement ("No data yet, come back tomorrow")
- ❌ Demander des infos qu'on récupère automatiquement via l'API Shopify
- ❌ Forcer un choix de plan avant de montrer la valeur
- ❌ Mur de configuration ("Choose your apps to monitor", "Select your categories")
- ❌ Email de bienvenue qui dit "Getting started guide — 12 steps"

## CE QU'ON FAIT TOUJOURS

- ✅ Le premier scan se lance AUTOMATIQUEMENT dès l'ouverture (0 clic)
- ✅ Pendant le scan (30-90s), progress bar + facts = le merchant apprend déjà
- ✅ Le résultat apparaît avec un score + 3 actions prioritaires
- ✅ Le plan Free est FONCTIONNEL — le merchant voit la vraie valeur avant de payer
- ✅ Shopify App Store = zéro friction (OAuth auto, pas de login séparé)
- ✅ Design Polaris-compatible — le merchant se sent chez lui dans le Shopify Admin
- ✅ Max 5 étapes d'onboarding (règle Shopify)

---

## LES 6 ÉTAPES

```
ÉTAPE 0 — DÉCOUVERTE        Shopify App Store (avant l'install)
ÉTAPE 1 — INSTALLATION      OAuth Shopify (0 secondes)
ÉTAPE 2 — PREMIER SCAN      Automatique (0-90 secondes)
ÉTAPE 3 — AHA MOMENT        Score + 3 issues + fixes (90 secondes)
ÉTAPE 4 — ACTIVATION        Monitoring + push + PWA (2 minutes)
ÉTAPE 5 — DASHBOARD         Utilisation quotidienne (Day 1+)
ÉTAPE 6 — UPGRADE           Contextuel, quand le merchant est prêt
```

---

## ÉTAPE 0 — DÉCOUVERTE (Shopify App Store)

Le merchant découvre StoreMD sur le Shopify App Store. C'est notre vitrine.

### Ce qu'il voit

```
┌──────────────────────────────────────────────────────┐
│  SHOPIFY APP STORE — StoreMD                          │
│                                                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │  Your Shopify store health score                 │ │
│  │  in 60 seconds. Free.                            │ │
│  │                                                   │ │
│  │  [Add app]                                        │ │
│  └─────────────────────────────────────────────────┘ │
│                                                       │
│  Screenshots:                                         │
│  • Dashboard avec score 67/100, trend ↗ +9            │
│  • Issues list avec fixes 1-click                     │
│  • AI Ready score 34%                                 │
│                                                       │
│  Key benefits (3 max):                                │
│  • Health Score — speed, apps, code, listings          │
│  • One-Click Fixes — not just diagnosis, action       │
│  • AI Ready — ChatGPT Shopping compatibility          │
│                                                       │
│  Social proof:                                        │
│  "Analyzed 530+ app reviews to build the scanner"     │
│                                                       │
│  Pricing:                                             │
│  Free plan available                                  │
│                                                       │
└──────────────────────────────────────────────────────┘
```

### Ce qu'il NE voit PAS

- Un mur de 43 features
- Un pricing compliqué avec des footnotes
- "Schedule a demo"
- "Contact sales"
- Screenshots d'un dashboard vide

### Métriques cibles

| Métrique | Cible |
|----------|-------|
| App Store page → Install click | >15% conversion |
| Bounce rate page App Store | <60% |

---

## ÉTAPE 1 — INSTALLATION (0 secondes)

### Flow technique

```
Merchant clique "Add app"
    │
    ▼
Shopify redirige vers /api/v1/auth/install?shop=mystore.myshopify.com
    │
    ▼
Backend valide le domain, génère state, redirige vers Shopify OAuth consent
    │
    ▼
Merchant voit les permissions demandées :
    "StoreMD wants to access:
     • Products (read and write)
     • Themes (read and write)
     • Orders (read only)
     • Online store content (read only)"
    │
    ▼
Merchant clique "Install app"
    │
    ▼
Shopify redirige vers /api/v1/auth/callback
    │
    ▼
Backend échange code → token, chiffre Fernet, crée session
    │
    ▼
Redirect → /onboarding (premier install) ou /dashboard (réinstall)
```

### Ce que le merchant fait

**RIEN.** Il clique "Add app", accepte les permissions, et il est dans l'app. Pas de :
- Signup
- Mot de passe
- Vérification email
- Configuration

### Données récupérées automatiquement pendant l'install

L'OAuth callback récupère tout ce dont l'agent a besoin pour le premier scan :

```python
# Récupéré automatiquement via Shopify API dans le callback
store_info = {
    "name": "My Store",                    # shop.name
    "domain": "mystore.myshopify.com",     # shop.primaryDomain
    "theme": "Dawn 15.0",                  # themes(roles: MAIN)
    "products_count": 847,                 # shop.productsCount
    "apps_count": 14,                      # appInstallations.totalCount
    "plan": "shopify",                     # shop.plan
    "currency": "USD",                     # shop.currencyCode
    "country": "US",                       # shop.billingAddress.countryCodeV2
}
# → Stocké dans la table stores
# → Le scan peut démarrer immédiatement
```

### Métriques cibles

| Métrique | Cible |
|----------|-------|
| Install → App open | >90% (pas de friction post-install) |
| Temps d'installation | <10 secondes |

---

## ÉTAPE 2 — PREMIER SCAN AUTOMATIQUE (0-90 secondes)

### Déclenchement

DÈS que l'app s'ouvre sur `/onboarding`, le scan se lance **SANS que le merchant clique**. Le frontend appelle `POST /api/v1/stores/{store_id}/scans` automatiquement avec `modules: ["health", "listings", "agentic"]`.

### Ce que le merchant voit

```
┌──────────────────────────────────────────────────────┐
│                                                       │
│   🔍 Scanning your store...                           │
│                                                       │
│   ████████████░░░░░░░░  62%                          │
│                                                       │
│   ✅ Theme analyzed (Dawn 15.0)                       │
│   ✅ 12 apps detected                                 │
│   ✅ 847 products scanned                              │
│   ⏳ Checking app impact on speed...                  │
│   ⏳ Detecting residual code...                       │
│                                                       │
│   💡 Did you know? The average Shopify store has      │
│      14 apps, each adding 200-500ms to load time.    │
│                                                       │
└──────────────────────────────────────────────────────┘
```

### Implémentation frontend

```tsx
// app/onboarding/page.tsx

"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ScanProgress } from "@/components/scan/ScanProgress";
import { ScoreReveal } from "@/components/scan/ScoreReveal";

export default function OnboardingPage() {
  const [scan, setScan] = useState<Scan | null>(null);
  const [phase, setPhase] = useState<"scanning" | "reveal" | "setup">("scanning");

  // Auto-trigger scan on mount
  useEffect(() => {
    async function startScan() {
      const store = await api.stores.getCurrent();
      const newScan = await api.scans.create({
        storeId: store.id,
        modules: ["health", "listings", "agentic"],
      });
      setScan(newScan);
      pollScanStatus(newScan.id);
    }
    startScan();
  }, []);

  // Poll scan status every 3 seconds
  async function pollScanStatus(scanId: string) {
    const interval = setInterval(async () => {
      const updated = await api.scans.get(scanId);
      setScan(updated);
      if (updated.status === "completed" || updated.status === "failed") {
        clearInterval(interval);
        setPhase("reveal");
      }
    }, 3000);
  }

  if (phase === "scanning") {
    return <ScanProgress scan={scan} />;
  }

  if (phase === "reveal") {
    return <ScoreReveal scan={scan} onContinue={() => setPhase("setup")} />;
  }

  return <MonitoringSetup onComplete={() => router.push("/dashboard")} />;
}
```

### Progress updates

Le frontend poll le status du scan toutes les 3 secondes. Le backend met à jour le scan en DB au fur et à mesure :

```python
# Dans l'orchestrateur, après chaque groupe de scanners
async def update_scan_progress(scan_id: str, step: str, progress: int):
    await supabase.table("scans").update({
        "metadata": {
            "current_step": step,
            "progress": progress,
        }
    }).eq("id", scan_id).execute()

# Groupe 1 terminé → progress 40%
# Groupe 2 terminé → progress 70%
# Analyse Claude → progress 90%
# Save → progress 100%, status "completed"
```

### Facts pendant le scan

5 facts en rotation (un à la fois, change toutes les 10 secondes) :

```typescript
const SCAN_FACTS = [
  "Did you know? The average Shopify store has 14 apps, each adding 200-500ms to load time.",
  "Stores that load in under 2 seconds convert 2x better than stores at 4 seconds.",
  "73% of Shopify stores have residual code from uninstalled apps.",
  "The European Accessibility Act requires online stores to be accessible. Fines up to €250,000.",
  "AI shopping agents (ChatGPT, Copilot) can now buy directly from Shopify stores.",
];
```

### Edge cases

| Situation | Comportement |
|-----------|-------------|
| Scan échoue | Afficher "Scan encountered an error. Retrying..." + auto-retry 1 fois |
| Scan timeout (>3 min) | Afficher "Taking longer than usual..." + bouton "Continue anyway" qui mène au dashboard |
| Scan partiel | Afficher les résultats disponibles + warning "Some checks couldn't be completed" |
| Store avec 0 produits | Scan health only (pas de listings/agentic), message "Add products to unlock more features" |
| Réinstallation (merchant revient) | Skip l'onboarding → redirect vers `/dashboard` directement |

### Métriques cibles

| Métrique | Cible |
|----------|-------|
| Scan completion rate | >95% |
| Time-to-first-value | <90 secondes |
| Abandon pendant le scan | <5% |

---

## ÉTAPE 3 — AHA MOMENT (90 secondes)

Le scan est terminé. Le merchant voit son score pour la PREMIÈRE fois. C'est LE moment critique.

### Ce que le merchant voit

```
┌──────────────────────────────────────────────────────┐
│                                                       │
│   Your Store Health Score                             │
│                                                       │
│            ┌───────┐                                  │
│            │  58   │  /100                            │
│            │ ████░ │                                  │
│            └───────┘                                  │
│     Mobile: 43/100    Desktop: 72/100                 │
│                                                       │
│   ⚠️ 3 critical issues found                         │
│                                                       │
│   ┌─────────────────────────────────────────────────┐│
│   │ 🔴 App "Privy" injects 340KB of unminified JS  ││
│   │    Impact: +1.8s load time                       ││
│   │    → Uninstall or replace with lighter alt       ││
│   └─────────────────────────────────────────────────┘│
│                                                       │
│   ┌─────────────────────────────────────────────────┐│
│   │ 🔴 3 ghost scripts from uninstalled apps        ││
│   │    Impact: +0.6s load time                       ││
│   │    → Remove residual code [1-click fix]          ││
│   └─────────────────────────────────────────────────┘│
│                                                       │
│   ┌─────────────────────────────────────────────────┐│
│   │ 🟡 12 products missing alt text                 ││
│   │    Impact: SEO penalty                           ││
│   │    → Generate alt text [1-click fix]             ││
│   └─────────────────────────────────────────────────┘│
│                                                       │
│   ┌──────────────────────────────────────────────┐   │
│   │ 🟢 Enable weekly monitoring (Free)           │   │
│   │    Get alerts when your score drops           │   │
│   └──────────────────────────────────────────────┘   │
│                                                       │
└──────────────────────────────────────────────────────┘
```

### Principes du Aha moment

1. **Score simple** — Un nombre. Pas un rapport. Le merchant comprend immédiatement.
2. **Top 3 only** — Pas tous les problèmes. Les 3 plus impactants. Triés par impact décroissant.
3. **Impact en chiffres** — "+1.8s load time" pas "slow". "$9.99/month" pas "unnecessary cost".
4. **Fix actionable** — Chaque issue a un bouton d'action. "1-click fix" si auto_fixable.
5. **CTA monitoring** — Le bouton "Enable monitoring" est le pont vers l'engagement long terme.

### Le merchant découvre des choses qu'il ne savait PAS

C'est ça le "aha" : le merchant apprend quelque chose de nouveau sur son store.

```
"Je ne savais pas que Privy ajoutait 1.8 secondes."
"Je ne savais pas que j'avais du code mort de 3 apps désinstallées."
"Je ne savais pas que 12 produits n'avaient pas d'alt text."
"Je ne savais pas que mon store n'était prêt qu'à 34% pour ChatGPT."
```

### Métriques cibles

| Métrique | Cible |
|----------|-------|
| Aha moment → Continue (click monitoring CTA) | >70% |
| At least 1 fix applied during onboarding | >30% |

---

## ÉTAPE 4 — ACTIVATION MONITORING (2 minutes)

Le merchant clique "Enable weekly monitoring". 3 questions, c'est tout.

### Écran

```
┌──────────────────────────────────────────────────────┐
│                                                       │
│   Set up monitoring                                   │
│                                                       │
│   1. Send alerts to:                                  │
│      ┌──────────────────────────────────────┐        │
│      │ john@mystore.com                      │        │
│      └──────────────────────────────────────┘        │
│      (pre-filled from Shopify)                        │
│                                                       │
│   2. Alert me when score drops by:                    │
│      ○ 3 points  ● 5 points  ○ 10 points             │
│      "We'll compare each scan to your store's         │
│       normal score."                                  │
│                                                       │
│   3. Install StoreMD on your phone?                   │
│      Get push notifications and access                │
│      your score in one tap.                           │
│      [Add to home screen]    [Not now]                │
│                                                       │
│   ┌──────────────────────────────────────────────┐   │
│   │           [Save & Go to Dashboard →]          │   │
│   └──────────────────────────────────────────────┘   │
│                                                       │
└──────────────────────────────────────────────────────┘
```

### Implémentation

```tsx
// components/onboarding/MonitoringSetup.tsx

interface MonitoringSetupProps {
  onComplete: () => void;
}

function MonitoringSetup({ onComplete }: MonitoringSetupProps) {
  const [email, setEmail] = useState(merchant.email); // pre-filled
  const [threshold, setThreshold] = useState(5);       // default
  const { canInstall, install } = useInstallPrompt();
  const { subscribe } = usePushNotifications();

  async function handleSave() {
    // 1. Sauvegarder les préférences
    await api.stores.updateSettings({
      notification_email: email,
      alert_threshold: threshold,
    });

    // 2. Marquer l'onboarding comme terminé
    await api.merchants.completeOnboarding();

    // 3. Redirect vers le dashboard
    onComplete();
  }

  async function handleInstallPWA() {
    const installed = await install();
    if (installed) {
      await subscribe(); // Demander la permission push
    }
  }

  return (
    <div>
      {/* Question 1 — Email */}
      <Input
        data-testid="alert-email"
        label="Send alerts to:"
        value={email}
        onChange={setEmail}
        type="email"
      />

      {/* Question 2 — Threshold */}
      <RadioGroup
        data-testid="alert-threshold"
        label="Alert me when score drops by:"
        value={threshold}
        onChange={setThreshold}
        options={[
          { value: 3, label: "3 points (sensitive)" },
          { value: 5, label: "5 points (recommended)" },
          { value: 10, label: "10 points (only major drops)" },
        ]}
      />

      {/* Question 3 — PWA */}
      {canInstall && (
        <div data-testid="install-pwa">
          <p>Install StoreMD on your phone?</p>
          <Button onClick={handleInstallPWA}>Add to home screen</Button>
          <Button variant="ghost">Not now</Button>
        </div>
      )}

      {/* Save */}
      <Button onClick={handleSave} className="w-full">
        Save & Go to Dashboard →
      </Button>
    </div>
  );
}
```

### "Not now" est toujours visible

Le merchant peut skip la question PWA. Il peut aussi skip TOUT le setup (bouton discret "Skip setup" en bas). Dans ce cas, les defaults s'appliquent : email Shopify + seuil 5 points + pas de push.

### Métriques cibles

| Métrique | Cible |
|----------|-------|
| Setup completion | >85% |
| PWA install rate (parmi ceux qui voient le prompt) | >25% |
| Push notifications enabled | >20% |

---

## ÉTAPE 5 — DASHBOARD QUOTIDIEN (Day 1+)

Le merchant ouvre l'app (PWA ou Shopify Admin). Il est sur le dashboard.

### Premier jour

```
┌──────────────────────────────────────────────────────┐
│  📊 Health  │  📝 Listings  │  🤖 AI Ready  │  ⚙️   │
│                                                       │
│  Score: 58/100                                        │
│  Mobile: 43    Desktop: 72                            │
│  (First scan — no trend yet)                          │
│                                                       │
│  3 critical issues                                    │
│  ┌───────────────────────────────────────────────┐   │
│  │ 🔴 Privy 340KB JS — +1.8s        [Fix →]     │   │
│  │ 🔴 3 ghost scripts — +0.6s       [Fix →]     │   │
│  │ 🟡 12 missing alt text            [Fix →]     │   │
│  └───────────────────────────────────────────────┘   │
│                                                       │
│  Next scan: Monday 4 AM                               │
│                                                       │
└──────────────────────────────────────────────────────┘
```

### Après 1 semaine

```
┌──────────────────────────────────────────────────────┐
│  📊 Health  │  📝 Listings  │  🤖 AI Ready  │  ⚙️   │
│                                                       │
│  Score: 67/100    ↗ +9 since last week                │
│  Mobile: 52    Desktop: 81                            │
│                                                       │
│  This week:                                           │
│  ✅ 3 ghost scripts removed (you approved Tue)        │
│  ✅ Alt text generated for 12 products                │
│  ⚠️ App "Reviews+" updated yesterday                  │
│     Your mobile score dropped from 67 to 63.          │
│     → Investigate                                     │
│                                                       │
│  Next recommended action:                             │
│  "Your store is 34% ready for ChatGPT Shopping.       │
│   12 products missing GTIN. Fix now →"                │
│                                                       │
│  [Score trend chart — 7 jours]                        │
│                                                       │
└──────────────────────────────────────────────────────┘
```

### L'agent met en avant UNE action prioritaire par jour

Pas 10 recommandations. UNE. La plus impactante. Le merchant n'est pas submergé.

```python
async def get_top_action(store_id: str) -> str:
    """Retourne LA recommandation la plus importante aujourd'hui."""
    # 1. Issues critical non résolues
    critical = await get_unresolved_issues(store_id, severity="critical")
    if critical:
        return critical[0].fix_description

    # 2. Score drop récent
    if await detect_recent_drop(store_id):
        return "Your score dropped recently. Check what changed."

    # 3. Agentic readiness (si score < 50%)
    agentic = await get_agentic_score(store_id)
    if agentic and agentic.score < 50:
        top_check = get_worst_agentic_check(agentic)
        return f"Your store is {agentic.score}% ready for ChatGPT Shopping. {top_check.fix}."

    # 4. Listing avec le plus de potentiel
    priority_listing = await get_top_priority_listing(store_id)
    if priority_listing:
        return f"Product '{priority_listing.title}' has a score of {priority_listing.score}/100 but generates ${priority_listing.revenue_30d}/month. Improving it could boost conversions."

    return "Your store is in good shape. Next scan scheduled."
```

### Métriques cibles

| Métrique | Cible |
|----------|-------|
| Day 1 retention (revient le lendemain) | >60% |
| Day 7 retention (revient après 1 semaine) | >40% |
| Day 30 retention | >25% |
| Issues resolved per week | >2 |

---

## ÉTAPE 6 — UPGRADE (quand le merchant est prêt)

### Pas de paywall bloquant

Le Free tier est FONCTIONNEL. Le merchant voit la valeur avant de payer. L'upgrade est suggéré EN CONTEXTE, quand le merchant atteint une limite.

### Triggers d'upgrade (contextuel, pas agressif)

| Trigger | Message | Plan suggéré |
|---------|---------|-------------|
| 2/2 scans utilisés | "You've used 2/2 scans this month. Upgrade for weekly scans." | Starter $39 |
| 5/5 product analyses | "You've analyzed 5/5 products. Upgrade for 100." | Starter $39 |
| Click sur Browser tab (Free/Starter) | "Browser Tests require Pro. See your store like a customer." | Pro $99 |
| Click sur Bot Filter (Free) | "Bot Traffic Filter requires Pro." | Pro $99 |
| Click sur Bulk Operations (Free/Starter) | "Bulk Operations require Pro." | Pro $99 |
| Merchant a 3+ stores | "Manage all your stores from one dashboard." | Pro $99 |
| Merchant a 5+ stores | "Agency plan supports up to 10 stores with white-label." | Agency $249 |

### Format de l'upgrade suggestion

```
┌──────────────────────────────────────────────────────┐
│  You've used 2/2 scans this month.                    │
│  Upgrade to Starter ($39/month) for weekly scans.     │
│                                                       │
│  [Upgrade →]    [Maybe later]                         │
└──────────────────────────────────────────────────────┘
```

- Pas de popup fullscreen
- Pas de countdown timer
- Pas de "limited time offer"
- "Maybe later" ferme le message (pas "Cancel" — framing négatif)
- Le message revient seulement quand le merchant atteint la limite à nouveau

### Métriques cibles

| Métrique | Cible |
|----------|-------|
| Free → Paid conversion | >12% (au-dessus de la moyenne SaaS 8%) |
| Time to upgrade | <14 jours |
| Upgrade from scan limit | >40% des upgrades |
| Upgrade from feature lock | >30% des upgrades |
| Churn M1 (après upgrade) | <8% |

---

## CROSS-SELL (dans le parcours)

Le cross-sell est CONTEXTUEL, pas un popup générique.

### StoreMD → ProfitPilot

```
Trigger:    StoreMD détecte des chargebacks dans les données du store
            OU les app costs sont élevés ($287/month en apps)

Message:
  "StoreMD detected 4 chargebacks this month ($320 lost).
   ProfitPilot can prevent them AND show your real profit.
   → Learn more"

Placement:  In-app banner en haut du dashboard, dismissible
Timing:     Après le 2ème scan (pas au premier — trop tôt)
```

### StoreMD → LeadQuiz

```
Trigger:    StoreMD voit du trafic (>5K visitors/mois) mais faible conversion (<1.5%)

Message:
  "Your store gets {visitors}/month but converts at {rate}%.
   A product quiz can guide visitors to the right product.
   Stores with quizzes convert 2-3x better.
   → Try LeadQuiz free"

Placement:  In-app banner, dismissible
Timing:     Après 2 semaines d'utilisation (le merchant fait confiance à StoreMD)
```

### Règles cross-sell

- Max 1 cross-sell visible à la fois
- Dismissible (le merchant clique X, ne revient pas pendant 30 jours)
- JAMAIS dans les push notifications
- JAMAIS dans les emails (sauf le weekly report, en footer discret)
- Toujours lié à une donnée RÉELLE du store (pas un pitch générique)

---

## DÉSINSTALLATION — LE DERNIER MOT

### Ce qui se passe

```
Merchant clique "Uninstall" dans Shopify Admin
    │
    ▼
Webhook app/uninstalled
    │
    ├── 1. Stripe subscription canceled IMMÉDIATEMENT
    ├── 2. Theme code cleaned (tout notre code supprimé)
    ├── 3. Mem0 memories deleted
    ├── 4. Email confirmation envoyé
    ├── 5. Data export disponible 30 jours
    └── 6. Data supprimée après 30 jours (GDPR)
```

### Email de désinstallation

```
Subject: StoreMD — Subscription canceled

Hi {name},

Your StoreMD subscription has been canceled. No future charges.

What we've done:
✅ Subscription canceled immediately
✅ All code removed from your theme
✅ Your data will be deleted in 30 days

[Export my data]

We'd love to know why you left:
[Too expensive] [Didn't see value] [Switched to another app]
[Too complicated] [Store closed] [Other]

— StoreMD
```

### Pourquoi c'est important

1. **Confiance** — Le merchant sait qu'il peut partir sans friction → il ose essayer
2. **Anti-concurrents** — "Unlike Privy, we don't charge you for 6 years after you leave"
3. **Feedback** — Le survey 1-clic donne des données pour améliorer le produit
4. **Réinstallation** — Un merchant bien traité à la sortie revient plus facilement

### Métriques

| Métrique | Cible |
|----------|-------|
| Uninstall survey response rate | >20% |
| Réinstallation dans 30 jours | >5% |

---

## MÉTRIQUES PARCOURS — RÉSUMÉ

| Étape | Métrique | Cible |
|-------|----------|-------|
| Découverte | App Store → Install | >15% |
| Installation | Install → App open | >90% |
| Premier scan | Scan completion | >95% |
| Premier scan | Time-to-first-value | <90 secondes |
| Aha moment | Score reveal → Continue | >70% |
| Aha moment | At least 1 fix applied | >30% |
| Activation | Setup completion | >85% |
| Activation | PWA install | >25% |
| Activation | Push enabled | >20% |
| Dashboard | Day 1 retention | >60% |
| Dashboard | Day 7 retention | >40% |
| Upgrade | Free → Paid | >12% |
| Upgrade | Time to upgrade | <14 jours |
| Churn | M1 churn | <8% |
| Uninstall | Survey response | >20% |
