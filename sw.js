/* 칼랭크 서비스 워커: 본 페이지는 항상 네트워크 먼저, 실패하면 저장본을 보여 준다.
   (검색 로봇과 최신 내용에는 영향 없음. 같은 사이트의 GET 요청만 다룬다.) */
const VER = "cr-v1";
const PAGES = VER + "-pages";
const ASSETS = VER + "-assets";
const MAX_PAGES = 120;

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(ASSETS).then((c) => c.addAll(["/offline.html", "/favicon-192.png"])).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((ks) => Promise.all(ks.filter((k) => !k.startsWith(VER)).map((k) => caches.delete(k)))).then(() => self.clients.claim())
  );
});

async function trim(name, max) {
  const c = await caches.open(name);
  const ks = await c.keys();
  for (let i = 0; i < ks.length - max; i++) await c.delete(ks[i]);
}

self.addEventListener("fetch", (e) => {
  const r = e.request;
  if (r.method !== "GET") return;
  const u = new URL(r.url);
  if (u.origin !== location.origin) return;
  if (/\.(ics|xml)$/.test(u.pathname) || u.pathname === "/sw.js") return;

  if (r.mode === "navigate") {
    e.respondWith(
      fetch(r).then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(PAGES).then((c) => c.put(r, copy)).then(() => trim(PAGES, MAX_PAGES));
        }
        return res;
      }).catch(() => caches.match(r).then((hit) => hit || caches.match("/offline.html")))
    );
    return;
  }

  if (/\.(css|js|png|svg|ico|woff2?|json)$/.test(u.pathname)) {
    e.respondWith(
      caches.open(ASSETS).then((c) =>
        c.match(r).then((hit) => {
          const net = fetch(r).then((res) => { if (res.ok) c.put(r, res.clone()); return res; }).catch(() => hit);
          return hit || net;
        })
      )
    );
  }
});
