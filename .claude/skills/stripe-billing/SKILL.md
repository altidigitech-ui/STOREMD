# Skill: Stripe Billing

> **Utilise ce skill quand tu travailles sur le billing :**
> **Checkout sessions, Customer Portal, webhooks Stripe, plans, usage metering.**

---

## QUAND UTILISER

- Implémenter/modifier `app/services/stripe_billing.py`
- Implémenter/modifier `app/api/routes/billing.py`
- Implémenter/modifier `app/api/routes/webhooks_stripe.py`
- Ajouter/modifier un plan ou ses limites
- Débugger un problème de facturation ou de plan

---

## LES 4 PLANS

| Plan | Stripe Price ID | Prix | Stores | Scans | Listings | Browser |
|------|----------------|------|--------|-------|----------|---------|
| Free | N/A (pas de sub) | $0 | 1 | 3/mois | 5 | ❌ |
| Starter | `price_starter_monthly` | $39/mois | 1 | ~4/mois (hebdo) | 100 | ❌ |
| Pro | `price_pro_monthly` | $99/mois | 3 | ~30/mois (daily) | 1000 | ✅ |
| Agency | `price_agency_monthly` | $249/mois | 10 | ~300/mois | Illimité | ✅ |

Les Price IDs sont des placeholders — remplacer par les vrais IDs Stripe en production.

```python
# app/config.py

STRIPE_PRICE_IDS: dict[str, str] = {
    "starter": settings.STRIPE_PRICE_STARTER,
    "pro": settings.STRIPE_PRICE_PRO,
    "agency": settings.STRIPE_PRICE_AGENCY,
}

PLAN_HIERARCHY: dict[str, int] = {
    "free": 0,
    "starter": 1,
    "pro": 2,
    "agency": 3,
}
```

---

## SERVICE BILLING

