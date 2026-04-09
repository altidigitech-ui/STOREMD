# StoreMD — Context

> **Vision business complète de StoreMD.**
> **Claude Code lit ce fichier pour comprendre POURQUOI on construit chaque feature.**

---

## PROBLÈME

Les merchants Shopify souffrent de 5 douleurs invisibles qui leur coûtent de l'argent sans qu'ils le sachent :

**1. App bloat** — Le store moyen a 14 apps installées. Chaque app ajoute 200-500ms de load time. Un store à 4s au lieu de 2s perd ~$2,100/mois en conversions. Le merchant ne sait pas QUELLE app est responsable.

**2. Code mort** — Quand un merchant désinstalle une app, elle laisse du code résiduel dans le thème (scripts, liquid snippets, CSS). Ce code continue de ralentir le store. Personne ne le détecte.

**3. Facturation fantôme** — Certaines apps continuent de facturer via Shopify Billing après désinstallation. Le merchant paie sans le savoir.

**4. Listings non optimisés** — Descriptions vagues, alt text manquant, SEO inexistant, variantes mal structurées. Le merchant perd du trafic organique et des conversions sans le savoir.

**5. Non-préparé pour l'IA** — Shopify a lancé les Agentic Storefronts (mars 2026). Les merchants vendent maintenant dans ChatGPT, Microsoft Copilot, Google Gemini. AI orders en hausse de 15x depuis janvier 2025. Un store sans metafields remplis, sans GTIN, sans descriptions structurées est INVISIBLE pour les agents IA. AUCUNE app ne scanne ça.

**Données marché :**
- Store moyen : 3.2s de load time
- <50% des stores passent les Core Web Vitals
- $2,100/mois perdu pour un store à 4s vs 2s
- EAA (European Accessibility Act) en vigueur depuis juin 2025 : amendes 5K-250K€ pour les stores non conformes vendant en EU

---

## SOLUTION

StoreMD est un **agent IA** qui surveille la santé complète d'un store Shopify en continu. Pas un outil passif qui génère un rapport PDF. Un agent qui DÉTECTE, ANALYSE, AGIT et APPREND.

**Architecture agent 4 couches :**
1. **DÉTECTER** — Webhooks Shopify (app install/uninstall, product update, theme change), scans planifiés (cron), browser automation (Playwright)
2. **ANALYSER** — Claude API interprète les données + Mem0 fournit le contexte historique (préférences merchant, patterns temporels, intelligence cross-store)
3. **AGIR** — Notification push/email + recommandation en langage simple + fix en 1 clic via Shopify API
4. **APPRENDRE** — Le merchant accepte ou refuse chaque recommandation → feedback stocké dans Mem0 → chaque cycle est meilleur que le précédent (pattern Ouroboros)

**One-liner :** "Your Shopify store health score in 60 seconds. Free."

**Message anti-app-bloat :** StoreMD dit aux merchants "vous avez trop d'apps." On ne peut pas leur vendre 5 apps séparées. C'est pourquoi StoreMD est UN SEUL agent avec 5 modules. Cohérent avec le message.

---

## PERSONAS

### Merchant Solo ($10K-$100K/mois revenue)
- Gère son store seul ou avec 1-2 personnes
- N'a pas de développeur
- Installe des apps sur recommandation, ne sait pas lesquelles posent problème
- Veut un score simple et des actions claires
- **Plan cible :** Starter $39/mois

### Merchant Growth ($100K-$1M/mois)
- Équipe de 3-10 personnes
- A un dev freelance occasionnel
- 15-25 apps, certaines redondantes
- Se soucie du SEO, de la conversion, de la conformité
- **Plan cible :** Pro $99/mois

### Agence Shopify (gère 5-50 stores)
- Besoin de rapports clients professionnels
- Dashboard multi-stores
- White-label pour présenter aux clients
- **Plan cible :** Agency $249/mois

---

## 5 MODULES — 43 FEATURES

### Module 1 : Store Health (20 features)

Le cœur de StoreMD. Diagnostique la santé technique du store.

