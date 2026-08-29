// PDFhero Service Worker — cache-first strategy
// Cache name and manifest.json version MUST be updated together on every release.
const CACHE_NAME = 'pdfhero-v1.02.1';

const CACHED_URLS = [
  './index.html',
  './manifest.json',
  './pdfcpu.wasm',
  'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.min.mjs',
  'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.worker.min.mjs',
  'https://unpkg.com/pdf-lib@1.17.1/dist/pdf-lib.min.js',
];

// Install: pre-cache all known assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(CACHED_URLS))
  );
  // Activate immediately without waiting for existing clients to close
  self.skipWaiting();
});

// Activate: remove any old versioned caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) =>
      Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      )
    )
  );
  // Take control of all open clients immediately
  self.clients.claim();
});

// Fetch: serve from cache, fall back to network and cache the response
self.addEventListener('fetch', (event) => {
  // Only handle GET requests
  if (event.request.method !== 'GET') return;

  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) {
        return cached;
      }

      // Not in cache — fetch from network and cache for future use
      return fetch(event.request)
        .then((response) => {
          // Only cache valid, non-opaque responses
          if (
            !response ||
            response.status !== 200 ||
            response.type === 'error'
          ) {
            return response;
          }

          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });

          return response;
        })
        .catch(() => {
          // Network failed and nothing in cache — return nothing gracefully
          return new Response('Network error and no cached response available.', {
            status: 503,
            statusText: 'Service Unavailable',
          });
        });
    })
  );
});
