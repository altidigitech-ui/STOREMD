# PWA.md — Progressive Web App StoreMD

> **Service worker, manifest, push notifications, install prompt, offline mode.**
> **Le merchant installe StoreMD sur son téléphone et reçoit des alertes push.**

---

## POURQUOI PWA

Le merchant Shopify vérifie son store sur mobile entre deux réunions. Il ne va pas ouvrir le Shopify Admin → Apps → StoreMD à chaque fois. Avec la PWA :

1. **Install sur le home screen** — icône native, lance en fullscreen
2. **Push notifications** — "Your score dropped 5 points" sans ouvrir l'app
3. **Chargement rapide** — service worker cache les assets statiques
4. **Disponible offline** — le dernier score est visible même hors connexion

---

## MANIFEST

```json
// public/manifest.json

{
  "name": "StoreMD — Shopify Store Health",
  "short_name": "StoreMD",
  "description": "AI agent that monitors your Shopify store health 24/7",
  "start_url": "/dashboard?source=pwa",
  "display": "standalone",
  "orientation": "portrait",
  "background_color": "#ffffff",
  "theme_color": "#2563eb",
  "scope": "/",
  "icons": [
    {
      "src": "/icons/icon-72x72.png",
      "sizes": "72x72",
      "type": "image/png"
    },
    {
      "src": "/icons/icon-96x96.png",
      "sizes": "96x96",
      "type": "image/png"
    },
    {
      "src": "/icons/icon-128x128.png",
      "sizes": "128x128",
      "type": "image/png"
    },
    {
      "src": "/icons/icon-144x144.png",
      "sizes": "144x144",
      "type": "image/png"
    },
    {
      "src": "/icons/icon-152x152.png",
      "sizes": "152x152",
      "type": "image/png"
    },
    {
      "src": "/icons/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/icons/icon-384x384.png",
      "sizes": "384x384",
      "type": "image/png"
    },
    {
      "src": "/icons/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ],
  "screenshots": [
    {
      "src": "/screenshots/dashboard-mobile.png",
      "sizes": "375x812",
      "type": "image/png",
      "form_factor": "narrow",
      "label": "Store health dashboard"
    },
    {
      "src": "/screenshots/dashboard-desktop.png",
      "sizes": "1440x900",
      "type": "image/png",
      "form_factor": "wide",
      "label": "Store health dashboard"
    }
  ],
  "categories": ["business", "productivity"],
  "lang": "en",
  "dir": "ltr"
}
```

### Next.js metadata

```tsx
// app/layout.tsx

export const metadata: Metadata = {
  title: "StoreMD — Shopify Store Health",
  description: "AI agent that monitors your Shopify store health 24/7",
  manifest: "/manifest.json",
  themeColor: "#2563eb",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "StoreMD",
  },
  viewport: {
    width: "device-width",
    initialScale: 1,
    maximumScale: 1,
  },
};
```

```html
<!-- Ajouté automatiquement par Next.js via metadata, mais vérifier : -->
<link rel="manifest" href="/manifest.json" />
<meta name="theme-color" content="#2563eb" />
<link rel="apple-touch-icon" href="/icons/icon-192x192.png" />
<meta name="apple-mobile-web-app-capable" content="yes" />
<meta name="apple-mobile-web-app-status-bar-style" content="default" />
```

---

## SERVICE WORKER

### Stratégie de cache

```
Assets statiques (JS, CSS, images, fonts)  → Cache First (cache, puis network si miss)
API responses                              → Network First (network, puis cache si offline)
Pages HTML                                 → Network First
Push notification clicks                   → Network Only
```

### Implémentation

