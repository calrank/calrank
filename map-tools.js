// 지도 도구 — 전체화면, 내 위치(GPS), 방위(북쪽 표시·보는 방향). Leaflet 지도에 붙인다.
// 위치는 이 브라우저 안에서만 쓰고 서버로 보내지 않는다. 지도는 항상 북쪽이 위다.
// 쓰는 곳: route-map.js(코스·트레일 지도), script.js(메인 대회 지도)
(function () {
  "use strict";
  // 위치는 이 브라우저 안에서만 쓰고 서버로 보내지 않는다. 지도는 항상 북쪽이 위다.
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
      ".rm-hud button{margin-top:6px;min-height:40px;padding:0 16px;border:0;border-radius:999px;background:" + M + ";color:#06362d;font:800 13px sans-serif;box-shadow:0 2px 6px rgba(8,70,58,.25);cursor:pointer}.rm-hud button:active{transform:scale(.96)}" +
      ".rm-me{position:relative;width:22px;height:22px}" +
      ".rm-me i{position:absolute;left:3px;top:3px;width:16px;height:16px;border-radius:50%;background:#1a73e8;border:3px solid #fff;box-shadow:0 0 0 1px rgba(0,0,0,.25),0 2px 6px rgba(0,0,0,.3)}" +
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
    north: "M5.71 9.7c.39.39 1.02.39 1.41 0L11 5.83V21c0 .55.45 1 1 1s1-.45 1-1V5.83l3.88 3.88a.996.996 0 1 0 1.41-1.41L12.7 2.7a.996.996 0 0 0-1.41 0L5.71 8.29a.996.996 0 0 0 0 1.41z"
  };
  function lab(a, ic, t) { a.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="' + ICO[ic] + '"/></svg><span></span>'; a.lastChild.textContent = t; }
  function attach(L, map, opt) {
    var wrap = opt.wrap, all = opt.all || [];
    injectCss();
    var full = false, gps = null, follow = true, me = null, acc = null, meEl = null, heading = null, lock = null, stat = null, gpsBtn = null, fullBtn = null, oriOn = false, C = null, hudEl = null, lastD = null, offWarn = 0;
    var secList = [];
    if (opt.secs && opt.secs.length && !courseId()) loadScript("/seg-core.js", function () {
      secList = opt.secs.filter(function (x) { return x.p && x.p.length > 1; }).map(function (x) { var L2 = 0; for (var i = 1; i < x.p.length; i++) L2 += Math.hypot((x.p[i][1] - x.p[i - 1][1]) * 111320 * Math.cos(x.p[i][0] * Math.PI / 180), (x.p[i][0] - x.p[i - 1][0]) * 111320); return { p: x.p, g: x.g, len: L2 }; });
    });
    var cid = courseId();
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
      if (!best) return "";
      var sc = secList[best.i], off = Math.round(best.o), lines = [];
      if (off > 60) { lines.push('<span class="rm-warn">가장 가까운 등산로에서 ' + off + 'm 떨어져 있습니다.</span>'); var now = Date.now(); if (now - offWarn > 20000) { offWarn = now; try { navigator.vibrate && navigator.vibrate([300, 150, 300]); } catch (e) {} } }
      else lines.push("지금 구간 <b>" + km(sc.len) + "</b> · 평균 경사 <b>" + Math.abs(sc.g).toFixed(0) + "%</b>");
      var sun = CalrankSeg.sun(ll[0], ll[1], new Date());
      if (sun) { var left = Math.round((sun.set - Date.now()) / 60000); lines.push("일몰 " + hm(sun.set) + (left > 0 ? " (" + left + "분 남음)" : ' <span class="rm-warn">일몰 후입니다</span>')); }
      lines.push('<button type="button" id="rmShare">내 위치 문구 복사</button>');
      hudEl = { d: null, ll: ll, ac: ac };
      return lines.join("<br>");
    }
    function hud(ll, ac, off) {
      if (!C && secList.length) return mtHud(ll, ac);
      if (!C) return "";
      var P = C.j.profile, tot = C.c.total, s = C.c.snap(ll[0], ll[1], lastD), d = s.dist, lines = [];
      if (off != null && off > 60) { lines.push('<span class="rm-warn">코스에서 ' + off + 'm 벗어났습니다. 왔던 길로 돌아가세요.</span>'); var now = Date.now(); if (now - offWarn > 20000) { offWarn = now; try { navigator.vibrate && navigator.vibrate([300, 150, 300]); } catch (e) {} } return lines.join("<br>"); }
      lastD = d;
      var nx = C.segs.filter(function (g) { return g.to > d + 30 && g.t !== "flat"; })[0], rest = tot - d;
      lines.push("코스 <b>" + km(d) + "</b> 지점 · 남은 거리 <b>" + km(rest) + "</b>");
      if (nx) lines.push((nx.from > d ? km(nx.from - d) + " 앞 " : "지금 ") + (nx.t === "up" ? "오르막" : "내리막") + " " + km(nx.len) + " · 평균 " + Math.abs(nx.grade).toFixed(0) + "%");
      var eta = new Date(Date.now() + secs(P, d, tot) * 1000), sun = CalrankSeg.sun(ll[0], ll[1], new Date());
      var t = "도착 예상 <b>" + hm(eta) + "</b>(Tobler 근사)";
      if (sun) { var gap = Math.round((sun.set - eta) / 60000); t += " · 일몰 " + hm(sun.set) + (gap < 0 ? ' <span class="rm-warn">일몰 후 도착 예상</span>' : " (여유 " + gap + "분)"); }
      lines.push(t);
      if (sun) { var left = Math.round((sun.set - Date.now()) / 60000), back = secs(P, 0, d) / 60; if (left > 0 && left < back * 1.2 + 30) lines.push('<span class="rm-warn">출발점으로 돌아가는 데 약 ' + Math.round(back) + '분, 일몰까지 ' + left + '분 남았습니다.</span>'); }
      lines.push('<button type="button" id="rmShare">내 위치 문구 복사</button>');
      hudEl = { d: d, ll: ll, ac: ac };
      return lines.join("<br>");
    }
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
        stat.hidden = false; stat.innerHTML = ""; stat.appendChild(document.createTextNode(base));
        if (h) { var hd = document.createElement("div"); hd.className = "rm-hud"; hd.innerHTML = h; stat.appendChild(hd); var sb = hd.querySelector("#rmShare"); if (sb) sb.onclick = share; }
      }, function (err) {
        stop(); say(err && err.code === 1 ? "위치 권한이 꺼져 있습니다. 주소창 왼쪽 자물쇠(또는 aA)에서 위치를 허용하고, 폰의 위치 서비스도 켜져 있는지 확인해 주세요. 카카오톡 같은 앱 안의 브라우저에서는 막혀 있으니 크롬·사파리에서 열어 주세요." : "위치를 가져오지 못했습니다. 하늘이 트인 곳에서 다시 눌러 주세요.");
      }, { enableHighAccuracy: true, maximumAge: 2000, timeout: 20000 });
    });
  }
  api.attach = attach; window.CalrankMapTools = api;
})();
