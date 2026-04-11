# COPY.md — Tous les textes StoreMD

> **Source de vérité pour tout le copy de l'app. EN ANGLAIS.**
> **Landing page, onboarding, dashboard, alertes, emails, pricing, errors.**
> **Tout texte affiché au merchant est ici. Pas d'improvisation dans le code.**

---

## PRINCIPES DE COPY

1. **Simple** — Le merchant n'est pas un dev. Pas de jargon technique. "Your store loads slowly because of an app" pas "Third-party script injection causes elevated CLS metrics."
2. **Actionable** — Chaque message dit quoi faire. "Remove this code" pas "Code residue detected."
3. **Specific** — Chiffres concrets. "+1.8s load time" pas "slow." "$9.99/month wasted" pas "unnecessary cost."
4. **Short** — Mobile-first. Le merchant lit sur un écran 375px. Chaque mot compte.
5. **Confident** — StoreMD est un expert. Pas de "maybe" ou "it seems like." "This app adds 1.8s" pas "This app might be affecting your speed."

---

## LANDING PAGE

### Hero

```
Headline:     Your Shopify store health score in 60 seconds. Free.
Subheadline:  StoreMD is an AI agent that monitors your store 24/7.
              Speed, apps, SEO, listings, AI readiness — one dashboard.
CTA:          Add to Shopify — Free
```

### How it works

```
Step 1:
  Title:    Install in 1 click
  Body:     Add StoreMD from the Shopify App Store.
            No signup, no configuration. Just click.

Step 2:
  Title:    Get your score in 60 seconds
  Body:     StoreMD scans your store automatically.
            Speed, apps, code, listings, AI readiness.
            Your health score appears in under a minute.

Step 3:
  Title:    Fix issues in 1 click
  Body:     Each issue comes with a clear fix.
            Alt text missing? Generated and applied in 1 click.
            Ghost code from old apps? Removed automatically.
```

### Feature cards

```
Card 1 — Store Health
  Title:    Health Score 24/7
  Body:     Your store gets a score out of 100.
            Mobile and desktop. Updated daily.
            Get alerts when it drops.

Card 2 — App Impact
  Title:    See which apps slow you down
  Body:     StoreMD measures the exact impact of each app
            on your load time. "Privy adds 1.8 seconds."
            Not guessing — measuring.

Card 3 — AI Ready
  Title:    Ready for ChatGPT Shopping?
  Body:     Shopify now sells through AI agents.
            StoreMD checks if your products are visible
            to ChatGPT, Copilot, and Gemini.
            "Your store is 34% ready."

Card 4 — Listings
  Title:    Optimize every product listing
  Body:     Score each product out of 100.
            Title, description, images, SEO.
            Fix the weakest ones first — prioritized by revenue.

Card 5 — Browser Tests
  Title:    See your store like a customer
  Body:     StoreMD simulates a real purchase path.
            Homepage → Product → Cart → Checkout.
            Measures real load times at each step.

Card 6 — One-Click Fixes
  Title:    Not just diagnosis. Action.
  Body:     Missing alt text? Generated and applied.
            Broken link? Redirect created.
            Ghost code? Removed.
            Preview before applying. Always reversible.
```

### Social proof

```
Line 1:   Built from 530+ competitor app reviews
Line 2:   Analyzed 600+ merchant pain points on Reddit
Line 3:   12 features no other Shopify app has
```

### Anti-app-bloat message

```
Title:    We practice what we preach
Body:     StoreMD tells you "you have too many apps."
          That's why StoreMD is ONE app with 5 modules —
          not 5 separate apps. Health, Listings, AI Ready,
          Compliance, and Browser Testing. One install.
```

### FAQ

```
Q: How long does a scan take?
A: About 60 seconds for the first scan.
   Daily scans run at 3 AM and don't interrupt anything.

Q: Will StoreMD slow down my store?
A: No. StoreMD reads your store data through the Shopify API.
   It never injects code into your theme (unless you use One-Click Fix,
   which only removes code, never adds it).

Q: What happens when I uninstall?
A: Your subscription is canceled immediately. No future charges.
   Any code changes we made are reversed. Zero residual code.
   Your data is deleted after 30 days.

Q: Do I need a developer?
A: No. Most fixes are 1-click or come with simple step-by-step instructions.
   A few advanced issues (like custom theme code) may need a developer.

Q: What's the AI Ready module?
A: Shopify now lets customers buy through ChatGPT, Copilot, and Gemini.
   StoreMD checks if your products have the data these AI agents need:
   barcodes, structured descriptions, proper categories.
   No other app does this.

Q: Is my data safe?
A: Yes. Your Shopify access token is encrypted.
   Your data is isolated — no other merchant can see it.
   We comply with GDPR and Shopify's data protection requirements.

Q: Can I cancel anytime?
A: Yes. Cancel in the Settings tab or through Shopify.
   Effective immediately. No cancellation fees.
```