```javascript
// public/sw.js

const CACHE_NAME = "storemd-v1";
const STATIC_ASSETS = [
  "/",
  "/dashboard",
  "/manifest.json",
  "/icons/icon-192x192.png",
  "/icons/icon-512x512.png",
];

// ─── INSTALL ───
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// ─── ACTIVATE ───
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

// ─── FETCH ───
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // API calls → Network First
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Static assets → Cache First
  if (
    request.destination === "style" ||
    request.destination === "script" ||
    request.destination === "image" ||
    request.destination === "font"
  ) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // Pages → Network First
  event.respondWith(networkFirst(request));
});

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response("Offline", { status: 503 });
  }
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok && request.method === "GET") {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    return new Response(JSON.stringify({ error: { code: "OFFLINE", message: "You are offline" } }), {
      status: 503,
      headers: { "Content-Type": "application/json" },
    });
  }
}

// ─── PUSH NOTIFICATIONS ───
self.addEventListener("push", (event) => {
  if (!event.data) return;

  const data = event.data.json();
  const options = {
    body: data.body,
    icon: "/icons/icon-192x192.png",
    badge: "/icons/badge-72x72.png",
    vibrate: [200, 100, 200],
    tag: data.tag || "storemd-notification",
    renotify: true,
    data: {
      url: data.action_url || "/dashboard",
    },
    actions: [
      { action: "open", title: "Open Dashboard" },
      { action: "dismiss", title: "Dismiss" },
    ],
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// ─── NOTIFICATION CLICK ───
self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const url = event.notification.data?.url || "/dashboard";

  if (event.action === "dismiss") return;

  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((windowClients) => {
      // Si l'app est déjà ouverte → focus + navigate
      for (const client of windowClients) {
        if (client.url.includes("/dashboard") && "focus" in client) {
          client.focus();
          client.navigate(url);
          return;
        }
      }
      // Sinon → ouvrir un nouveau tab
      return clients.openWindow(url);
    })
  );
});
```

### Enregistrement dans Next.js

```tsx
// hooks/use-service-worker.ts

"use client";

import { useEffect } from "react";

export function useServiceWorker() {
  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;

    navigator.serviceWorker
      .register("/sw.js")
      .then((registration) => {
        console.log("SW registered:", registration.scope);

        // Vérifier les mises à jour toutes les heures
        setInterval(() => {
          registration.update();
        }, 60 * 60 * 1000);
      })
      .catch((error) => {
        console.error("SW registration failed:", error);
      });
  }, []);
}

// Utiliser dans le layout root
// app/layout.tsx
// <ServiceWorkerProvider /> ou appeler useServiceWorker() dans un client component
```

---

## PUSH NOTIFICATIONS

### Frontend — Subscription

```tsx
// hooks/use-push-notifications.ts

"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export function usePushNotifications() {
  const [permission, setPermission] = useState<NotificationPermission>(
    typeof window !== "undefined" ? Notification.permission : "default"
  );
  const [isSubscribed, setIsSubscribed] = useState(false);

  async function subscribe(): Promise<boolean> {
    // 1. Demander la permission
    const perm = await Notification.requestPermission();
    setPermission(perm);
    if (perm !== "granted") return false;

    // 2. Obtenir la subscription push
    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(
        process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY!
      ),
    });

    // 3. Envoyer la subscription au backend
    await api.notifications.subscribePush({
      subscription: subscription.toJSON(),
    });

    setIsSubscribed(true);
    return true;
  }

  async function unsubscribe(): Promise<void> {
    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();
    if (subscription) {
      await subscription.unsubscribe();
      await api.notifications.unsubscribePush();
      setIsSubscribed(false);
    }
  }

  return { permission, isSubscribed, subscribe, unsubscribe };
}

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)));
}
```

### Backend — Envoyer une notification push

```python
# app/services/push.py

from pywebpush import webpush, WebPushException
from app.config import settings

async def send_push_notification(
    subscription: dict,
    title: str,
    body: str,
    action_url: str = "/dashboard",
    tag: str = "storemd",
) -> bool:
    """Envoie une notification push via Web Push Protocol."""
    payload = json.dumps({
        "title": title,
        "body": body,
        "action_url": action_url,
        "tag": tag,
    })

    try:
        webpush(
            subscription_info=subscription,
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={
                "sub": f"mailto:{settings.VAPID_CONTACT_EMAIL}",
            },
        )
        return True

    except WebPushException as exc:
        if exc.response and exc.response.status_code == 410:
            # 410 Gone — subscription expirée, supprimer
            logger.info("push_subscription_expired", subscription=subscription.get("endpoint", "")[:50])
            await remove_push_subscription(subscription)
            return False

        logger.warning("push_send_failed", error=str(exc))
        return False
```