```python
# app/services/stripe_billing.py

import stripe
from app.config import settings, STRIPE_PRICE_IDS, PLAN_HIERARCHY
from app.core.exceptions import BillingError, ErrorCode

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeBillingService:
    def __init__(self, supabase: SupabaseClient):
        self.supabase = supabase

    # ─── CHECKOUT ───

    async def create_checkout_session(
        self, merchant_id: str, plan: str, return_url: str
    ) -> str:
        """Crée une Stripe Checkout session. Retourne l'URL de checkout."""
        if plan not in STRIPE_PRICE_IDS:
            raise BillingError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Invalid plan: {plan}",
                status_code=400,
            )

        # Récupérer ou créer le Stripe customer
        customer_id = await self.get_or_create_customer(merchant_id)

        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                mode="subscription",
                line_items=[{
                    "price": STRIPE_PRICE_IDS[plan],
                    "quantity": 1,
                }],
                success_url=f"{return_url}?session_id={{CHECKOUT_SESSION_ID}}&status=success",
                cancel_url=f"{return_url}?status=canceled",
                subscription_data={
                    "metadata": {
                        "merchant_id": merchant_id,
                        "plan": plan,
                    },
                },
                allow_promotion_codes=True,
            )
            return session.url
        except stripe.error.StripeError as exc:
            raise BillingError(
                code=ErrorCode.BILLING_CHECKOUT_FAILED,
                message=f"Checkout failed: {str(exc)}",
                status_code=502,
            )

    # ─── CUSTOMER PORTAL ───

    async def create_portal_session(self, merchant_id: str, return_url: str) -> str:
        """Crée une Stripe Customer Portal session pour gérer l'abonnement."""
        merchant = await self.get_merchant(merchant_id)

        if not merchant.get("stripe_customer_id"):
            raise BillingError(
                code=ErrorCode.BILLING_CUSTOMER_NOT_FOUND,
                message="No Stripe customer found",
                status_code=404,
            )

        try:
            session = stripe.billing_portal.Session.create(
                customer=merchant["stripe_customer_id"],
                return_url=return_url,
            )
            return session.url
        except stripe.error.StripeError as exc:
            raise BillingError(
                code=ErrorCode.BILLING_PORTAL_FAILED,
                message=f"Portal failed: {str(exc)}",
                status_code=502,
            )

    # ─── CUSTOMER MANAGEMENT ───

    async def get_or_create_customer(self, merchant_id: str) -> str:
        """Récupère le Stripe customer ID ou en crée un."""
        merchant = await self.get_merchant(merchant_id)

        if merchant.get("stripe_customer_id"):
            return merchant["stripe_customer_id"]

        # Créer le customer Stripe
        customer = stripe.Customer.create(
            email=merchant["email"],
            metadata={"merchant_id": merchant_id},
        )

        # Stocker l'ID dans la DB
        await self.supabase.table("merchants").update({
            "stripe_customer_id": customer.id,
        }).eq("id", merchant_id).execute()

        return customer.id

    # ─── PLAN CHECKING ───

    async def check_plan_access(self, merchant_id: str, feature: str) -> bool:
        """Vérifie si le merchant a accès à une feature selon son plan."""
        from docs.FEATURES import FEATURE_PLANS  # ou app/config.py

        required_plan = FEATURE_PLANS.get(feature, "pro")
        merchant = await self.get_merchant(merchant_id)
        current_plan = merchant.get("plan", "free")

        return PLAN_HIERARCHY[current_plan] >= PLAN_HIERARCHY[required_plan]

    # ─── USAGE METERING ───

    async def increment_usage(
        self, merchant_id: str, store_id: str, usage_type: str
    ) -> dict:
        """Incrémente le compteur d'usage et vérifie la limite."""
        today = date.today()
        period_start = today.replace(day=1)
        period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        # Upsert le usage record
        result = await self.supabase.table("usage_records").upsert({
            "merchant_id": merchant_id,
            "store_id": store_id,
            "usage_type": usage_type,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "count": 1,  # sera incrémenté par le ON CONFLICT
            "limit_count": await self.get_usage_limit(merchant_id, usage_type),
        }, on_conflict="merchant_id,store_id,usage_type,period_start").execute()

        # Incrémenter le count
        record = result.data[0]
        new_count = record["count"] + 1
        await self.supabase.table("usage_records").update({
            "count": new_count,
        }).eq("id", record["id"]).execute()

        # Vérifier la limite
        limit = record["limit_count"]
        return {
            "count": new_count,
            "limit": limit,
            "remaining": max(0, limit - new_count),
            "exceeded": new_count > limit,
        }

    async def get_usage_limit(self, merchant_id: str, usage_type: str) -> int:
        """Retourne la limite d'usage selon le plan du merchant."""
        merchant = await self.get_merchant(merchant_id)
        plan = merchant.get("plan", "free")

        limits = {
            "scan": {"free": 3, "starter": 5, "pro": 31, "agency": 310},
            "listing_analysis": {"free": 5, "starter": 100, "pro": 1000, "agency": 999999},
            "browser_test": {"free": 0, "starter": 0, "pro": 31, "agency": 310},
            "one_click_fix": {"free": 0, "starter": 20, "pro": 100, "agency": 999999},
            "bulk_operation": {"free": 0, "starter": 0, "pro": 10, "agency": 999999},
        }

        return limits.get(usage_type, {}).get(plan, 0)

    # ─── CANCEL ───

    async def cancel_subscription(self, merchant_id: str):
        """Annule immédiatement l'abonnement (app uninstall)."""
        merchant = await self.get_merchant(merchant_id)
        sub_id = merchant.get("stripe_subscription_id")

        if sub_id:
            try:
                stripe.Subscription.cancel(sub_id)
                logger.info("subscription_canceled", merchant_id=merchant_id)
            except stripe.error.StripeError as exc:
                logger.error("subscription_cancel_failed",
                             merchant_id=merchant_id, error=str(exc))

        # Mettre à jour le plan en DB
        await self.supabase.table("merchants").update({
            "plan": "free",
            "stripe_subscription_id": None,
        }).eq("id", merchant_id).execute()

    # ─── HELPERS ───

    async def get_merchant(self, merchant_id: str) -> dict:
        result = await self.supabase.table("merchants").select(
            "id, email, plan, stripe_customer_id, stripe_subscription_id"
        ).eq("id", merchant_id).single().execute()
        return result.data
```

---

## API ROUTES

```python
# app/api/routes/billing.py

from app.models.schemas import CheckoutRequest, CheckoutResponse

@router.post("/billing/checkout")
async def create_checkout(
    request: CheckoutRequest,
    merchant: Merchant = Depends(get_current_merchant),
    billing: StripeBillingService = Depends(get_billing_service),
):
    url = await billing.create_checkout_session(
        merchant_id=merchant.id,
        plan=request.plan,
        return_url=f"{settings.APP_URL}/dashboard/settings",
    )
    return CheckoutResponse(checkout_url=url)


@router.get("/billing/portal")
async def get_portal(
    merchant: Merchant = Depends(get_current_merchant),
    billing: StripeBillingService = Depends(get_billing_service),
):
    url = await billing.create_portal_session(
        merchant_id=merchant.id,
        return_url=f"{settings.APP_URL}/dashboard/settings",
    )
    return {"portal_url": url}
```

