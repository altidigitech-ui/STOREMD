"use client";

import { useCallback, useEffect, useState } from "react";

function urlBase64ToUint8Array(base64String: string): ArrayBuffer {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding)
    .replace(/-/g, "+")
    .replace(/_/g, "/");
  const rawData = window.atob(base64);
  const buffer = new ArrayBuffer(rawData.length);
  const view = new Uint8Array(buffer);
  for (let i = 0; i < rawData.length; i++) {
    view[i] = rawData.charCodeAt(i);
  }
  return buffer;
}

type Permission = "default" | "granted" | "denied";

export function usePushNotifications() {
  const [permission, setPermission] = useState<Permission>("default");
  const [isSubscribed, setIsSubscribed] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!("Notification" in window)) return;
    setPermission(Notification.permission as Permission);
  }, []);

  const subscribe = useCallback(async (): Promise<boolean> => {
    if (typeof window === "undefined") return false;
    if (!("Notification" in window) || !("serviceWorker" in navigator)) {
      return false;
    }

    const perm = (await Notification.requestPermission()) as Permission;
    setPermission(perm);
    if (perm !== "granted") return false;

    const vapidKey = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY;
    if (!vapidKey) return false;

    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidKey),
    });

    // A dedicated backend endpoint will pick up this payload. Until
    // it ships we POST to /api/v1/notifications/push-subscribe and
    // log failures rather than throw.
    try {
      await fetch("/api/v1/notifications/push-subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subscription: subscription.toJSON() }),
      });
    } catch {
      // no-op; we retry via settings later
    }

    setIsSubscribed(true);
    return true;
  }, []);

  const unsubscribe = useCallback(async (): Promise<void> => {
    if (!("serviceWorker" in navigator)) return;
    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();
    if (subscription) {
      await subscription.unsubscribe();
      setIsSubscribed(false);
    }
  }, []);

  return { permission, isSubscribed, subscribe, unsubscribe };
}