### VAPID Keys

```bash
# Générer les VAPID keys (à faire UNE fois)
# pip install py-vapid
python -c "
from py_vapid import Vapid
v = Vapid()
v.generate_keys()
print('Public:', v.public_key)
print('Private:', v.private_key)
"

# Env vars
VAPID_PUBLIC_KEY=BNx...       # Frontend (NEXT_PUBLIC_VAPID_PUBLIC_KEY)
VAPID_PRIVATE_KEY=MIx...     # Backend only
VAPID_CONTACT_EMAIL=contact@storemd.com
```

### Quand envoyer un push

| Situation | Push ? | Contenu |
|-----------|--------|---------|
| Score drop ≥ seuil | ✅ | "Score dropped from 67 to 62. Probable cause: Reviews+ update." |
| Issue critical détectée | ✅ | "Critical: App Privy injects 340KB. +1.8s load time." |
| App update avec régression | ✅ | "Reviews+ updated. Your mobile score dropped 4 points." |
| Weekly report prêt | ❌ Email | "Weekly Report: Score 67 (+9)." |
| Fix appliqué avec succès | ❌ In-app | "Fix applied: alt text added to 12 images." |
| New feature / changelog | ❌ Jamais | Pas de push marketing |
| Demande de review | ❌ Jamais | Interdit |
| Upgrade / pricing | ❌ Jamais | Interdit |

**Max 3 push par semaine** (configurable dans settings).

---

## INSTALL PROMPT

### Quand afficher le prompt

Pas immédiatement. Après le premier scan réussi (le merchant a vu la valeur) :

```tsx
// hooks/use-install-prompt.ts

"use client";

import { useState, useEffect } from "react";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export function useInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [canInstall, setCanInstall] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);

  useEffect(() => {
    // Vérifier si déjà installé (standalone mode)
    if (window.matchMedia("(display-mode: standalone)").matches) {
      setIsInstalled(true);
      return;
    }

    // Écouter l'événement beforeinstallprompt
    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      setCanInstall(true);
    };

    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  async function install(): Promise<boolean> {
    if (!deferredPrompt) return false;

    await deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;

    setDeferredPrompt(null);
    setCanInstall(false);

    if (outcome === "accepted") {
      setIsInstalled(true);
      return true;
    }
    return false;
  }

  return { canInstall, isInstalled, install };
}
```

### UI du prompt

Affiché dans l'onboarding (étape 3) et dans les settings :

```tsx
function InstallPrompt() {
  const { canInstall, isInstalled, install } = useInstallPrompt();

  if (isInstalled) {
    return (
      <div className="flex items-center gap-2 text-sm text-green-600">
        <CheckCircle className="w-4 h-4" />
        StoreMD is installed on your device
      </div>
    );
  }

  if (!canInstall) return null;

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
      <h4 className="text-sm font-medium text-blue-900">
        Install StoreMD on your device
      </h4>
      <p className="text-xs text-blue-700 mt-1">
        Get push notifications when your score drops.
        Access your dashboard in one tap.
      </p>
      <Button size="sm" className="mt-3" onClick={install}>
        Add to home screen
      </Button>
    </div>
  );
}
```

---

## OFFLINE MODE

### Ce qui fonctionne offline

| Fonctionnalité | Offline ? | Comment |
|----------------|-----------|---------|
| Voir le dernier score | ✅ | Cached par le service worker (API Network First) |
| Voir les dernières issues | ✅ | Cached |
| Voir le trend chart | ✅ | Cached |
| Lancer un nouveau scan | ❌ | Nécessite Shopify API (network) |
| Appliquer un fix | ❌ | Nécessite Shopify API (network) |
| Recevoir des push | ✅ | Push fonctionne même si l'app est fermée |
| Voir les settings | ✅ | Cached |