```python
# Schemas
class CheckoutRequest(BaseModel):
    plan: str = Field(..., pattern="^(starter|pro|agency)$")

class CheckoutResponse(BaseModel):
    checkout_url: str
```

---

## WEBHOOKS STRIPE

### Events à gérer

| Event | Ce qu'on fait |
|-------|-------------|
| `checkout.session.completed` | Activer le plan, créer la subscription en DB |
| `invoice.paid` | Confirmer le paiement, reset usage counters |
| `invoice.payment_failed` | Marquer `past_due`, notifier le merchant |
| `customer.subscription.updated` | Plan change (upgrade/downgrade), mettre à jour en DB |
| `customer.subscription.deleted` | Annulation, revenir au plan Free |

### Handler

```python
# app/api/routes/webhooks_stripe.py

# La validation signature est dans SECURITY.md section 3

async def process_stripe_event(event_id: str):
    """Traite un event Stripe (appelé en background via Celery)."""
    event_record = await get_webhook_event(event_id)
    event_type = event_record["topic"]
    payload = event_record["payload"]

    handlers = {
        "checkout.session.completed": handle_checkout_completed,
        "invoice.paid": handle_invoice_paid,
        "invoice.payment_failed": handle_invoice_payment_failed,
        "customer.subscription.updated": handle_subscription_updated,
        "customer.subscription.deleted": handle_subscription_deleted,
    }

    handler = handlers.get(event_type)
    if handler:
        await handler(payload)

    # Marquer comme traité
    await mark_webhook_processed(event_id)


async def handle_checkout_completed(payload: dict):
    """Nouveau checkout réussi → activer le plan."""
    session = payload["object"]
    merchant_id = session["subscription_data"]["metadata"]["merchant_id"]
    plan = session["subscription_data"]["metadata"]["plan"]
    subscription_id = session["subscription"]

    # Mettre à jour le merchant
    await supabase.table("merchants").update({
        "plan": plan,
        "stripe_subscription_id": subscription_id,
    }).eq("id", merchant_id).execute()

    # Créer la subscription en DB
    await supabase.table("subscriptions").insert({
        "merchant_id": merchant_id,
        "stripe_subscription_id": subscription_id,
        "stripe_customer_id": session["customer"],
        "stripe_price_id": session["line_items"]["data"][0]["price"]["id"],
        "plan": plan,
        "status": "active",
        "current_period_start": datetime.fromtimestamp(
            session["current_period_start"], UTC
        ).isoformat(),
        "current_period_end": datetime.fromtimestamp(
            session["current_period_end"], UTC
        ).isoformat(),
    }).execute()

    logger.info("plan_activated", merchant_id=merchant_id, plan=plan)


async def handle_invoice_paid(payload: dict):
    """Facture payée → reset les usage counters pour la nouvelle période."""
    invoice = payload["object"]
    subscription_id = invoice.get("subscription")
    if not subscription_id:
        return

    # Trouver le merchant
    sub = await supabase.table("subscriptions").select("merchant_id").eq(
        "stripe_subscription_id", subscription_id
    ).maybe_single().execute()

    if sub.data:
        merchant_id = sub.data["merchant_id"]
        # Les usage_records s'auto-reset par période (UNIQUE constraint)
        # Pas besoin de supprimer manuellement
        logger.info("invoice_paid", merchant_id=merchant_id)


async def handle_invoice_payment_failed(payload: dict):
    """Paiement échoué → marquer past_due, notifier."""
    invoice = payload["object"]
    subscription_id = invoice.get("subscription")
    if not subscription_id:
        return

    await supabase.table("subscriptions").update({
        "status": "past_due",
    }).eq("stripe_subscription_id", subscription_id).execute()

    # Notifier le merchant
    sub = await supabase.table("subscriptions").select("merchant_id").eq(
        "stripe_subscription_id", subscription_id
    ).maybe_single().execute()

    if sub.data:
        await send_notification(
            merchant_id=sub.data["merchant_id"],
            channel="email",
            title="Payment failed — update your card",
            body="Your last payment failed. Update your payment method to keep your plan active.",
            action_url=f"{settings.APP_URL}/dashboard/settings",
            category="billing_alert",
        )


async def handle_subscription_updated(payload: dict):
    """Plan modifié (upgrade/downgrade via Customer Portal)."""
    subscription = payload["object"]
    subscription_id = subscription["id"]
    new_price_id = subscription["items"]["data"][0]["price"]["id"]

    # Trouver le plan correspondant au price_id
    new_plan = next(
        (plan for plan, price_id in STRIPE_PRICE_IDS.items() if price_id == new_price_id),
        None,
    )

    if not new_plan:
        logger.warning("unknown_price_id", price_id=new_price_id)
        return

    # Mettre à jour
    await supabase.table("subscriptions").update({
        "plan": new_plan,
        "status": subscription["status"],
        "current_period_start": datetime.fromtimestamp(
            subscription["current_period_start"], UTC
        ).isoformat(),
        "current_period_end": datetime.fromtimestamp(
            subscription["current_period_end"], UTC
        ).isoformat(),
        "cancel_at_period_end": subscription.get("cancel_at_period_end", False),
    }).eq("stripe_subscription_id", subscription_id).execute()

    # Mettre à jour le merchant
    sub = await supabase.table("subscriptions").select("merchant_id").eq(
        "stripe_subscription_id", subscription_id
    ).maybe_single().execute()

    if sub.data:
        await supabase.table("merchants").update({
            "plan": new_plan,
        }).eq("id", sub.data["merchant_id"]).execute()

        logger.info("plan_changed", merchant_id=sub.data["merchant_id"],
                     new_plan=new_plan)


async def handle_subscription_deleted(payload: dict):
    """Subscription annulée → revenir au Free."""
    subscription = payload["object"]
    subscription_id = subscription["id"]

    await supabase.table("subscriptions").update({
        "status": "canceled",
        "canceled_at": datetime.now(UTC).isoformat(),
    }).eq("stripe_subscription_id", subscription_id).execute()

    sub = await supabase.table("subscriptions").select("merchant_id").eq(
        "stripe_subscription_id", subscription_id
    ).maybe_single().execute()

    if sub.data:
        await supabase.table("merchants").update({
            "plan": "free",
            "stripe_subscription_id": None,
        }).eq("id", sub.data["merchant_id"]).execute()

        logger.info("plan_canceled", merchant_id=sub.data["merchant_id"])
```

