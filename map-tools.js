// 지도 도구 — 전체화면, 내 위치(GPS), 방위(북쪽 표시·보는 방향). Leaflet 지도에 붙인다.
// 위치는 이 브라우저 안에서만 쓴다. 단 ‘장소 제보’를 누를 때만 그 지점 좌표를 서버로 보낸다. 지도는 항상 북쪽이 위다.
// 쓰는 곳: route-map.js(코스·트레일 지도), script.js(메인 대회 지도)
(function () {
  "use strict";
  // 위치는 이 브라우저 안에서만 쓴다. 단 ‘장소 제보’를 누를 때만 그 지점 좌표를 서버로 보낸다. 지도는 항상 북쪽이 위다.
  var api = { attach: null, exitFull: function () {} };
  function injectCss() {
    if (document.getElementById("rmCss")) return;
    var st = document.createElement("style"); st.id = "rmCss";
    var M = "#3EE0BE", MD = "#0E9F87", INK = "#15110F";
    st.textContent = ".rm-full{position:fixed!important;inset:0;width:100%!important;height:100vh!important;height:100dvh!important;max-width:none!important;margin:0!important;border:0!important;border-radius:0!important;z-index:99999}" +
      "body.rm-lock{overflow:hidden}" +
      // 모든 지도 버튼: 둥근 모서리, 옅은 민트 테두리, 그림자. 누르면 살짝 눌리고 켜진 상태는 민트로 채운다.
      ".leaflet-bar{border:0!important;box-shadow:none!important;background:none!important;display:flex;flex-direction:column;gap:8px}" +
      ".leaflet-bar a,.rm-ctl a{display:flex!important;align-items:center;justify-content:center;gap:6px;width:46px!important;height:46px!important;line-height:1!important;padding:0;border:1px solid rgba(14,159,135,.35)!important;border-radius:16px!important;background:#fff!important;color:" + INK + "!important;font:700 14px/1 sans-serif;text-decoration:none!important;cursor:pointer;white-space:nowrap;box-shadow:0 3px 10px rgba(8,70,58,.22);transition:transform .12s,background .15s,box-shadow .15s}" +
      ".leaflet-bar a:hover,.rm-ctl a:hover{background:#e9fbf6!important}" +
      ".leaflet-bar a:active,.rm-ctl a:active{transform:scale(.94);box-shadow:0 1px 4px rgba(8,70,58,.3)}" +
      ".leaflet-bar a:focus-visible,.rm-ctl a:focus-visible{outline:3px solid " + MD + ";outline-offset:2px}" +
      ".leaflet-control-zoom a span{font-size:26px;font-weight:600}.rm-ctl a span{font-size:14px;font-weight:800}" +
      ".rm-ctl{display:block}.rm-ctl a{width:auto!important;min-width:46px;padding:0 14px 0 12px!important}" +
      ".rm-ctl a svg{width:22px;height:22px;flex:none;fill:currentColor}" +
      ".rm-ctl a[aria-pressed=true]{background:" + M + "!important;border-color:" + MD + "!important}" +
      ".rm-north{display:flex;flex-direction:column;align-items:center;justify-content:center;width:46px;height:46px;border-radius:50%;background:#fff;color:" + INK + ";border:1px solid rgba(14,159,135,.35);font:800 11px/1 sans-serif;box-shadow:0 3px 10px rgba(8,70,58,.22);pointer-events:none}" +
      ".rm-north svg{width:18px;height:18px;fill:" + MD + "}" +
      ".rm-stat{max-width:calc(100vw - 90px);padding:10px 14px;border-radius:18px;background:rgba(255,255,255,.97);color:" + INK + ";font:600 13px/1.45 sans-serif;border:1px solid rgba(14,159,135,.3);border-left:5px solid " + M + ";box-shadow:0 4px 14px rgba(8,70,58,.25)}" +
      ".rm-hud{line-height:1.6;margin-top:6px;padding-top:6px;border-top:1px solid #d9efe9;font-weight:600}.rm-hud b{font-weight:800}.rm-warn{color:#b3261e;font-weight:800}" +
      ".rm-hud button{margin-top:6px;min-height:40px;padding:0 16px;border:0;border-radius:999px;background:" + M + ";color:#06362d;font:800 13px sans-serif;box-shadow:0 2px 6px rgba(8,70,58,.25);cursor:pointer}.rm-hud button:active{transform:scale(.96)}.rm-hud button.alt{margin-left:6px;background:#fff;border:1.5px solid #9fd8cc;box-shadow:none}" +
      ".rm-q{margin-top:8px;padding:10px 12px;border-radius:14px;background:#e9fbf6;border:1px solid #bfeee3}.rm-q span{display:block;font-weight:700}" +
      ".rm-q button{margin:8px 6px 0 0}.rm-q button.alt{background:#fff;color:#15110F;border:1px solid #9fd8cc;box-shadow:none}.rm-q small{display:block;margin-top:6px;font-weight:500;color:#4a5a56}" +
      ".rm-by{display:block;margin:0 0 4px;font-style:normal;font-size:12.5px;color:#2A7A50}.rm-by b{font-weight:900}" +
      ".rm-thx{margin-top:8px;padding:8px 12px;border-radius:14px;background:#e9fbf6;font-weight:700}" +
      ".rm-dot{display:inline-block;width:9px;height:9px;margin-right:7px;border-radius:50%;background:#1f9d62;vertical-align:1px;animation:rmBlink 1.4s ease-in-out infinite}.rm-dot.mid{background:#d99a00}.rm-dot.bad{background:#b3261e}.rm-dot.wait{background:#8a8a8a;animation:none}" +
      "@keyframes rmBlink{0%,100%{opacity:1}50%{opacity:.25}}@media (prefers-reduced-motion:reduce){.rm-dot{animation:none}}" +
      ".rm-rep{position:fixed;left:8px;right:8px;bottom:calc(8px + env(safe-area-inset-bottom,0px));z-index:100000;max-width:520px;margin:0 auto;max-height:min(80vh,560px);overflow:auto;padding:12px 14px 14px;border-radius:18px;background:#fff;color:#15110F;box-shadow:0 6px 22px rgba(8,70,58,.35);border:1.5px solid #9fd8cc;font:600 13px/1.55 sans-serif}" +
      ".rm-rep[hidden]{display:none}.rm-rep h3{margin:0 0 4px;font:900 15px/1.3 sans-serif}.rm-rep .x{position:absolute;right:8px;top:6px;width:40px;height:40px;border:0;background:none;font-size:24px;line-height:1;color:#555;cursor:pointer}" +
      ".rm-rep p{margin:2px 0 8px}.rm-rep .ks{display:grid;grid-template-columns:repeat(auto-fit,minmax(104px,1fr));gap:8px;margin:8px 0}" +
      ".rm-rep .k{display:flex;align-items:center;gap:8px;min-height:46px;padding:0 10px 0 6px;border:1.5px solid #cfd8d5;border-radius:14px;background:#fff;color:#15110F;font:800 13px/1.2 sans-serif;cursor:pointer;text-align:left}" +
      ".rm-rep .k[aria-pressed=true]{border:2.5px solid var(--c);background:#f3fbf9}.rm-rep .k:disabled{opacity:.45}" +
      ".rm-rep .kd{display:inline-flex;align-items:center;justify-content:center;flex:none;width:30px;height:30px;border-radius:9px;background:var(--c)}.rm-rep .kd svg{display:block}" +
      ".rm-rep input{box-sizing:border-box;width:100%;min-height:44px;margin:4px 0 8px;padding:0 12px;border:1.5px solid #cfd8d5;border-radius:12px;font:600 14px sans-serif}" +
      ".rm-rep .go{min-height:46px;padding:0 18px;border:0;border-radius:999px;background:#0e9f87;color:#fff;font:900 14px/1 sans-serif;cursor:pointer}.rm-rep .go:disabled{opacity:.45}" +
      ".rm-rep .ghost{min-height:46px;padding:0 16px;margin-left:8px;border:1.5px solid #9fd8cc;border-radius:999px;background:#fff;color:#15110F;font:800 13px/1 sans-serif;cursor:pointer}" +
      ".rm-rep .m{margin:8px 0 0;font-weight:700}.rm-rep .w{color:#b3261e}.rm-rep small{display:block;margin-top:8px;font-weight:500;color:#4a5a56}.rm-rep a{color:#0b6b5a}" +
      ".rm-me{position:relative;width:22px;height:22px}" +
      ".rm-me i{position:absolute;left:3px;top:3px;width:16px;height:16px;border-radius:50%;background:#1a73e8;border:3px solid #fff;box-shadow:0 0 0 1px rgba(0,0,0,.25),0 2px 6px rgba(0,0,0,.3)}" +
      ".rm-me::before{content:'';position:absolute;left:3px;top:3px;width:16px;height:16px;border-radius:50%;background:#1a73e8;opacity:.55;animation:rmPulse 1.6s ease-out infinite}" +
      ".rm-me i{animation:rmBeat 1.6s ease-in-out infinite}" +
      "@keyframes rmPulse{0%{transform:scale(1);opacity:.6}100%{transform:scale(4);opacity:0}}" +
      "@keyframes rmBeat{0%,100%{transform:scale(1)}50%{transform:scale(1.18)}}" +
      "@keyframes rmFade{0%,100%{opacity:.55}50%{opacity:.1}}" +
      "@media (prefers-reduced-motion:reduce){.rm-me i{animation:none}.rm-me::before{animation:rmFade 2.4s ease-in-out infinite;transform:scale(2.2)}}" +
      ".rm-me u{position:absolute;left:5px;top:-9px;width:0;height:0;border-left:6px solid transparent;border-right:6px solid transparent;border-bottom:12px solid #1a73e8;transform-origin:6px 20px;display:none}";
    document.head.appendChild(st);
  }
  function distToPath(lat, lon, pts) {
    var k = 111320, c = Math.cos(lat * Math.PI / 180), best = 1e12;
    for (var i = 1; i < pts.length; i++) {
      var ax = (pts[i - 1][1] - lon) * k * c, ay = (pts[i - 1][0] - lat) * k, bx = (pts[i][1] - lon) * k * c, by = (pts[i][0] - lat) * k,
        dx = bx - ax, dy = by - ay, L2 = dx * dx + dy * dy || 1, t = Math.max(0, Math.min(1, -(ax * dx + ay * dy) / L2));
      best = Math.min(best, Math.hypot(ax + t * dx, ay + t * dy));
    }
    return best;
  }

  // 트레일루트 HUD: 코스 자료(field/<id>.json)가 있는 코스에서만 켜진다.
  function loadScript(src, ok) { if (window.CalrankSeg) return ok(); var t = document.createElement("script"); t.src = src; t.onload = ok; document.head.appendChild(t); }
  function courseId() { var m = location.pathname.match(/course-([^/]+)\.html$/); return m ? m[1] : null; }
  // Tobler 하이킹 함수(1993): 시속 km = 6·e^(-3.5·|경사+0.05|). 쉬는 시간·짐·노면은 들어 있지 않은 근사값이다.
  function secs(P, from, to) {
    var t = 0;
    for (var i = 1; i < P.length; i++) {
      var a = Math.max(P[i - 1][0], from), b = Math.min(P[i][0], to); if (b <= a) continue;
      var sl = (P[i][1] - P[i - 1][1]) / ((P[i][0] - P[i - 1][0]) || 1), v = 6 * Math.exp(-3.5 * Math.abs(sl + 0.05));
      t += (b - a) / 1000 / v * 3600;
    }
    return t;
  }
  function hm(d) { return ("0" + d.getHours()).slice(-2) + ":" + ("0" + d.getMinutes()).slice(-2); }
  function km(m) { return (m / 1000).toFixed(m >= 10000 ? 0 : 1) + "km"; }
  // 아이콘: Material Design Icons(Apache 2.0)
  var ICO = {
    my_location: "M12 8c-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4-1.79-4-4-4zm8.94 3A8.994 8.994 0 0 0 13 3.06V2c0-.55-.45-1-1-1s-1 .45-1 1v1.06A8.994 8.994 0 0 0 3.06 11H2c-.55 0-1 .45-1 1s.45 1 1 1h1.06A8.994 8.994 0 0 0 11 20.94V22c0 .55.45 1 1 1s1-.45 1-1v-1.06A8.994 8.994 0 0 0 20.94 13H22c.55 0 1-.45 1-1s-.45-1-1-1h-1.06zM12 19c-3.87 0-7-3.13-7-7s3.13-7 7-7 7 3.13 7 7-3.13 7-7 7z",
    fullscreen: "M6 14c-.55 0-1 .45-1 1v3c0 .55.45 1 1 1h3c.55 0 1-.45 1-1s-.45-1-1-1H7v-2c0-.55-.45-1-1-1zm0-4c.55 0 1-.45 1-1V7h2c.55 0 1-.45 1-1s-.45-1-1-1H6c-.55 0-1 .45-1 1v3c0 .55.45 1 1 1zm11 7h-2c-.55 0-1 .45-1 1s.45 1 1 1h3c.55 0 1-.45 1-1v-3c0-.55-.45-1-1-1s-1 .45-1 1v2zM14 6c0 .55.45 1 1 1h2v2c0 .55.45 1 1 1s1-.45 1-1V6c0-.55-.45-1-1-1h-3c-.55 0-1 .45-1 1z",
    close: "M18.3 5.71a.996.996 0 0 0-1.41 0L12 10.59 7.11 5.7A.996.996 0 1 0 5.7 7.11L10.59 12 5.7 16.89a.996.996 0 1 0 1.41 1.41L12 13.41l4.89 4.89a.996.996 0 1 0 1.41-1.41L13.41 12l4.89-4.89c.38-.38.38-1.02 0-1.4z",
    gps_off: "M22 13c.55 0 1-.45 1-1s-.45-1-1-1h-1.06A8.994 8.994 0 0 0 13 3.06V2c0-.55-.45-1-1-1s-1 .45-1 1v1.06c-.98.11-1.91.38-2.77.78l1.53 1.53a6.995 6.995 0 0 1 8.87 8.87l1.53 1.53c.4-.86.67-1.79.78-2.77H22zm-1.56 5.88L5.12 3.56a.996.996 0 1 0-1.41 1.41L5.04 6.3A9.061 9.061 0 0 0 3.06 11H2c-.55 0-1 .45-1 1s.45 1 1 1h1.06A8.994 8.994 0 0 0 11 20.94V22c0 .55.45 1 1 1s1-.45 1-1v-1.06c1.77-.2 3.38-.91 4.69-1.98l1.33 1.33c.39.39 1.02.39 1.41 0 .4-.39.4-1.02.01-1.41zM12 19A6.995 6.995 0 0 1 6.46 7.73l9.81 9.81A6.972 6.972 0 0 1 12 19z",
    add_place: { v: "0 -960 960 960", d: "M529.5-510.59q20.5-20.59 20.5-49.5t-20.59-49.41q-20.59-20.5-49.5-20.5t-49.41 20.59q-20.5 20.59-20.5 49.5t20.59 49.41q20.59 20.5 49.5 20.5t49.41-20.59Zm-71 407.09Q448-107 440-115q-42-38-91-87.5T258-309q-42-57-70-119t-28-124q0-150 96.5-239T480-880q41 0 62.5 19.5T564-803v1q0 28.87 20.56 49.44Q605.13-732 634-732h58v58q0 14 5.22 27.05Q702.43-633.9 712-624q10 10 21 14t25 6q24 2 33.5 16.5T801-550q0 30-14 69.5t-32 77q-18 37.5-35.5 67T694-296q-45 58-92 105t-82 76q-8 8-18.75 11.5t-21.5 3.5q-10.75 0-21.25-3.5ZM732-772h-98q-12.75 0-21.37-8.68-8.63-8.67-8.63-21.5 0-12.82 8.63-21.32 8.62-8.5 21.37-8.5h98v-98q0-12.75 8.68-21.38 8.67-8.62 21.5-8.62 12.82 0 21.32 8.62 8.5 8.63 8.5 21.38v98h98q12.75 0 21.38 8.68 8.62 8.67 8.62 21.5 0 12.82-8.62 21.32-8.63 8.5-21.38 8.5h-98v98q0 12.75-8.68 21.37-8.67 8.63-21.5 8.63-12.82 0-21.32-8.63-8.5-8.62-8.5-21.37v-98Z" },
    north: "M5.71 9.7c.39.39 1.02.39 1.41 0L11 5.83V21c0 .55.45 1 1 1s1-.45 1-1V5.83l3.88 3.88a.996.996 0 1 0 1.41-1.41L12.7 2.7a.996.996 0 0 0-1.41 0L5.71 8.29a.996.996 0 0 0 0 1.41z"
  };
  function lab(a, ic, t) { var o = ICO[ic], v = typeof o === "string" ? "0 0 24 24" : o.v, p = typeof o === "string" ? o : o.d; a.innerHTML = '<svg viewBox="' + v + '" aria-hidden="true"><path d="' + p + '"/></svg><span></span>'; a.lastChild.textContent = t; }
  function attach(L, map, opt) {
    var wrap = opt.wrap, all = opt.all || [];
    injectCss();
    var full = false, gps = null, follow = true, me = null, acc = null, meEl = null, heading = null, lock = null, stat = null, gpsBtn = null, fullBtn = null, oriOn = false, C = null, hudEl = null, lastD = null, offWarn = 0;
    var secList = [];
    if (opt.secs && opt.secs.length && !courseId()) loadScript("/seg-core.js", function () {
      secList = opt.secs.filter(function (x) { return x.p && x.p.length > 1; }).map(function (x) { var L2 = 0; for (var i = 1; i < x.p.length; i++) L2 += Math.hypot((x.p[i][1] - x.p[i - 1][1]) * 111320 * Math.cos(x.p[i][0] * Math.PI / 180), (x.p[i][0] - x.p[i - 1][0]) * 111320); return { p: x.p, g: x.g, len: L2 }; });
    });
    var cid = courseId();
    var mm = /mountain-(\d+)\.html/.exec(location.pathname), routeId = cid || (mm ? "mt-" + mm[1] : null);
    function getSpots() { return (opt.spots || []).filter(function (s) { return s[0] === "toilet"; }); }
    var poiList = null, poiAll = [], poiLen = 0, pq = null, uq = null, lastOff = null, thx = null, skipQ = {};
    var ASK = { "화장실": "화장실", "식수대": "식수대", "약수터·샘터": "약수터·샘터", "대피소": "대피소" };
    var memDev = null;
    function devId() { try { var v = localStorage.getItem("calrank_dev"); if (!v) { v = ""; for (var i = 0; i < 32; i++) v += Math.floor(Math.random() * 16).toString(16); localStorage.setItem("calrank_dev", v); } return v; } catch (e) { if (!memDev) { memDev = ""; for (var j = 0; j < 32; j++) memDev += Math.floor(Math.random() * 16).toString(16); } return memDev; } }
    function doneMap() { try { return JSON.parse(localStorage.getItem("calrank_pc") || "{}"); } catch (e) { return {}; } }
    function markDone(key) { try { var m = doneMap(), n = Date.now(); Object.keys(m).forEach(function (x) { if (n - m[x] > 864e5) delete m[x]; }); m[key] = n; localStorage.setItem("calrank_pc", JSON.stringify(m)); } catch (e) {} }
    // 시설 지점 근처(40m 안)를 지날 때만 한 번 묻고, 70m 넘게 멀어지면 저절로 접는다.
    function askHtml(d, ac, tot) {
      if (thx && Date.now() < thx.until) return '<div class="rm-thx">' + thx.html + "</div>";
      thx = null;
      if (!poiAll.length || ac > 50) { pq = null; return ""; }
      var k = poiLen > 0 && tot > 0 && Math.abs(tot / poiLen - 1) < 0.25 ? tot / poiLen : 1;
      if (pq && Math.abs(pq.pos - d) > 70) { skipQ[pq.key] = 1; pq = null; }
      if (!pq) {
        var done = doneMap(), best = null;
        poiAll.forEach(function (p) { var pos = p.d * k, g = Math.abs(pos - d); if (g <= 40 && !skipQ[p.key] && !done[routeId + "|" + p.key] && (!best || g < best.g)) best = { g: g, pos: pos, key: p.key, kind: p.kind }; });
        pq = best;
      }
      if (!pq) return "";
      return qBox(pq.kind, pq.key);
    }
    // 이 지점을 처음 확인한 사람의 닉네임을 보여 주거나, 아직 없으면 "내 이름이 남는다"고 알려 준다.
    function whoNote(key) {
      var c = window.CalrankChecks && window.CalrankChecks[key], nm = c && c.first_name ? String(c.first_name).replace(/[^가-힣A-Za-z0-9_]/g, "") : "";
      if (nm) return '<em class="rm-by"><b>' + nm + "</b> 님이 확인한 지점</em>";
      var mine = ""; try { mine = localStorage.getItem("calrank_nick") || ""; } catch (e) {}
      if (!(c && c.yes_n) && mine && window.CalrankAuth && window.CalrankAuth.user()) return '<em class="rm-by">처음 확인하면 내 닉네임이 남습니다</em>';
      return "";
    }
    function qBox(kind, key) {
      return '<div class="rm-q" role="group" aria-label="시설 확인">' + (key ? whoNote(key) : "") + '<span>여기 <b>' + kind + '</b>이(가) 있나요?</span><button type="button" id="rmQy">있어요</button><button type="button" id="rmQn" class="alt">없어요</button><button type="button" id="rmQs" class="alt">건너뛰기</button><small>누르면 확인 기록이 남습니다. 내 위치는 보내지 않습니다.</small></div>';
    }
    // 산 페이지: 등산로 구간 거리 대신 좌표로 가까운 화장실 지점(40m)을 찾는다. 70m 넘게 멀어지면 접는다.
    function askSpot(ll, ac) {
      if (thx && Date.now() < thx.until) return '<div class="rm-thx">' + thx.html + "</div>";
      thx = null;
      var spotList = getSpots();
      if (!spotList.length || ac > 50) { pq = null; return ""; }
      var kx = 111320 * Math.cos(ll[0] * Math.PI / 180), ky = 111320;
      function dist(s) { return Math.hypot((s[2] - ll[1]) * kx, (s[1] - ll[0]) * ky); }
      if (pq && dist(pq.s) > 70) { skipQ[pq.key] = 1; pq = null; }
      if (!pq) {
        var done = doneMap(), best = null;
        spotList.forEach(function (s) { var key = s[3], g = dist(s); if (key && g <= 40 && !skipQ[key] && !done[routeId + "|" + key] && (!best || g < best.g)) best = { g: g, s: s, key: key, kind: "화장실" }; });
        pq = best;
      }
      if (!pq) return "";
      return qBox(pq.kind, pq.key);
    }
    // 이용자가 제보한 지점(USER:번호) 근처(40m 안)를 지날 때도 한 번 묻는다. 내가 올린 지점은 묻지 않는다.
    function askUser(ll, ac) {
      var SPx = window.CalrankSpots;
      if (!SPx || !SPx.users || ac > 50) { uq = null; return ""; }
      var kx = 111320 * Math.cos(ll[0] * Math.PI / 180);
      function dist(p) { return Math.hypot((p.lon - ll[1]) * kx, (p.lat - ll[0]) * 111320); }
      if (uq && dist(uq.p) > 70) { skipQ[uq.key] = 1; uq = null; }
      if (!uq) {
        var done = doneMap(), best = null;
        SPx.users().forEach(function (p) { if (p.mine) return; var g = dist(p); if (g <= 40 && !skipQ[p.key] && !done[routeId + "|" + p.key] && (!best || g < best.g)) best = { g: g, p: p, key: p.key, kind: p.label === "위험" ? "위험 구간" : p.label }; });
        uq = best;
      }
      return uq ? qBox(uq.kind, uq.key) : "";
    }
    function bindAsk(root) {
      var y = root.querySelector("#rmQy"), n = root.querySelector("#rmQn"), sk = root.querySelector("#rmQs"), q = uq || pq; if (!y || !q) return;
      function close(html) { skipQ[q.key] = 1; if (uq === q) uq = null; else pq = null; if (html) thx = { html: html, until: Date.now() + 7000 }; repaint(); }
      function send(ans) {
        if (!window.CalrankAuth) { close("지금은 기록하지 못했습니다."); return; }
        close("기록하는 중…");
        CalrankAuth.rpc("submit_poi_check", { p_route: routeId, p_poi: q.key, p_answer: ans, p_device: devId() }).then(function (r) {
          var res = r && !r.error ? r.data : "err";
          if (res === "ok") {
            markDone(routeId + "|" + q.key);
            var who = CalrankAuth.user() ? "" : ' <small>로그인하면 닉네임이 함께 남습니다.</small>';
            thx = { html: "고맙습니다. 다음 사람이 이 기록을 봅니다." + who, until: Date.now() + 7000 };
          } else thx = { html: res === "slow" ? "너무 자주 눌렀습니다. 잠시 뒤에 다시 해 주세요." : "지금은 기록하지 못했습니다.", until: Date.now() + 5000 };
          repaint(); setTimeout(repaint, 7100);
        });
      }
      y.onclick = function () { send("yes"); }; n.onclick = function () { send("no"); }; sk.onclick = function () { close(""); };
    }
    if (cid && window.fetch) fetch("/data/course_pois.json").then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
      var r = j && j.routes && j.routes[(/^dr-/.test(cid) ? "두루누비:" : "숲길:") + cid];
      if (r && !r.failed) poiAll = (r.pois || []).filter(function (p) { return ASK[p[1]] && p[3]; }).map(function (p) { return { d: p[0], kind: p[1], key: p[3] + ":" + (Math.round(p[0] / 10) * 10) }; });
      if (r && !r.failed) poiLen = r.lengthM || 0;
      if (r && !r.failed) poiList = { len: r.lengthM || 0, pois: (r.pois || []).filter(function (p) { return p[1] === "화장실"; }).map(function (p) { return p[0]; }).sort(function (x, y) { return x - y; }) };
    }).catch(function () {});
    if (cid) fetch("/field/" + cid + ".json").then(function (r) { return r.ok ? r.json() : null; }).then(function (j) { if (j && j.profile && j.path && j.path.length > 1) loadScript("/seg-core.js", function () { C = { j: j, c: CalrankSeg.course(j.path, j.profile[j.profile.length - 1][0]), segs: CalrankSeg.segments(j.profile) }; }); }).catch(function () {});
    function Ctl(pos, ic, label, title, fn) {
      var C = L.Control.extend({ options: { position: pos }, onAdd: function () {
        var d = L.DomUtil.create("div", "leaflet-bar rm-ctl"), a = L.DomUtil.create("a", "", d);
        a.href = "#"; a.setAttribute("role", "button"); a.setAttribute("aria-label", title); a.title = title; lab(a, ic, label);
        L.DomEvent.disableClickPropagation(d); L.DomEvent.on(a, "click", function (e) { L.DomEvent.preventDefault(e); fn(a); });
        return d; } });
      var c = new C(); c.addTo(map); return c;
    }
    // 북쪽 표시(지도는 북쪽이 위로 고정)
    var N = L.Control.extend({ options: { position: "topright" }, onAdd: function () { var d = L.DomUtil.create("div", "rm-north"); d.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="' + ICO.north + '"/></svg>북'; d.setAttribute("aria-label", "지도는 북쪽이 위입니다"); return d; } });
    new N().addTo(map);
    fullBtn = Ctl("topright", "fullscreen", "전체화면", "지도를 화면 가득 보기", function (a) {
      full = !full; wrap.classList.toggle("rm-full", full); document.body.classList.toggle("rm-lock", full);
      lab(a, full ? "close" : "fullscreen", full ? "닫기" : "전체화면"); a.setAttribute("aria-pressed", full ? "true" : "false");
      setTimeout(function () { map.invalidateSize(); if (!full && all.length) map.fitBounds(L.latLngBounds(all), { padding: [16, 16] }); }, 60);
    });
    api.exitFull = function () { if (full) fullBtn.getContainer().firstChild.click(); };
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && full) { var a = fullBtn.getContainer().firstChild; a.click(); } });
    var S = L.Control.extend({ options: { position: "bottomleft" }, onAdd: function () { stat = L.DomUtil.create("div", "rm-stat"); stat.hidden = true; return stat; } });
    new S().addTo(map);
    function say(t) { stat.hidden = !t; stat.textContent = t || ""; }
    function setHeading(h) {
      if (h == null || isNaN(h) || !meEl) return;
      var a = (screen.orientation && screen.orientation.angle) || 0; heading = (h + a + 360) % 360;
      var u = meEl.querySelector("u"); u.style.display = "block"; u.style.transform = "rotate(" + heading + "deg)";
    }
    function onOri(e) { var h = e.webkitCompassHeading != null ? e.webkitCompassHeading : (e.absolute && e.alpha != null ? 360 - e.alpha : null); if (h != null) setHeading(h); }
    function startOri() {
      if (oriOn || typeof DeviceOrientationEvent === "undefined") return; oriOn = true;
      // 리스너는 먼저 달고, 권한을 따로 요구하는 기기(iOS)에서는 허용을 요청한다.
      window.addEventListener("deviceorientationabsolute", onOri, true); window.addEventListener("deviceorientation", onOri, true);
      if (DeviceOrientationEvent.requestPermission) { try { DeviceOrientationEvent.requestPermission().catch(function () {}); } catch (e) {} }
    }
    function stop() {
      if (gps !== null) navigator.geolocation.clearWatch(gps); gps = null;
      if (me) { map.removeLayer(me); map.removeLayer(acc); me = acc = meEl = null; }
      window.removeEventListener("deviceorientationabsolute", onOri, true); window.removeEventListener("deviceorientation", onOri, true); oriOn = false;
      if (lock) { try { lock.release(); } catch (e) {} lock = null; }
      lab(gpsBtn, "my_location", "내 위치"); gpsBtn.setAttribute("aria-pressed", "false"); say("");
    }
    function share() {
      if (!hudEl || (!C && !secList.length)) return;
      var h1 = document.querySelector("h1"), nm = C ? (C.j.name || "코스") : ((h1 && h1.textContent.trim()) || "등산로");
      var t = nm + (C ? " · 코스 " + km(hudEl.d) + " 지점" : "") + " · 위도 " + hudEl.ll[0].toFixed(5) + ", 경도 " + hudEl.ll[1].toFixed(5) + " (GPS 오차 ±" + hudEl.ac + "m) · " + hm(new Date()) + " 기준. 긴급 상황은 119에 이 위치를 불러 주세요.";
      if (navigator.share) navigator.share({ text: t }).catch(function () {});
      else if (navigator.clipboard) navigator.clipboard.writeText(t).then(function () { say("위치 문구를 복사했습니다."); }, function () { say(t); });
      else say(t);
    }
    // 산 등산로 지도: 한 줄로 이어진 코스가 아니라 구간 모음이라, 가장 가까운 구간의 길이·평균 경사와 일몰 정보만 보여 준다.
    function mtHud(ll, ac) {
      var best = null;
      secList.forEach(function (sc, i) { var o = distToPath(ll[0], ll[1], sc.p); if (!best || o < best.o) best = { o: o, i: i }; });
      if (!best) { lastOff = null; return askSpot(ll, ac) || askUser(ll, ac); }
      var sc = secList[best.i], off = Math.round(best.o), lines = []; lastOff = off;
      if (off > 60) { lines.push('<span class="rm-warn">가장 가까운 등산로에서 ' + off + 'm 떨어져 있습니다.</span>'); var now = Date.now(); if (now - offWarn > 20000) { offWarn = now; try { navigator.vibrate && navigator.vibrate([300, 150, 300]); } catch (e) {} } }
      else lines.push("지금 구간 <b>" + km(sc.len) + "</b> · 평균 경사 <b>" + Math.abs(sc.g).toFixed(0) + "%</b>");
      var sun = CalrankSeg.sun(ll[0], ll[1], new Date());
      if (sun) { var left = Math.round((sun.set - Date.now()) / 60000); lines.push("일몰 " + hm(sun.set) + (left > 0 ? " (" + left + "분 남음)" : ' <span class="rm-warn">일몰 후입니다</span>')); }
      var qs = askSpot(ll, ac) || askUser(ll, ac); if (qs) lines.push(qs);
      lines.push(btns());
      hudEl = { d: null, ll: ll, ac: ac };
      return lines.join("<br>");
    }
    function btns() { return '<button type="button" id="rmShare">내 위치 문구 복사</button> <button type="button" id="rmAdd" class="alt">＋ 깃발 꽂기</button>'; }
    function hud(ll, ac, off) {
      if (!C && secList.length) return mtHud(ll, ac);
      if (!C) return (getSpots().length ? askSpot(ll, ac) : "") || askUser(ll, ac);
      var P = C.j.profile, tot = C.c.total, s = C.c.snap(ll[0], ll[1], lastD), d = s.dist, lines = [];
      if (off != null && off > 60) { lines.push('<span class="rm-warn">코스에서 ' + off + 'm 벗어났습니다. 왔던 길로 돌아가세요.</span>'); var now = Date.now(); if (now - offWarn > 20000) { offWarn = now; try { navigator.vibrate && navigator.vibrate([300, 150, 300]); } catch (e) {} } return lines.join("<br>"); }
      lastD = d;
      var nx = C.segs.filter(function (g) { return g.to > d + 30 && g.t !== "flat"; })[0], rest = tot - d;
      lines.push("코스 <b>" + km(d) + "</b> 지점 · 남은 거리 <b>" + km(rest) + "</b>");
      if (poiList) {
        var k = poiList.len > 0 && tot > 0 && Math.abs(tot / poiList.len - 1) < 0.25 ? tot / poiList.len : 1, nt = null;
        for (var q = 0; q < poiList.pois.length; q++) if (poiList.pois[q] * k > d + 20) { nt = poiList.pois[q] * k - d; break; }
        lines.push(nt == null ? "앞쪽에 등록된 화장실 지점이 없습니다 (지도 자료 기준)" : "다음 화장실 지점 약 <b>" + (nt >= 1000 ? km(nt) : Math.round(nt / 10) * 10 + "m") + "</b> 앞 (지도 자료 기준·현장 확인 전)");
      }
      if (nx) lines.push((nx.from > d ? km(nx.from - d) + " 앞 " : "지금 ") + (nx.t === "up" ? "오르막" : "내리막") + " " + km(nx.len) + " · 평균 " + Math.abs(nx.grade).toFixed(0) + "%");
      var eta = new Date(Date.now() + secs(P, d, tot) * 1000), sun = CalrankSeg.sun(ll[0], ll[1], new Date());
      var t = "도착 예상 <b>" + hm(eta) + "</b>(Tobler 근사)";
      if (sun) { var gap = Math.round((sun.set - eta) / 60000); t += " · 일몰 " + hm(sun.set) + (gap < 0 ? ' <span class="rm-warn">일몰 후 도착 예상</span>' : " (여유 " + gap + "분)"); }
      lines.push(t);
      if (sun) { var left = Math.round((sun.set - Date.now()) / 60000), back = secs(P, 0, d) / 60; if (left > 0 && left < back * 1.2 + 30) lines.push('<span class="rm-warn">출발점으로 돌아가는 데 약 ' + Math.round(back) + '분, 일몰까지 ' + left + '분 남았습니다.</span>'); }
      var qh = askHtml(d, ac, tot) || askUser(ll, ac); if (qh) lines.push(qh);
      lines.push(btns());
      hudEl = { d: d, ll: ll, ac: ac };
      return lines.join("<br>");
    }
    var lastFix = null;
    function paintStat(base, h) {
      stat.hidden = false; stat.innerHTML = "";
      var ac0 = lastFix ? lastFix.ac : 0, dot = document.createElement("i"); dot.className = "rm-dot " + (ac0 <= 30 ? "" : ac0 <= 100 ? "mid" : "bad"); dot.setAttribute("aria-hidden", "true"); dot.id = "rmDot"; stat.appendChild(dot);
      stat.appendChild(document.createTextNode((ac0 <= 30 ? "GPS 연결됨 · " : ac0 <= 100 ? "GPS 신호 보통 · " : "GPS 신호 약함 · ") + base));
      if (h) { var hd = document.createElement("div"); hd.className = "rm-hud"; hd.innerHTML = h; stat.appendChild(hd); var sb = hd.querySelector("#rmShare"); if (sb) sb.onclick = share; var ab = hd.querySelector("#rmAdd"); if (ab) ab.onclick = toggleRep; bindAsk(hd); }
    }
    setInterval(function () { var d = document.getElementById("rmDot"); if (d && lastFix && gps !== null) { var stale = Date.now() - lastFix.at > 12000; d.classList.toggle("wait", stale); d.title = stale ? "위치 신호를 기다리는 중" : ""; } }, 2000);
    function repaint() { if (lastFix && gps !== null) paintStat(lastFix.base, hud(lastFix.ll, lastFix.ac, lastFix.off)); }
    Ctl("topleft", "my_location", "내 위치", "GPS로 내 위치 보기", function (a) {
      gpsBtn = a;
      if (gps !== null) { stop(); return; }
      if (!navigator.geolocation) { say("이 브라우저는 위치를 지원하지 않습니다."); return; }
      say("위치를 찾는 중입니다."); lab(a, "gps_off", "위치 끄기"); a.setAttribute("aria-pressed", "true"); follow = true; startOri();
      if (navigator.wakeLock) navigator.wakeLock.request("screen").then(function (l) { lock = l; }).catch(function () {});
      gps = navigator.geolocation.watchPosition(function (g) {
        var ll = [g.coords.latitude, g.coords.longitude], ac = Math.round(g.coords.accuracy || 0);
        if (!me) {
          meEl = L.DomUtil.create("div", "rm-me"); meEl.innerHTML = "<u></u><i></i>";
          me = L.marker(ll, { icon: L.divIcon({ html: meEl, className: "", iconSize: [22, 22], iconAnchor: [11, 11] }), keyboard: false, zIndexOffset: 1000 }).addTo(map);
          acc = L.circle(ll, { radius: ac, color: "#1a73e8", weight: 1, fillOpacity: 0.12 }).addTo(map);
          map.on("dragstart", function () { follow = false; });
          map.fitBounds(L.latLngBounds(all.concat([ll])), { padding: [24, 24], maxZoom: 17 });
        } else { me.setLatLng(ll); acc.setLatLng(ll).setRadius(ac); if (follow) map.panTo(ll); }
        if (g.coords.heading != null && !isNaN(g.coords.heading) && (g.coords.speed || 0) > 1) setHeading(g.coords.heading);
        var off = all.length > 1 ? Math.round(distToPath(ll[0], ll[1], all)) : null, offT = off == null ? "" : off >= 1000 ? (off / 1000).toFixed(off >= 10000 ? 0 : 1) + "km" : off + "m";
        var nn = (!C && secList.length) ? "등산로" : "코스", base = off == null ? "GPS 오차 ±" + ac + "m" : off <= 30 ? (nn + " 위에 있습니다 (" + nn + "에서 ") + off + "m · GPS 오차 ±" + ac + "m)" : off > 100 ? nn + "에서 약 " + offT + " 벗어나 있습니다 (GPS 오차 ±" + ac + "m)" : nn + "에서 약 " + offT + " 떨어져 있습니다 (GPS 오차 ±" + ac + "m)", h = hud(ll, ac, off);
        lastFix = { ll: ll, ac: ac, off: off, base: base, at: Date.now() };
        paintStat(base, h); updRep();
      }, function (err) {
        stop(); say(err && err.code === 1 ? "위치 권한이 꺼져 있습니다. 주소창 왼쪽 자물쇠(또는 aA)에서 위치를 허용하고, 폰의 위치 서비스도 켜져 있는지 확인해 주세요. 카카오톡 같은 앱 안의 브라우저에서는 막혀 있으니 크롬·사파리에서 열어 주세요." : "위치를 가져오지 못했습니다. 하늘이 트인 곳에서 다시 눌러 주세요.");
      }, { enableHighAccuracy: true, maximumAge: 2000, timeout: 20000 });
    });
    // ── 새 장소 제보: 지도에 없는 화장실·식수·쉼터·조망·위험을, 지금 서 있는 곳(GPS)에서 직접 올린다. ──
    var repEl = document.createElement("div"); repEl.className = "rm-rep"; repEl.hidden = true; repEl.setAttribute("role", "dialog"); repEl.setAttribute("aria-label", "깃발 꽂기");
    document.body.appendChild(repEl);
    var rep = { kind: null, busy: false, msg: "", note: "", done: false, doneMsg: "" }, RK = ["toilet", "water", "shelter", "view", "danger"];
    var RMSG = { login: "로그인하면 깃발을 꽂을 수 있습니다.", nick: "깃발에 걸 닉네임을 먼저 정해 주세요(내 활동 페이지).", bad: "내용을 확인해 주세요. 메모에는 연락처·인터넷 주소·욕설을 쓸 수 없습니다.", region: "이 코스에서 너무 멀리 떨어진 곳에는 깃발을 꽂을 수 없습니다.", accuracy: "GPS 오차가 커서 받을 수 없습니다. 하늘이 트인 곳에서 다시 시도해 주세요.", blocked: "올린 깃발이 여러 번 가려져 7일 동안 꽂을 수 없습니다.", slow: "방금 깃발을 꽂았습니다. 1분 뒤에 다시 꽂아 주세요.", limit: "깃발은 하루 5개까지 꽂을 수 있습니다. 내일 또 발견해 주세요." };
    function myNick() { try { return localStorage.getItem("calrank_nick") || ""; } catch (e) { return ""; } }
    function posProblem() {
      if (gps === null || !lastFix) return "먼저 ‘내 위치’를 켜 주세요. 위치가 잡히면 깃발을 꽂을 수 있습니다.";
      if (Date.now() - lastFix.at > 20000) return "위치 신호를 기다리는 중입니다. 잠시 뒤에 다시 시도해 주세요.";
      if (lastFix.ac > 30) return "GPS 오차가 ±" + lastFix.ac + "m 로 큽니다. 하늘이 트인 곳에서 잠시 기다린 뒤 다시 시도해 주세요.";
      var off = (!C && secList.length) ? lastOff : lastFix.off;
      if (off != null && off > 80) return "코스에서 " + (off >= 1000 ? (off / 1000).toFixed(1) + "km" : Math.round(off) + "m") + " 떨어져 있어 깃발을 꽂을 수 없습니다. 코스 위에서 꽂아 주세요.";
      return "";
    }
    function closeRep() { repEl.hidden = true; }
    function renderRep() {
      var SPx = window.CalrankSpots, KD = SPx && SPx.KIND, user = window.CalrankAuth && CalrankAuth.user();
      var h = '<button type="button" class="x" aria-label="닫기">×</button><h3>첫 발견자가 되어 보세요</h3>';
      if (!SPx || !KD || !routeId) h += "<p>이 페이지에서는 깃발을 꽂을 수 없습니다.</p>";
      else if (!user) h += '<p>로그인하면 내 이름으로 깃발을 꽂을 수 있습니다. 닉네임이 ‘처음 발견한 사람’으로 지도에 남습니다.</p><button type="button" class="go" id="rmRepLogin">로그인</button>';
      else if (!myNick()) h += '<p>깃발에는 닉네임이 걸립니다. 닉네임을 정하면 바로 꽂을 수 있습니다.</p><a href="/myrank.html">내 활동에서 닉네임 정하기</a>';
      else if (rep.done) h += '<p class="m" id="rmRepDone"></p><button type="button" class="go" id="rmRepClose">닫기</button><button type="button" class="ghost" id="rmRepMore">다른 곳도 꽂기</button>';
      else {
        h += '<p>지도에 없는 곳을 발견하셨나요? 지금 서 있는 곳에 내 이름으로 깃발을 꽂습니다. <span id="rmRepAcc"></span></p><div class="ks" role="group" aria-label="발견한 것">';
        RK.forEach(function (k) { h += '<button type="button" class="k" data-k="' + k + '" style="--c:' + KD[k].c + '" aria-pressed="' + (rep.kind === k ? "true" : "false") + '"><span class="kd" style="--c:' + KD[k].c + '">' + SPx.sign(k, 20) + "</span>" + (k === "danger" ? "위험 구간" : KD[k].label) + "</button>"; });
        h += '</div><input id="rmRepNote" type="text" maxlength="40" autocomplete="off" placeholder="메모(선택, 40자) 예: 문 앞 계단" aria-label="메모(선택)"><button type="button" class="go" id="rmRepGo">여기에 깃발 꽂기</button><div class="m" id="rmRepMsg" aria-live="polite"></div>' +
          "<small>깃발에는 내 닉네임이 ‘처음 발견한 사람’으로 남고, 뒤따르는 러너·산악인이 ‘있어요/없어요’로 확인합니다. 위험 구간은 2명이 확인하면 모두에게 보입니다. 깃발은 하루 5개까지 꽂을 수 있습니다.</small>";
      }
      repEl.innerHTML = h;
      var nt = repEl.querySelector("#rmRepNote"); if (nt) { nt.value = rep.note || ""; nt.oninput = function () { rep.note = nt.value; }; }
      var dn = repEl.querySelector("#rmRepDone"); if (dn) dn.textContent = rep.doneMsg;
      updRep();
    }
    function updRep() {
      if (repEl.hidden || rep.done) return;
      var go = repEl.querySelector("#rmRepGo"); if (!go) return;
      var a = repEl.querySelector("#rmRepAcc"), m = repEl.querySelector("#rmRepMsg"), prob = posProblem();
      if (a) a.textContent = lastFix && gps !== null ? "(GPS 오차 ±" + lastFix.ac + "m)" : "";
      go.disabled = !!prob || !rep.kind || rep.busy;
      if (m) { var t = rep.msg || prob || (rep.kind ? "" : "무엇을 발견하셨는지 골라 주세요."); m.textContent = t; m.className = "m" + (prob || (rep.msg && !rep.busy && !rep.done) ? " w" : ""); }
    }
    function fin(ok, msg) { rep.busy = false; if (ok) { rep.done = true; rep.doneMsg = msg; rep.msg = ""; rep.kind = null; rep.note = ""; renderRep(); } else { rep.msg = msg; updRep(); } }
    function sendRep() {
      var SPx = window.CalrankSpots, nt = repEl.querySelector("#rmRepNote"); rep.note = nt ? nt.value : rep.note;
      if (posProblem() || !rep.kind || rep.busy || !window.CalrankAuth) { updRep(); return; }
      var ll = lastFix.ll, ac = lastFix.ac, kind = rep.kind, note = (rep.note || "").trim();
      rep.busy = true; rep.msg = "깃발을 꽂는 중…"; updRep();
      var near = SPx.near(kind, ll[0], ll[1], 25);
      if (near) {
        if (!near.key) { fin(false, "25m 안에 이미 지도에 있는 곳입니다. 그곳을 눌러 ‘있어요’로 확인해 주세요."); return; }
        CalrankAuth.rpc("submit_poi_check", { p_route: routeId, p_poi: near.key, p_answer: "yes", p_device: devId() }).then(function (r) {
          var v = r && !r.error ? r.data : "err";
          if (v === "ok") { markDone(routeId + "|" + near.key); fin(true, "이미 누군가 발견한 곳입니다. ‘있어요’ 확인을 더했습니다. 고맙습니다."); }
          else fin(false, v === "slow" ? "너무 자주 눌렀습니다. 잠시 뒤에 다시 해 주세요." : "지금은 기록하지 못했습니다.");
        }, function () { fin(false, "지금은 기록하지 못했습니다."); });
        return;
      }
      CalrankAuth.rpc("submit_poi_user", { p_route: routeId, p_kind: kind, p_lat: ll[0], p_lon: ll[1], p_acc: ac, p_note: note || null }).then(function (r) {
        var v = r && !r.error ? String(r.data) : "err";
        if (v.indexOf("ok:USER:") === 0) {
          var id = Number(v.slice(8)); SPx.add({ id: id, kind: kind, lat: ll[0], lon: ll[1], note: note, mine: true }, myNick()); markDone(routeId + "|USER:" + id);
          fin(true, kind === "danger" ? "깃발을 꽂았습니다. 위험 구간은 2명이 확인하면 모두에게 보입니다. 지금은 나에게만 보입니다." : "깃발을 꽂았습니다. 이 곳의 첫 발견자로 내 닉네임이 남았습니다. 뒤따르는 사람이 확인할수록 믿을 만한 곳이 됩니다.");
        } else if (v.indexOf("dup:") === 0) { markDone(routeId + "|" + v.slice(4)); fin(true, "이미 누군가 발견한 곳입니다. ‘있어요’ 확인을 더했습니다. 고맙습니다."); }
        else fin(false, RMSG[v] || "지금은 깃발을 꽂지 못했습니다.");
      }, function () { fin(false, "지금은 깃발을 꽂지 못했습니다."); });
    }
    repEl.addEventListener("click", function (e) {
      var t = e.target; if (!t || !t.closest) return;
      var kb = t.closest(".k"), id = t.closest("button") && t.closest("button").id;
      if (t.closest(".x") || id === "rmRepClose") { closeRep(); return; }
      if (kb) { rep.kind = kb.getAttribute("data-k"); rep.msg = ""; var nt = repEl.querySelector("#rmRepNote"); if (nt) rep.note = nt.value; renderRep(); return; }
      if (id === "rmRepGo") { sendRep(); return; }
      if (id === "rmRepMore") { rep.done = false; rep.msg = ""; renderRep(); return; }
      if (id === "rmRepLogin") { closeRep(); if (api.exitFull) api.exitFull(); var ab = document.getElementById("acctBtn"); if (ab) ab.click(); }
    });
    function toggleRep() {
      if (!repEl.hidden) { closeRep(); return; }
      rep.done = false; rep.msg = ""; repEl.hidden = false; renderRep();
    }
    Ctl("topleft", "add_place", "깃발 꽂기", "지금 서 있는 곳에 내 이름으로 깃발 꽂기", toggleRep);
  }
  api.attach = attach; window.CalrankMapTools = api;
})();
