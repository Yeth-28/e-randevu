// DentalReserv — Service Worker
const CACHE_NAME = 'dental-v1';

self.addEventListener('install', e => {
    self.skipWaiting();
});

self.addEventListener('activate', e => {
    e.waitUntil(clients.claim());
});

// Push bildirimi geldiğinde
self.addEventListener('push', e => {
    if (!e.data) return;
    const data = e.data.json();
    e.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: '/static/icons/tooth-icon.png',
            badge: '/static/icons/tooth-badge.png',
            tag: data.type,
            renotify: true,
            vibrate: [200, 100, 200],
        })
    );
});

// Bildirimi tıklayınca paneli aç
self.addEventListener('notificationclick', e => {
    e.notification.close();
    e.waitUntil(
        clients.matchAll({ type: 'window' }).then(clientList => {
            for (const client of clientList) {
                if (client.url.includes('panel.localhost') && 'focus' in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow('http://panel.localhost:8000/');
            }
        })
    );
});