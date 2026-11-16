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
    st.textContent = ".rm-full{position:fixed!important;inset:0;width:100%!important;height:100vh!important;height:100dvh!important;max-width:none!important;margin:0!important;border:0!important;border-radius:0!important;z-index:99999}" +
      "body.rm-lock{overflow:hidden}" +
      ".rm-ctl a{display:flex!important;align-items:center;justify-content:center;width:auto!important;min-width:44px;height:44px!important;padding:0 12px;font:700 14px/1 sans-serif;color:#222!important;background:#fff;text-decoration:none!important;cursor:pointer;white-space:nowrap}" +
      ".rm-ctl a[aria-pressed=true]{background:#222;color:#fff!important}" +
      ".rm-north{display:flex;flex-direction:column;align-items:center;justify-content:center;width:44px;height:44px;border-radius:50%;background:rgba(255,255,255,.92);color:#222;font:800 12px/1.1 sans-serif;box-shadow:0 1px 4px rgba(0,0,0,.35);pointer-events:none}" +
      ".rm-north b{font-size:17px;line-height:1}" +
      ".rm-stat{max-width:calc(100vw - 90px);padding:7px 10px;border-radius:8px;background:rgba(255,255,255,.94);color:#222;font:600 13px/1.4 sans-serif;box-shadow:0 1px 4px rgba(0,0,0,.3)}" +
      ".rm-hud{line-height:1.55;margin-top:6px;padding-top:6px;border-top:1px solid #ddd;font-weight:600}.rm-hud b{font-weight:800}.rm-warn{color:#b3261e;font-weight:800}.rm-hud button{margin-top:4px;min-height:36px;padding:0 10px;border:1px solid #222;border-radius:6px;background:#fff;color:#222;font:700 13px sans-serif}" +
      ".rm-me{position:relative;width:22px;height:22px}" +
      ".rm-me i{position:absolute;left:3px;top:3px;width:16px;height:16px;border-radius:50%;background:#1a73e8;border:3px solid #fff;box-shadow:0 0 0 1px rgba(0,0,0,.25)}" +
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
  function attach(L, map, opt) {
    var wrap = opt.wrap, all = opt.all || [];
    injectCss();
    var full = false, gps = null, follow = true, me = null, acc = null, meEl = null, heading = null, lock = null, stat = null, gpsBtn = null, fullBtn = null, oriOn = false, C = null, hudEl = null, lastD = null, offWarn = 0;
    var cid = courseId();
    if (cid) fetch("/field/" + cid + ".json").then(function (r) { return r.ok ? r.json() : null; }).then(function (j) { if (j && j.profile && j.path && j.path.length > 1) loadScript("/seg-core.js", function () { C = { j: j, c: CalrankSeg.course(j.path, j.profile[j.profile.length - 1][0]), segs: CalrankSeg.segments(j.profile) }; }); }).catch(function () {});
    function Ctl(pos, label, title, fn) {
      var C = L.Control.extend({ options: { position: pos }, onAdd: function () {
        var d = L.DomUtil.create("div", "leaflet-bar rm-ctl"), a = L.DomUtil.create("a", "", d);
        a.href = "#"; a.setAttribute("role", "button"); a.setAttribute("aria-label", title); a.title = title; a.textContent = label;
        L.DomEvent.disableClickPropagation(d); L.DomEvent.on(a, "click", function (e) { L.DomEvent.preventDefault(e); fn(a); });
        return d; } });
      var c = new C(); c.addTo(map); return c;
    }
    // 북쪽 표시(지도는 북쪽이 위로 고정)
    var N = L.Control.extend({ options: { position: "topright" }, onAdd: function () { var d = L.DomUtil.create("div", "rm-north"); d.innerHTML = "<b>↑</b>북"; d.setAttribute("aria-label", "지도는 북쪽이 위입니다"); return d; } });
    new N().addTo(map);
    fullBtn = Ctl("topright", "전체화면", "지도를 화면 가득 보기", function (a) {
      full = !full; wrap.classList.toggle("rm-full", full); document.body.classList.toggle("rm-lock", full);
      a.textContent = full ? "닫기" : "전체화면"; a.setAttribute("aria-pressed", full ? "true" : "false");
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
      gpsBtn.textContent = "내 위치"; gpsBtn.setAttribute("aria-pressed", "false"); say("");
    }
    function share() {
      if (!hudEl || !C) return;
      var t = (C.j.name || "코스") + " · 코스 " + km(hudEl.d) + " 지점 · 위도 " + hudEl.ll[0].toFixed(5) + ", 경도 " + hudEl.ll[1].toFixed(5) + " (GPS 오차 ±" + hudEl.ac + "m) · " + hm(new Date()) + " 기준. 긴급 상황은 119에 이 위치를 불러 주세요.";
      if (navigator.share) navigator.share({ text: t }).catch(function () {});
      else if (navigator.clipboard) navigator.clipboard.writeText(t).then(function () { say("위치 문구를 복사했습니다."); }, function () { say(t); });
      else say(t);
    }
    function hud(ll, ac, off) {
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
    Ctl("topleft", "내 위치", "GPS로 내 위치 보기", function (a) {
      gpsBtn = a;
      if (gps !== null) { stop(); return; }
      if (!navigator.geolocation) { say("이 브라우저는 위치를 지원하지 않습니다."); return; }
      say("위치를 찾는 중입니다."); a.textContent = "위치 끄기"; a.setAttribute("aria-pressed", "true"); follow = true; startOri();
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
        var base = off == null ? "GPS 오차 ±" + ac + "m" : off <= 30 ? "코스 위에 있습니다 (코스에서 " + off + "m · GPS 오차 ±" + ac + "m)" : off > 100 ? "코스에서 약 " + offT + " 벗어나 있습니다 (GPS 오차 ±" + ac + "m)" : "코스에서 약 " + offT + " 떨어져 있습니다 (GPS 오차 ±" + ac + "m)", h = hud(ll, ac, off);
        stat.hidden = false; stat.innerHTML = ""; stat.appendChild(document.createTextNode(base));
        if (h) { var hd = document.createElement("div"); hd.className = "rm-hud"; hd.innerHTML = h; stat.appendChild(hd); var sb = hd.querySelector("#rmShare"); if (sb) sb.onclick = share; }
      }, function (err) {
        stop(); say(err && err.code === 1 ? "위치 권한이 꺼져 있습니다. 주소창 왼쪽 자물쇠(또는 aA)에서 위치를 허용하고, 폰의 위치 서비스도 켜져 있는지 확인해 주세요. 카카오톡 같은 앱 안의 브라우저에서는 막혀 있으니 크롬·사파리에서 열어 주세요." : "위치를 가져오지 못했습니다. 하늘이 트인 곳에서 다시 눌러 주세요.");
      }, { enableHighAccuracy: true, maximumAge: 2000, timeout: 20000 });
    });
  }
  api.attach = attach; window.CalrankMapTools = api;
})();