### Footer CTA

```
Headline:     Your store deserves a doctor.
CTA:          Add to Shopify — Free
Subtext:      Free plan includes 1 full audit + 2 scans/month.
              No credit card required.
```

---

## ONBOARDING

### Scan progress screen

```
Title:        Scanning your store...
Progress:     ████████████░░░░░░░░  62%

Steps:
  ✅ Theme analyzed ({theme_name})
  ✅ {apps_count} apps detected
  ✅ {products_count} products scanned
  ⏳ Checking app impact on speed...
  ⏳ Detecting residual code...

Fact (rotating, one at a time):
  "Did you know? The average Shopify store has 14 apps, each adding 200-500ms to load time."
  "Stores that load in under 2 seconds convert 2x better than stores at 4 seconds."
  "73% of Shopify stores have residual code from uninstalled apps."
  "The European Accessibility Act now requires online stores to be accessible. Fines up to €250,000."
  "AI shopping agents (ChatGPT, Copilot) can now buy directly from Shopify stores."
```

### Score reveal

```
Title:          Your Store Health Score
Score display:  {score} /100
Breakdown:      Mobile: {mobile_score}/100    Desktop: {desktop_score}/100

Issues header:  ⚠️ {critical_count} critical issues found

Issue format:
  🔴 {severity_emoji} {title}
     Impact: {impact}
     → {fix_description}

Example:
  🔴 App "Privy" injects 340KB of unminified JS
     Impact: +1.8s load time
     → Uninstall or replace with a lighter alternative

  🔴 3 ghost scripts from uninstalled apps
     Impact: +0.6s load time
     → Remove residual code [1-click fix]

  🟡 12 products missing alt text (SEO impact)
     → Generate alt text [1-click fix]

CTA:            🟢 Enable weekly monitoring (Free)
                Get alerts when your score drops
```

### Monitoring setup (3 questions)

```
Question 1:
  Label:    Send alerts to:
  Default:  {merchant_email} (pre-filled from Shopify)
  Type:     email input

Question 2:
  Label:    Alert me when score drops below:
  Default:  -5 points
  Type:     slider (1-20 points)
  Help:     "We'll compare each scan to your store's normal score."

Question 3:
  Label:    Install StoreMD on your phone?
  Body:     Get push notifications. Access your score in one tap.
  CTA:      Add to home screen
  Skip:     "Not now" (always visible)
```

### Onboarding complete

```
Title:    You're all set! 🎉
Body:     StoreMD is now monitoring your store.
          Your next scan is scheduled for {next_scan_date}.
          You'll get an alert if anything changes.
CTA:      Go to Dashboard →
```

---

## DASHBOARD

### Tab labels

```
Health      → Store Health
Listings    → Listings
AI Ready    → AI Ready
Browser     → Browser Tests
Settings    → Settings (gear icon, no text on mobile)
```

### Score hero

```
Score:      {score} /100
Trend:      ↗ +{delta} since last week    (if positive)
            ↘ -{delta} since last week    (if negative)
            → Stable since last week       (if 0)
Breakdown:  Mobile: {mobile}/100  |  Desktop: {desktop}/100
Last scan:  {time_ago} ago
CTA:        [Scan now]  (if scans remaining)
            [Scan limit reached — Upgrade →]  (if 0 remaining)
```

### Issues list

```
Header:     {issues_count} issues found ({critical_count} critical)
Sort:       Most impactful first (default)

Empty state:
  Title:    No issues found
  Body:     Your store is in great shape. Next scan: {next_scan_date}.
  Icon:     ✅ (green checkmark)

Issue actions:
  [Fix →]       → Opens OneClickFix preview (if auto_fixable)
  [Dismiss]     → Mark as dismissed (with feedback reason)
  [Details]     → Expand to see full description

Feedback on dismiss:
  "Why are you dismissing this?"
  ○ Not relevant to my store
  ○ Too risky to change
  ○ I'll do it later
  ○ I disagree with the recommendation
  ○ Already fixed
  ○ Other
```

### Apps impact section

```
Title:      App Impact on Speed
Subtitle:   Total impact: +{total_ms}ms ({total_s}s)

Row format: {app_name}    {impact_ms}ms    {scripts_size}KB    [Details]
Sort:       Highest impact first

Footer:     These numbers show the estimated load time
            each app adds to your store.
```