| # | Feature | Plan |
|---|---------|------|
| 1 | Health Score 24/7 — score /100 mobile + desktop | Free |
| 2 | Diagnostic 3 couches — Traffic → Engagement → Purchase | Free |
| 3 | Alertes régressives — push/email quand le score baisse | Starter |
| 4 | App Impact Scanner — impact de CHAQUE app individuellement | Starter |
| 5 | Bot Traffic Filter — sépare trafic humain vs bots | Pro |
| 6 | App Risk Monitor — alertes cross-store quand une app pose problème | Pro |
| 7 | Collection Backup auto — snapshot avant changement majeur | Starter |
| 8 | Content Theft Scanner — détecte si le contenu est copié (Phase 2) | Pro |
| 9 | Security Monitor — SSL, headers, permissions apps | Starter |
| 10 | AI Crawler Monitor — mesure trafic GPTBot, ClaudeBot, etc. | Pro |
| 11 | Benchmark concurrence — compare avec stores similaires | Pro |
| 12 | Fix Generator — recommandations en langage simple | Free |
| 13 | Weekly Report Push — rapport hebdo email/push | Starter |
| 14 | Uninstall Residue Detector — code mort d'apps désinstallées | Starter |
| 15 | Pixel Health Check — GA4, Meta Pixel, TikTok Pixel | Starter |
| 16 | App Update Tracker — alerte quand une app se met à jour | Pro |
| 17 | Permission Monitor — alerte quand une app change ses scopes | Pro |
| 18 | Code Weight Scanner — poids JS/CSS par source | Starter |
| 19 | Ghost Billing Detector — apps désinstallées qui facturent encore | Starter |
| 20 | Email Domain Health Monitor — SPF, DKIM, DMARC | Pro |

### Module 2 : Listings (14 features)

Ex-ListingLab, absorbé dans StoreMD. Optimise les listings produits.

| # | Feature | Plan |
|---|---------|------|
| 21 | Catalogue Scan — score /100 par listing | Free (5 produits) |
| 22 | Priorisation par impact revenue | Starter |
| 23 | Diagnostic par élément — titre, description, images, SEO | Free |
| 24 | Rewrite ciblé — réécrit ce qui est faible, garde ce qui marche | Starter |
| 25 | Bulk Import Intelligent — CSV → listings Shopify | Pro |
| 26 | Dead Listing Detector — 0 vues/ventes depuis 90 jours | Starter |
| 27 | Image Optimizer — compression, WebP, alt text auto | Starter |
| 28 | Product Variant Organizer — variantes mal structurées | Pro |
| 29 | SEO Engine — meta titles, descriptions, URL handles | Starter |
| 30 | Multi-langue — listings non-traduits dans les marchés activés | Pro |
| 31 | New Product Watch — webhook → analyse auto dès ajout produit | Starter |
| 32 | Benchmark catégorie — compare avec top performers du secteur | Pro |
| 33 | Bulk Operations — 50-500 listings en 1 clic | Pro |
| 34 | Zero Lock-in + Safe Mode — tout est réversible, preview avant apply | Free |

### Module 3 : Agentic Readiness (4 features)

EXCLUSIVITÉ MONDIALE. Personne ne fait ça. Source : Shopify Agentic Storefronts mars 2026.

| # | Feature | Plan |
|---|---------|------|
| 35 | Agentic Readiness Score — /100 compatibilité ChatGPT/Copilot/Gemini | Starter |
| 36 | Agentic Fix Generator — GTIN manquants, metafields vides, descriptions non-structurées | Starter |
| 37 | Agentic Monitoring — alerte si nouveau produit non-compatible IA | Pro |
| 38 | HS Code Validator — vérifie HS codes pour tarifs internationaux | Pro |

### Module 4 : Compliance & Fixes (3 features)

Source : StoreScan (9 scanners, 0 reviews), EAA 2025, données speed 2026.

| # | Feature | Plan |
|---|---------|------|
| 39 | Accessibility Scanner (EAA) — WCAG 2.1 en continu, amendes EU | Starter |
| 40 | Broken Links Scanner — liens cassés internes + externes, impact SEO | Starter |
| 41 | One-Click Fix Engine — transversal : alt text, redirects, code résiduel en 1 clic | Starter |

### Module 5 : Browser Automation (2 features + 1 extension)

