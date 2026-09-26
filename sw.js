/* What's 4 Dinner? service worker — v2.0.0
   App shell: cache-first (works fully offline after first visit).
   Google Fonts: stale-while-revalidate.
   Map/geocoding APIs: always network (the app keeps its own saved copy of the last search). */
const VERSION = "2.0.0";
const SHELL = "w4d-shell-" + VERSION;
const RUNTIME = "w4d-runtime-" + VERSION;
const SHELL_FILES = [
  "./", "./index.html", "./manifest.json", "./assets/logo.png",
  "./icons/icon-192.png", "./icons/icon-512.png", "./icons/icon-maskable-512.png",
  "./icons/apple-touch-icon.png", "./icons/favicon-64.png"
];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(SHELL).then(c => c.addAll(SHELL_FILES)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== SHELL && k !== RUNTIME).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  // Live data: never cache here.
  if (/overpass|nominatim\.openstreetmap\.org/.test(url.hostname)) return;

  // Fonts: stale-while-revalidate.
  if (url.hostname === "fonts.googleapis.com" || url.hostname === "fonts.gstatic.com") {
    e.respondWith(caches.open(RUNTIME).then(async cache => {
      const hit = await cache.match(req);
      const net = fetch(req).then(res => { if (res.ok || res.type === "opaque") cache.put(req, res.clone()); return res; }).catch(() => hit);
      return hit || net;
    }));
    return;
  }

  // Same-origin: navigations fall back to the cached app; files are cache-first.
  if (url.origin === self.location.origin) {
    if (req.mode === "navigate") {
      e.respondWith(fetch(req).then(res => {
        const copy = res.clone(); caches.open(SHELL).then(c => c.put("./index.html", copy)); return res;
      }).catch(() => caches.match("./index.html")));
      return;
    }
    e.respondWith(caches.match(req, { ignoreSearch: true }).then(hit => hit || fetch(req).then(res => {
      if (res.ok) { const copy = res.clone(); caches.open(RUNTIME).then(c => c.put(req, copy)); }
      return res;
    })));
  }
});
