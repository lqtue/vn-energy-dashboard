// Vietnam Energy Atlas — service worker
// Cache-first for own data + basemap tiles. Network-first for HTML/JS so updates land.

const VERSION = 'v5';
const DATA_CACHE = `vn-energy-data-${VERSION}`;
const TILE_CACHE = `vn-energy-tiles-${VERSION}`;
const SHELL_CACHE = `vn-energy-shell-${VERSION}`;

const SHELL = ['./', './index.html'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(SHELL_CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => ![DATA_CACHE, TILE_CACHE, SHELL_CACHE].includes(k))
          .map(k => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // Own GeoJSON — cache-first, ~permanent. Bust by changing the file path on update.
  if (url.origin === location.origin && url.pathname.includes('/data/') && url.pathname.endsWith('.geojson')) {
    e.respondWith(cacheFirst(req, DATA_CACHE));
    return;
  }

  // Basemap raster tiles (CARTO + Esri) — cache-first
  if (url.hostname.endsWith('basemaps.cartocdn.com') ||
      url.hostname === 'server.arcgisonline.com') {
    e.respondWith(cacheFirst(req, TILE_CACHE, { maxEntries: 600 }));
    return;
  }

  // Shell HTML — network-first so new deploys land
  if (req.mode === 'navigate' || (url.origin === location.origin && url.pathname.endsWith('.html'))) {
    e.respondWith(networkFirst(req, SHELL_CACHE));
    return;
  }
});

async function cacheFirst(req, cacheName, opts = {}) {
  const cache = await caches.open(cacheName);
  const hit = await cache.match(req);
  if (hit) return hit;
  try {
    const res = await fetch(req);
    if (res.ok) {
      cache.put(req, res.clone());
      if (opts.maxEntries) trimCache(cache, opts.maxEntries);
    }
    return res;
  } catch (err) {
    return hit || Response.error();
  }
}

async function networkFirst(req, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const res = await fetch(req);
    if (res.ok) cache.put(req, res.clone());
    return res;
  } catch (err) {
    const hit = await cache.match(req);
    return hit || Response.error();
  }
}

async function trimCache(cache, max) {
  const keys = await cache.keys();
  if (keys.length <= max) return;
  for (let i = 0; i < keys.length - max; i++) cache.delete(keys[i]);
}