EXCLUSIVITÉ MONDIALE. Playwright sur le store du merchant. Pas l'API — la RÉALITÉ vue par le client.

| # | Feature | Plan |
|---|---------|------|
| 42 | Visual Store Test — screenshots mobile+desktop, diff visuel entre scans | Pro |
| 43 | Real User Simulation — parcours Homepage→Checkout, temps réels, bottleneck | Pro |
| — | Accessibility Live Test — WCAG en rendu réel (extension du #39) | Pro |

---

## PRICING

| Plan | Prix | Stores | Scans | Listings | Browser |
|------|------|--------|-------|----------|---------|
| Free | $0 | 1 | 1 audit + 2/mois | 5 analyses | ❌ |
| Starter | $39/mois | 1 | Hebdomadaire | 100 produits | ❌ |
| Pro | $99/mois | 3 | Quotidien | 1000 produits, bulk ops | ✅ |
| Agency | $249/mois | 10 | Quotidien | Illimité, API | ✅ + white-label |

**Justification pricing :** StoreMD remplace StoreMD seul ($29) + ListingLab ($29) = $58/mois. Le Starter à $39 est MOINS CHER que les deux séparés. Plus de valeur, moins cher, une seule app.

**Unit economics cible :**
- CAC : <$50 (organique App Store + Reddit + content marketing)
- LTV : >$500 (churn <8% M1, ARPU ~$80)
- LTV/CAC : >10x
- Gross margin : >85% (Claude API ~$0.02/scan, Railway ~$20/mois, Supabase ~$25/mois)

---

## CONCURRENTS

### Directs

| Concurrent | Force | Faille exploitable |
|---|---|---|
| **StoreScan** (jan 2026, 0 reviews, $9.99-49.99) | 9 scanners, health score, rapports PDF | 0 traction, 1 dev seul, hébergé sur Render, PAS d'agent, PAS d'app impact, PAS de bot filter, PAS de monitoring continu |
| **Clawly** (mars 2026, 0 reviews, $9.99-79.99) | Framework IA généraliste Shopify | Le merchant doit configurer ses assistants lui-même, pas de features pré-configurées, modèle token-based |
| **TinyIMG, Thunder, EA Page Speed Booster** | Compression images, defer scripts, lazy loading | Optimisations aveugles, ne diagnostiquent pas le POURQUOI ("c'est l'app Privy qui injecte 340KB") |
| **Agences audit** ($500-$2,000) | Rapport one-shot PDF 20-50 pages | ONE-SHOT. Pas de monitoring continu. Le rapport expire le jour même. StoreMD fait ça en continu pour $39/mois. |
| **Overlays accessibilité** (accessiBe, Isonomy) | Widget par-dessus le code | Ne fixent PAS les problèmes, ajoutent un widget. Isonomy passé de gratuit à payant du jour au lendemain. Les overlays elles-mêmes ralentissent le store. |

### Features volées aux concurrents (et faites MIEUX)

| Feature | Volée à | Comment on fait mieux |
|---|---|---|
| Accessibility Scanner | StoreScan | Agent CONTINU avec alertes quand une app casse l'accessibilité, pas un scan one-shot |
| Broken Links Scanner | StoreScan | Continu + correction auto via One-Click Fix |
| One-Click Fixes | StoreScan | Pour TOUT : alt text, redirects, code résiduel, permissions — pas juste SEO basique |
| "Built for Shopify" badge | GoProfit, NoFraud | Objectif Day 1. Signal de confiance obligatoire. |

### 4 exclusivités mondiales (AUCUN concurrent)

1. **Agentic Readiness Scanner** — "ton store est prêt à 34% pour ChatGPT Shopping"
2. **Visual Store Test** — diff visuel screenshots mobile+desktop entre scans, cause identifiée
3. **Real User Simulation** — parcours achat complet, temps réels par étape, bottleneck avec cause
4. **Accessibility Live Test** — WCAG vérifié en rendu navigateur réel, pas HTML statique

---

## MOAT (pourquoi les merchants ne quittent JAMAIS)

**Après 6 mois d'utilisation :**
- 6 mois d'historique health score = le merchant voit l'évolution de son store
- Bot fingerprinting cross-store = détection plus précise que n'importe quel concurrent
- Code résiduel de 20 apps désinstallées identifié et nettoyé
- Accessibility score conforme EAA
- L'agent connaît les préférences du merchant (Mem0) — recommandations personnalisées, taux d'acceptation >80%
- Intelligence cross-store : "l'app X cause des problèmes sur 47 stores"
- **Impossible de partir sans perdre tout ça**

**Pour qu'un concurrent rattrape :**

| Ce qu'il devrait faire | Temps |
|---|---|
| Reconstruire l'architecture Mem0 + LangGraph | 3-6 mois |
| Accumuler 6 mois de données merchant | 6 mois (incompressible) |
| Construire du cross-store intelligence | 12 mois pour atteindre une masse utile |
| Implémenter le feedback loop Ouroboros | 2-3 mois + données d'entraînement |
| Obtenir "Built for Shopify" | 1-3 mois de review |
| **Total** | **12-18 mois de retard** |

---

## VALIDATION TERRAIN

| Métrique | Valeur |
|----------|--------|
| Threads Reddit scrapés | 12+ |
| Commentaires analysés | 600+ |
| Reviews concurrents Shopify App Store | 380+ |
| Concurrents analysés | 10+ |
| Données marché (APPWRK, Market Clarity) | Intégrées |
| Shopify Agentic Commerce (mars 2026) | AI orders x15, nouveau canal de vente |
| EAA enforcement (juin 2025) | Amendes 5K-250K€ |
| Tarifs US (de minimis mort, Section 122) | HS Code Validator |
| Shopify Tinker (mars 2026) | Analysé — pas de menace directe (crée des assets, ne diagnostique pas) |

---

## PARCOURS UTILISATEUR (résumé)

Détails dans `docs/ONBOARDING.md`.

**Principe :** Le merchant voit de la VALEUR en moins de 90 secondes. Pas un tutoriel. Pas un dashboard vide.

1. **Install** (0s) — Shopify OAuth, zéro signup, zéro mot de passe
2. **Premier scan auto** (0-90s) — Se lance DÈS l'ouverture, progress bar avec facts
3. **Aha moment** (90s) — Score /100 + 3 issues critiques + impact en secondes + fix 1-clic
4. **Activation monitoring** (2min) — 3 questions : email, seuil alerte, install PWA
5. **Dashboard quotidien** — Onglets Health / Listings / AI Ready. 1 action prioritaire par jour
6. **Upgrade contextuel** — "You've used 2/2 scans this month. Upgrade → $39/month." Pas de popup agressif.

**Métriques cibles :**
- Time-to-first-value : <90 secondes
- Onboarding completion : >85%
- Day 1 retention : >60%
- Day 7 retention : >40%
- Free → Paid conversion : >12%
- Churn M1 : <8%

---

## CROSS-SELL

| Depuis StoreMD | Vers | Trigger contextuel |
|---|---|---|
| StoreMD | ProfitPilot | StoreMD détecte des chargebacks ou app costs élevés ($287/mois en apps) |
| StoreMD | LeadQuiz | Store a du trafic (8K visitors/mois) mais faible conversion (<1.5%). Quiz convertit 2-3x mieux. |

---

## DÉSINSTALLATION

Principe : annulation instantanée, zéro facturation fantôme, zéro code résiduel. C'est aussi un argument de vente : "Unlike Privy, we don't charge you for 6 years after you leave."

1. Webhook `app/uninstalled` → arrêt IMMÉDIAT billing Stripe
2. Script cleanup → suppression de TOUT notre code du thème
3. Email confirmation avec export données 30 jours
4. Données supprimées après 30 jours (GDPR)

---

## OBJECTIFS M1 (avril 2026)

1. Backend core (scan engine, Shopify API client, auth OAuth, Stripe billing)
2. Module Store Health : 20 features opérationnelles
3. Module Listings : 14 features opérationnelles
4. Module Agentic Readiness : 4 features (MVP)
5. Frontend PWA : dashboard, onboarding, landing page SSR
6. Deploy Railway (backend + worker) + Vercel (frontend)
7. Soumission "Built for Shopify" badge