---

## FRONTEND — UPGRADE FLOW

```typescript
// components/shared/UpgradeModal.tsx

async function handleUpgrade(plan: "starter" | "pro" | "agency") {
  const response = await api.billing.createCheckout({ plan });
  // Redirect vers Stripe Checkout
  window.location.href = response.checkout_url;
}

// Après le retour de Stripe (success_url)
// Le webhook a déjà mis à jour le plan en DB
// Le frontend poll /api/v1/billing/status pour confirmer
```

```typescript
// Affichage contextuel de l'upgrade (pas de popup agressif)
function UsageBanner({ usage }: { usage: UsageRecord }) {
  if (usage.remaining > 0) return null;

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
      <p className="text-sm text-amber-800">
        You've used {usage.count}/{usage.limit} {usage.type} this month.{" "}
        <button onClick={() => openUpgradeModal()} className="underline font-medium">
          Upgrade for more →
        </button>
      </p>
    </div>
  );
}
```

---

## PLAN CHECK DANS LES ENDPOINTS

```python
# Pattern à utiliser dans chaque endpoint protégé par un plan

@router.get("/stores/{store_id}/visual/diff")
async def get_visual_diff(
    store_id: str,
    store: Store = Depends(get_current_store),
    billing: StripeBillingService = Depends(get_billing_service),
):
    # Vérifier le plan AVANT d'exécuter
    if not await billing.check_plan_access(store.merchant_id, "visual_store_test"):
        raise AppError(
            code=ErrorCode.PLAN_REQUIRED,
            message="Visual Store Test requires Pro plan or above",
            status_code=403,
            context={"feature": "visual_store_test", "required_plan": "pro"},
        )
    # ... exécuter la feature
```

---

## INTERDICTIONS

- ❌ `STRIPE_SECRET_KEY` dans le frontend → ✅ Backend only, `PUBLISHABLE_KEY` côté client
- ❌ Créer un checkout sans metadata `merchant_id` → ✅ Toujours inclure pour le webhook
- ❌ Modifier le plan sans passer par Stripe → ✅ Le plan change UNIQUEMENT via webhooks Stripe
- ❌ Charger le merchant après uninstall → ✅ Cancel la sub AVANT de marquer le merchant
- ❌ Bloquer le merchant sans notification → ✅ Toujours notifier avant downgrade
- ❌ Auto-submit le checkout → ✅ Le merchant clique, Stripe gère le paiement
- ❌ Hardcoder les Price IDs → ✅ Env vars via config.py
- ❌ Facturer après uninstall → ✅ Cancel immédiat dans le webhook `app/uninstalled`
