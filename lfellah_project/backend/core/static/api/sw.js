// Service Worker L'Fellah 2.0 — v2: clean, no cache
self.addEventListener('install', event => {
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    // Supprimer TOUS les caches de l'ancien service worker
    event.waitUntil(
        caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k))))
    );
    self.clients.claim();
});

// Ne rien mettre en cache
self.addEventListener('fetch', event => {
    event.respondWith(fetch(event.request));
});
