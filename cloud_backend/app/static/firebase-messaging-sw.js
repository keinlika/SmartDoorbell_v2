// firebase-messaging-sw.js
// Store this file in your static/ directory,
// but make sure it is served at:
// https://sentiosmarthome.com/firebase-messaging-sw.js

importScripts('https://www.gstatic.com/firebasejs/9.22.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.22.0/firebase-messaging-compat.js');

// ============================================================
// REPLACE THESE WITH YOUR REAL FIREBASE WEB APP VALUES
// ============================================================
const firebaseConfig = {
  apiKey: "YOUR_FIREBASE_API_KEY",
  authDomain: "YOUR_FIREBASE_AUTH_DOMAIN",
  projectId: "YOUR_FIREBASE_PROJECT_ID",
  storageBucket: "YOUR_FIREBASE_STORAGE_BUCKET",
  messagingSenderId: "YOUR_FIREBASE_MESSAGING_SENDER_ID",
  appId: "YOUR_FIREBASE_APP_ID"
};

firebase.initializeApp(firebaseConfig);

let messaging = null;
try {
  messaging = firebase.messaging();
} catch (err) {
  console.error('[SW] Firebase messaging init failed:', err);
}

// ============================================================
// HELPERS
// ============================================================
function resolveAppUrl(data = {}) {
  // Default to dashboard home
  const baseUrl = '/';

  // Optional deep-link support later
  if (data && data.event_id) {
    return `/?event_id=${encodeURIComponent(data.event_id)}`;
  }

  if (data && data.device_id) {
    return `/?device_id=${encodeURIComponent(data.device_id)}`;
  }

  return baseUrl;
}

function buildNotification(payload) {
  const notification = payload?.notification || {};
  const data = payload?.data || {};

  return {
    title: notification.title || 'Sentio Smart Home',
    options: {
      body: notification.body || 'New doorbell event detected.',
      icon: '/static/icons/icon-192x192.png',
      badge: '/static/icons/icon-badge.png',
      tag: data.tag || 'doorbell-notification',
      renotify: false,
      requireInteraction: false,
      data: {
        ...data,
        click_url: resolveAppUrl(data)
      },
      actions: [
        {
          action: 'view',
          title: 'View'
        },
        {
          action: 'dismiss',
          title: 'Dismiss'
        }
      ]
    }
  };
}

// ============================================================
// FIREBASE BACKGROUND MESSAGES
// ============================================================
if (messaging) {
  messaging.onBackgroundMessage((payload) => {
    console.log('[SW] Background message received:', payload);

    const { title, options } = buildNotification(payload);
    self.registration.showNotification(title, options);
  });
}

// ============================================================
// FALLBACK PUSH HANDLER
// Useful if your backend later sends raw Web Push payloads
// ============================================================
self.addEventListener('push', (event) => {
  if (!event.data) {
    return;
  }

  let payload = {};
  try {
    payload = event.data.json();
  } catch (err) {
    payload = {
      notification: {
        title: 'Sentio Smart Home',
        body: event.data.text()
      },
      data: {}
    };
  }

  const { title, options } = buildNotification(payload);
  event.waitUntil(self.registration.showNotification(title, options));
});

// ============================================================
// NOTIFICATION CLICK HANDLING
// ============================================================
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event.action, event.notification?.data);

  event.notification.close();

  if (event.action === 'dismiss') {
    return;
  }

  const targetUrl = event.notification?.data?.click_url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        try {
          const clientUrl = new URL(client.url);
          const desiredUrl = new URL(targetUrl, self.location.origin);

          // Focus an existing tab on same origin
          if (clientUrl.origin === desiredUrl.origin && 'focus' in client) {
            if ('navigate' in client && clientUrl.pathname + clientUrl.search !== desiredUrl.pathname + desiredUrl.search) {
              return client.navigate(desiredUrl.href).then(() => client.focus());
            }
            return client.focus();
          }
        } catch (err) {
          console.warn('[SW] Client URL match failed:', err);
        }
      }

      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});

// ============================================================
// OPTIONAL CLOSE EVENT
// ============================================================
self.addEventListener('notificationclose', () => {
  console.log('[SW] Notification closed');
});