### Agentic readiness (AI Ready tab)

```
Score:      Your store is {score}% ready for AI shopping

Check format:
  ✅ {check_name}                    (if pass)
  ❌ {check_name} — {affected} products need attention    (if fail)
  🟡 {check_name} — {affected} products partially ready   (if partial)

Checks:
  GTIN/Barcode present
  Key metafields filled (material, dimensions, weight)
  Structured product descriptions
  Schema markup on product pages
  Google product categories assigned
  Published to Shopify Catalog

Context:    Shopify now sells through ChatGPT, Copilot, and Gemini.
            Products without this data are invisible to AI agents.
            AI orders grew 15x in the past year.
```

### Browser tests (Browser tab — Pro)

```
Visual Store Test:
  Title:      Visual Changes Detected
  Body:       {diff_pct}% of your {device} homepage changed since last scan.
              Probable cause: {cause}
  Images:     [Before] [After] (side by side)

User Simulation:
  Title:      Purchase Path: {total_s}s total
  Steps:      Homepage        {time}s
              Collection      {time}s
              Product         {time}s  ⚠️ Bottleneck
              Add to Cart     {time}s
              Checkout        {time}s
  Bottleneck: {step_name}: {cause}

Locked state (Free/Starter):
  Title:      Browser Tests — Pro
  Body:       See your store exactly as customers see it.
              Visual change detection, real purchase path simulation,
              and accessibility testing in real browser conditions.
  CTA:        [Upgrade to Pro — $99/month]
```

### Weekly report banner (in-app)

```
Title:      Weekly Report — {date_range}
Body:       Score: {score} ({trend_emoji}{delta})
            {resolved_count} issues resolved · {new_count} new
Top action: {top_action_text}
CTA:        [View full report]  [Download PDF]
```

---

## NOTIFICATIONS

### Push notifications

```
Score drop:
  Title:    Score dropped {delta} points
  Body:     Your health score went from {old} to {new}. {cause}.

Critical issue:
  Title:    Critical issue detected
  Body:     {issue_title}. Impact: {impact}.

App update regression:
  Title:    {app_name} update affected your score
  Body:     Your {device} score dropped {delta} points after {app_name} updated.
```

### Email — Weekly report

```
Subject:    StoreMD Weekly Report — Score {score} ({trend_emoji}{delta})

Body:
  Hi {merchant_name},

  Here's your weekly store health report for {date_range}.

  HEALTH SCORE: {score}/100 ({trend_emoji}{delta} vs last week)
  Mobile: {mobile}/100 | Desktop: {desktop}/100

  THIS WEEK:
  ✅ {resolved} issues resolved
  ⚠️ {new} new issues detected

  TOP ACTION:
  {top_action_description}

  [Open Dashboard →]

  — StoreMD

  You received this because you have weekly reports enabled.
  [Manage notification preferences]
```

### Email — Uninstall confirmation

```
Subject:    StoreMD — Subscription canceled

Body:
  Hi {merchant_name},

  Your StoreMD subscription has been canceled. No future charges.

  What we've done:
  ✅ Subscription canceled immediately
  ✅ All code removed from your theme
  ✅ Your data will be deleted in 30 days

  Your scan history is available for export for 30 days.
  [Export my data]

  We'd love to know why you left:
  [Too expensive] [Didn't see value] [Switched to another app]
  [Too complicated] [Store closed] [Other]

  If you ever want to come back, just reinstall from the Shopify App Store.

  — StoreMD
```

---

## PRICING PAGE

```
Headline:     Simple pricing. No surprises.
Subheadline:  Start free. Upgrade when you need more.

FREE ($0/month):
  - 1 full health audit
  - 2 scans per month
  - 5 product analyses
  - Health score + trend
  - Fix recommendations
  CTA: Current plan (if active) / Add to Shopify (if new)

STARTER ($39/month):
  - Everything in Free
  - Weekly scans
  - 100 product analyses
  - App impact scanner
  - Residue detector
  - Ghost billing detector
  - One-click fixes (20/month)
  - Weekly email report
  - Agentic readiness score
  - Accessibility scanner
  CTA: Upgrade to Starter

PRO ($99/month):  ← MOST POPULAR badge
  - Everything in Starter
  - Daily scans
  - 1,000 product analyses
  - 3 stores
  - Bulk operations
  - Visual Store Test
  - Real User Simulation
  - Accessibility Live Test
  - Bot traffic filter
  - AI crawler monitor
  - Benchmark
  CTA: Upgrade to Pro

AGENCY ($249/month):
  - Everything in Pro
  - 10 stores
  - Unlimited product analyses
  - API access
  - White-label reports
  - Priority support
  CTA: Upgrade to Agency

Footer:
  All plans include:
  ✓ Instant cancellation, zero fees
  ✓ No code injected in your theme
  ✓ Data encrypted and isolated
  ✓ GDPR compliant

  "Unlike some apps, we don't charge you after you uninstall."
```

