const CACHE = "pillshelf-v1";
const ASSETS = ["./", "./index.html", "./manifest.webmanifest", "./fonts/Galmuri11.woff2", "./fonts/Galmuri11-Bold.woff2", "../BAC100/fonts/Pretendard.woff2", "./icon-192.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
// 네트워크 우선, 실패 시 캐시 (업데이트가 바로 반영되도록)
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET" || new URL(e.request.url).origin !== location.origin) return;
  e.respondWith(fetch(e.request).then(r => { const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); return r; }).catch(() => caches.match(e.request)));
});