### Indicateur offline

```tsx
// hooks/use-online-status.ts

"use client";

import { useState, useEffect } from "react";

export function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(
    typeof window !== "undefined" ? navigator.onLine : true
  );

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  return isOnline;
}
```

```tsx
// Afficher un banner quand offline
function OfflineBanner() {
  const isOnline = useOnlineStatus();
  if (isOnline) return null;

  return (
    <div className="bg-yellow-50 border-b border-yellow-200 px-4 py-2 text-center">
      <p className="text-xs text-yellow-800">
        You're offline. Showing cached data. Some features are unavailable.
      </p>
    </div>
  );
}
```

---

## MISE À JOUR DU SERVICE WORKER

Quand une nouvelle version du service worker est détectée :

```tsx
// hooks/use-service-worker.ts (ajout)

useEffect(() => {
  if (!("serviceWorker" in navigator)) return;

  navigator.serviceWorker.ready.then((registration) => {
    registration.addEventListener("updatefound", () => {
      const newWorker = registration.installing;
      if (!newWorker) return;

      newWorker.addEventListener("statechange", () => {
        if (newWorker.state === "installed" && navigator.serviceWorker.controller) {
          // Nouvelle version disponible
          showUpdateToast();
        }
      });
    });
  });
}, []);

function showUpdateToast() {
  toast({
    title: "Update available",
    description: "Refresh to get the latest version of StoreMD.",
    action: (
      <Button size="sm" variant="outline" onClick={() => window.location.reload()}>
        Refresh
      </Button>
    ),
    duration: Infinity, // Ne pas auto-dismiss
  });
}
```

---

## ENV VARS PWA

```bash
# Frontend (NEXT_PUBLIC_)
NEXT_PUBLIC_VAPID_PUBLIC_KEY=BNx...

# Backend (Railway)
VAPID_PRIVATE_KEY=MIx...
VAPID_CONTACT_EMAIL=contact@storemd.com
```

---

## FICHIERS

```
frontend/
├── public/
│   ├── manifest.json                # PWA manifest
│   ├── sw.js                        # Service worker
│   ├── icons/
│   │   ├── icon-72x72.png
│   │   ├── icon-96x96.png
│   │   ├── icon-128x128.png
│   │   ├── icon-144x144.png
│   │   ├── icon-152x152.png
│   │   ├── icon-192x192.png         # Required for PWA
│   │   ├── icon-384x384.png
│   │   ├── icon-512x512.png         # Required for PWA
│   │   └── badge-72x72.png          # Notification badge
│   └── screenshots/
│       ├── dashboard-mobile.png     # Install prompt preview
│       └── dashboard-desktop.png
│
├── src/
│   └── hooks/
│       ├── use-service-worker.ts
│       ├── use-push-notifications.ts
│       ├── use-install-prompt.ts
│       └── use-online-status.ts
│
backend/
├── app/
│   └── services/
│       └── push.py                  # Web Push (pywebpush)
```

---

## INTERDICTIONS

- ❌ Push pour demander une review → ✅ Interdit. Notifications = problèmes + diagnostics uniquement
- ❌ Push pour promouvoir un upgrade → ✅ Interdit. L'upgrade est contextuel dans le dashboard
- ❌ Push sans respecter la limite hebdo → ✅ `can_notify()` vérifie avant chaque envoi
- ❌ Service worker qui cache les POST → ✅ Cache uniquement les GET
- ❌ Forcer l'install prompt au premier load → ✅ Après le premier scan réussi
- ❌ VAPID private key dans le frontend → ✅ Backend only
- ❌ Ignorer les subscription 410 Gone → ✅ Supprimer la subscription expirée
- ❌ Push sans action_url → ✅ Chaque push mène à la page pertinente du dashboard