---

## ERROR MESSAGES (user-facing)

Messages affichés au merchant quand une erreur survient. Mappés aux ErrorCodes dans `docs/ERRORS.md`.

```
AUTH_JWT_INVALID:
  "Your session has expired. Please log in again."

AUTH_PLAN_REQUIRED:
  "This feature requires the {plan} plan. Upgrade to unlock it."

AUTH_RATE_LIMIT_EXCEEDED:
  "Too many requests. Please wait a moment and try again."

SCAN_ALREADY_RUNNING:
  "A scan is already in progress. Please wait for it to complete."

SCAN_LIMIT_REACHED:
  "You've used all your scans for this month. Upgrade for more."

SCAN_FAILED:
  "The scan encountered an error. We'll try again automatically."

SCAN_PARTIAL:
  "Scan completed, but some checks couldn't be performed. Results may be incomplete."

SHOPIFY_RATE_LIMIT:
  "Shopify is busy right now. Your scan will retry automatically."

SHOPIFY_TOKEN_EXPIRED:
  "We've lost access to your store. Please reinstall StoreMD."

FIX_APPLY_FAILED:
  "We couldn't apply this fix. Please try again or contact support."

FIX_ALREADY_APPLIED:
  "This fix has already been applied."

FIX_NOT_REVERTABLE:
  "This fix can't be undone. The original state is no longer available."

BILLING_CHECKOUT_FAILED:
  "Payment setup failed. Please try again."

BILLING_CUSTOMER_NOT_FOUND:
  "We couldn't find your billing account. Please contact support."

INTERNAL_ERROR:
  "Something went wrong. Please try again. If the problem persists, contact support."

OFFLINE:
  "You're offline. Showing the last available data."
```

---

## EMPTY STATES

```
No scans yet:
  Title:    No scans yet
  Body:     Run your first scan to see your store health score.
  CTA:      [Scan now]

No issues:
  Title:    All clear! ✅
  Body:     No issues detected. Your store is in great shape.
  Sub:      Next scan: {next_scan_date}

No apps detected:
  Title:    No third-party apps found
  Body:     Your store doesn't have any apps installed.
            That's actually great for performance!

No products (listings tab):
  Title:    No products to analyze
  Body:     Add products to your Shopify store first.

No browser tests (locked):
  Title:    Browser Tests — Pro plan
  Body:     See your store like a customer.
  CTA:      [Upgrade to Pro]

No notifications:
  Title:    No notifications yet
  Body:     You'll see alerts here when your score changes
            or issues are detected.
```

---

## MICROCOPY

```
Scan button:          Scan now
Fix button:           Fix →
Applied button:       ✅ Applied
Undo button:          Undo
Dismiss button:       Dismiss
Details button:       Details
Show all:             Show all {count} issues
Upgrade CTA:          Upgrade to {plan}
Cancel:               Maybe later  (never "Cancel" — negative framing)
Loading:              Scanning your store...
Refreshing:           Updating...
Saving:               Saving...
Time ago:             2h ago / 3 days ago / Just now
Score trend up:       ↗ +{n} since last week
Score trend down:     ↘ -{n} since last week
Score trend stable:   → Stable since last week
Plan badge:           PRO (on locked features)
Partial scan warning: ⚠️ Some checks couldn't be completed
```

---

## TONE RULES

```
DO:
  ✅ "Your store loads in 4.2 seconds. The average is 3.2 seconds."
  ✅ "This app adds 1.8 seconds to your load time."
  ✅ "12 products are missing alt text."
  ✅ "Remove this code to save 0.6 seconds."

DON'T:
  ❌ "Oops! Something went wrong!"           → Too casual
  ❌ "WARNING: Critical performance issue!"   → Too alarming
  ❌ "It seems like maybe there could be..."  → Too uncertain
  ❌ "Click here to learn more about..."      → Too vague
  ❌ "Awesome! Great job!"                    → Too enthusiastic
  ❌ "Your store sucks"                       → Obviously not
  ❌ Technical jargon (CLS, LCP, FCP, TTFB)  → Say "load time" or "speed"
```
