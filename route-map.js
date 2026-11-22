// 경로 지도. 버튼을 눌렀을 때만 Leaflet 과 OpenStreetMap 지도를 불러온다(누르기 전에는 외부로 요청하지 않는다).
// 자료는 #mapData(JSON)에 들어 있다. {"path": [[lat,lon],...]} 또는 {"secs": [{"p": [[lat,lon],...], "g": 평균경사%}, ...]}
(function () {
  "use strict";
  var mtSpots = [];
  var btn = document.getElementById("mapBtn"), box = document.getElementById("mapBox"), el = document.getElementById("mapData");
  if (!btn || !box || !el) return;
  var data; try { data = JSON.parse(el.textContent); } catch (e) { return; }
  var V = "1.9.4", BASE = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/" + V + "/";
  var COL = [[5, "#14bfa0"], [10, "#f2c230"], [15, "#f28a30"], [999, "#e5484d"]];  // 완만할수록 민트, 가파를수록 노랑·주황·빨강
  function colorOf(g) { g = Math.abs(g); for (var i = 0; i < COL.length; i++) if (g < COL[i][0]) return COL[i][1]; return COL[3][1]; }
  function load(cb) {
    if (window.L) return cb();
    var css = document.createElement("link"); css.rel = "stylesheet"; css.href = BASE + "leaflet.css"; document.head.appendChild(css);
    var s = document.createElement("script"); s.src = BASE + "leaflet.js"; s.onload = cb;
    s.onerror = function () { btn.disabled = false; btn.textContent = "트레일루트 맵을 불러오지 못했어요. 다시 눌러 보세요"; };
    document.head.appendChild(s);
  }
  function draw() {
    var L = window.L, map = L.map(box, { scrollWheelZoom: false }), all = [];
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 17, attribution: "© OpenStreetMap contributors" }).addTo(map);
    if (data.secs) {
      data.secs.forEach(function (s) {
        if (!s.p || s.p.length < 2) return;
        L.polyline(s.p, { color: "#fff", weight: 9, opacity: 0.9, lineCap: "round", lineJoin: "round" }).addTo(map); L.polyline(s.p, { color: colorOf(s.g), weight: 5, opacity: 1, lineCap: "round", lineJoin: "round" }).addTo(map); all = all.concat(s.p);
      });
    } else if (data.path && data.path.length > 1) {
      L.polyline(data.path, { color: "#fff", weight: 9, opacity: 0.9, lineCap: "round", lineJoin: "round" }).addTo(map); L.polyline(data.path, { color: "#14bfa0", weight: 5, opacity: 1, lineCap: "round", lineJoin: "round" }).addTo(map);
      L.circleMarker(data.path[0], { radius: 7, color: "#fff", weight: 2, fillColor: "#0e9f87", fillOpacity: 1 }).addTo(map).bindTooltip("출발");
      L.circleMarker(data.path[data.path.length - 1], { radius: 7, color: "#fff", weight: 2, fillColor: "#15110f", fillOpacity: 1 }).addTo(map).bindTooltip("도착");
      all = data.path;
    }
    if (all.length) map.fitBounds(L.latLngBounds(all), { padding: [16, 16] });
    setTimeout(function () { map.invalidateSize(); }, 50);
    controls(L, map, all, data.secs || null);
    spots(L, map);
  }

  // 시설 지점. 산림청 등산로 자료의 지점(2016-12-31 기준)을 산 페이지 지도에만 올린다. 현장 확인은 하지 않았다.
  var KIND = {
    toilet: { label: "화장실", icon: "toilet", c: "#3b82f6" },
    water: { label: "식수·샘터", icon: "droplet", c: "#0ea5e9" },
    spring: { label: "샘터", icon: "droplet", c: "#0891b2" },
    shelter: { label: "쉼터", icon: "umbrella-on-ground", c: "#16a34a" },
    view: { label: "조망", icon: "camera", c: "#8b5cf6" },
    danger: { label: "위험", icon: "warning", c: "#e5484d" },
    peak: { label: "정상", icon: "mountain", c: "#92400e" }
  };
  // 마커 글리프: Material Symbols Rounded(Apache-2.0). 직접 그리지 않고 그대로 쓴다.
  var GLY = {"toilet": "M212-110v-270h-20q-12.75 0-21.37-8.63Q162-397.25 162-410v-198q0-29 21.5-50.5t50.24-21.5h104.52q28.74 0 50.24 21.5Q410-637 410-608v198q0 12.75-8.62 21.37Q392.75-380 380-380h-20v270q0 12.75-8.62 21.37Q342.75-80 330-80h-88q-12.75 0-21.37-8.63Q212-97.25 212-110Zm22.5-645.42q-21.5-21.42-21.5-51.5t21.42-51.58q21.42-21.5 51.5-21.5t51.58 21.42q21.5 21.42 21.5 51.5t-21.42 51.58q-21.42 21.5-51.5 21.5t-51.58-21.42ZM630-110v-210h-65q-14.55 0-23.27-12-8.73-12-4.73-26l75-273q7.22-23.59 26.61-36.3Q658-680 684-680t45.39 12.7Q748.78-654.59 756-631l75 273q4 14-4.73 26-8.72 12-23.27 12h-65v210q0 12.75-8.62 21.37Q720.75-80 708-80h-48q-12.75 0-21.37-8.63Q630-97.25 630-110Zm2.5-645.42q-21.5-21.42-21.5-51.5t21.42-51.58q21.42-21.5 51.5-21.5t51.58 21.42q21.5 21.42 21.5 51.5t-21.42 51.58q-21.42 21.5-51.5 21.5t-51.58-21.42Z", "water": "M251.5-174Q160-268 160-408q0-64 29-127t72.5-121q43.5-58 94-108.5T450-854q7-6 14.5-8.5T480-865q8 0 15.5 2.5T510-854q44 39 94.5 89.5t94 108.5Q742-598 771-535t29 127q0 140-91.5 234T480-80q-137 0-228.5-94ZM479-208q16 0 24.5-5.5T512-230q0-11-8.5-17t-25.5-6q-42 0-85.5-26.5T337-373q-2-9-9-14.5t-15-5.5q-11 0-17 8.5t-4 17.5q15 84 71 121.5T479-208Z", "spring": "M251.5-174Q160-268 160-408q0-64 29-127t72.5-121q43.5-58 94-108.5T450-854q7-6 14.5-8.5T480-865q8 0 15.5 2.5T510-854q44 39 94.5 89.5t94 108.5Q742-598 771-535t29 127q0 140-91.5 234T480-80q-137 0-228.5-94ZM479-208q16 0 24.5-5.5T512-230q0-11-8.5-17t-25.5-6q-42 0-85.5-26.5T337-373q-2-9-9-14.5t-15-5.5q-11 0-17 8.5t-4 17.5q15 84 71 121.5T479-208Z", "shelter": "M160-180v-341l-60 46q-10 8-22 6t-20-12q-8-10-6-22t12-20l96-73v-84q0-13 8.5-21.5T190-710q13 0 21.5 8.5T220-680v38l224-170q8-6 17-9.5t19-3.5q10 0 19 3.5t17 9.5l381 290q10 8 11.5 20t-6.5 22q-8 10-19.5 11.5T861-475l-61-46v341q0 25-17.5 42.5T740-120H525q-6 0-10.5-4.5T510-135v-175q0-13-8.5-21.5T480-340q-13 0-21.5 8.5T450-310v175q0 6-4.5 10.5T435-120H220q-25 0-42.5-17.5T160-180Zm35-580q-15 0-24.5-11t-4.5-24q11-34 40-54.5t64-20.5q14 0 26-7t18-20q5-9 12.5-16t18.5-7q15 0 24.5 11t4.5 24q-12 34-40.5 54.5T270-810q-14 0-25.5 7.5T226-783q-5 9-12.5 16t-18.5 7Z", "view": "M480-267q72 0 121-49t49-121q0-73-49-121.5T480-607q-73 0-121.5 48.5T310-437q0 72 48.5 121T480-267Zm0-60q-48 0-79-31.5T370-437q0-48 31-79t79-31q47 0 78.5 31t31.5 79q0 47-31.5 78.5T480-327ZM140-120q-24 0-42-18t-18-42v-513q0-23 18-41.5t42-18.5h147l55-66q8-11 20-16t26-5h184q14 0 26 5t20 16l55 66h147q23 0 41.5 18.5T880-693v513q0 24-18.5 42T820-120H140Z", "danger": "M92-120q-9 0-15.5-4T66-135q-4-7-4.5-14.5T66-165l388-670q5-8 11.5-11.5T480-850q8 0 14.5 3.5T506-835l388 670q5 8 4.5 15.5T894-135q-4 7-10.5 11t-15.5 4H92Zm413.5-125.5Q514-254 514-267t-8.5-21.5Q497-297 484-297t-21.5 8.5Q454-280 454-267t8.5 21.5Q471-237 484-237t21.5-8.5Zm0-111Q514-365 514-378v-164q0-13-8.5-21.5T484-572q-13 0-21.5 8.5T454-542v164q0 13 8.5 21.5T484-348q13 0 21.5-8.5Z", "peak": "m76-288 180-240q5-6 11-9t13-3q7 0 13 3t11 9l162 216q5 6 11 9t13 3q19 0 27-16.5t-3-31.5L411-485q-6-8-6-18t6-18l125-167q5-6 11-9t13-3q7 0 13 3t11 9l300 400q11 15 3 31.5T860-240H100q-19 0-27-16.5t3-31.5Z"};
  function sign(key, px) { return '<svg viewBox="0 -960 960 960" width="' + px + '" height="' + px + '" aria-hidden="true"><path fill="#fff" d="' + GLY[key] + '"/></svg>'; }
  // 처음에는 꼭 필요한 것만 보여 주고, 확대할수록 더 보인다. 조망은 기본으로 꺼 둔다(버튼으로 켠다).
  var MINZ = { peak: 0, danger: 0, toilet: 14, water: 14, spring: 14, shelter: 15, view: 16 }, DEFOFF = { view: 1 };
  var COURSEZ = { peak: 0, danger: 0, toilet: 12, water: 12, spring: 12, shelter: 13, view: 14 };  // 코스는 길어서 더 멀리서부터 보인다
  // 코스 페이지: data/course_pois.json 의 지점은 '출발점에서 몇 m' 로만 들어 있으니 경로 위의 위치로 바꾼다.
  var KOR = { "화장실": "toilet", "식수대": "water", "약수터·샘터": "water", "쉼터": "shelter", "대피소": "shelter", "전망": "view" };
  function planar(a, b) {
    var x = (b[1] - a[1]) * Math.PI / 180 * Math.cos((a[0] + b[0]) / 2 * Math.PI / 180), y = (b[0] - a[0]) * Math.PI / 180;
    return 6371000 * Math.sqrt(x * x + y * y);
  }
  function pointAt(path, cum, d) {
    for (var i = 1; i < path.length; i++) {
      if (cum[i] >= d) {
        var seg = cum[i] - cum[i - 1], t = seg > 0 ? (d - cum[i - 1]) / seg : 0;
        return [path[i - 1][0] + (path[i][0] - path[i - 1][0]) * t, path[i - 1][1] + (path[i][1] - path[i - 1][1]) * t];
      }
    }
    return path[path.length - 1];
  }
  function courseList(cb) {
    var m = /course-(dr|ft)-(.+)\.html/.exec(location.pathname), path = data.path;
    if (!m || !path || path.length < 2) return cb(null);
    var rid = (m[1] === "dr" ? "두루누비:dr-" : "숲길:ft-") + m[2];
    fetch("/data/course_pois.json").then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
      var r = j && j.routes && j.routes[rid];
      if (!r || !r.pois || !r.pois.length) return cb(null);
      var cum = [0]; for (var i = 1; i < path.length; i++) cum.push(cum[i - 1] + planar(path[i - 1], path[i]));
      var list = []; r.pois.forEach(function (p) { var k = KOR[p[1]]; if (!k) return; var ll = pointAt(path, cum, Math.min(p[0], cum[cum.length - 1])); list.push([k, ll[0], ll[1], p[3] ? p[3] + ":" + (Math.round(p[0] / 10) * 10) : null]); });
      cb(list, "OpenStreetMap 기여자가 등록한 지점(" + (j.built || "") + " 수집)입니다. 현장 확인은 하지 않았고, 목록에 없다고 실제로 없다는 뜻은 아닙니다. 가기 전에 최신 안내를 확인해 주세요.");
    }).catch(function () { cb(null); });
  }
  function spots(L, map) {
    if (!window.fetch) return;
    var m = /mountain-(\d+)\.html/.exec(location.pathname);
    var get = m ? function (cb) {
      fetch("/data/mountain_spots.json").then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
        mtSpots.length = 0; ((j && j.mountains && j.mountains[m[1]]) || []).forEach(function (s) { mtSpots.push([s[0], s[1], s[2], String(s[0]).toUpperCase() + ":" + Math.round(s[1] * 1e4) + "-" + Math.round(s[2] * 1e4)]); }); cb(mtSpots.length ? mtSpots : null, "산림청 등산로 자료의 지점(2016년 12월 기준)입니다. 현장 확인은 하지 않았으니 가기 전에 최신 안내를 확인해 주세요. 지도 바탕의 작은 심볼은 OpenStreetMap 기본 표시입니다.");
      }).catch(function () { cb(null); });
    } : courseList;
    var MZ = m ? MINZ : COURSEZ;
    get(function (list, noteText) {
      if (!list || !list.length) return;
      if (!document.getElementById("spStyle")) {
        var st = document.createElement("style"); st.id = "spStyle";
        st.textContent = ".sp{display:flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:9px;background:var(--c);border:2px solid #fff;box-shadow:0 0 0 1px rgba(0,0,0,.18),0 2px 6px rgba(0,0,0,.3);box-sizing:border-box}.sp svg{display:block}.sp-dot{display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:8px;background:var(--c)}.sp-dot svg{display:block}" +
          ".sp-pop{font:600 13px/1.6 sans-serif;color:#15110f;min-width:150px}.sp-pop .by{margin:4px 0 2px;font-weight:900;font-size:14px}.sp-pop .cnt{color:#555}.sp-pop button{margin-top:8px;min-height:36px;padding:0 12px;border:1.5px solid #bbb;border-radius:999px;background:#fff;color:#444;font:700 12px/1 sans-serif;cursor:pointer}.sp-pop .rmsg{margin-top:6px;font-size:12px;color:#444}" +
          ".sp-bar{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 0;padding:0}.sp-chip{display:inline-flex;align-items:center;gap:6px;min-height:40px;padding:0 14px 0 8px;border:1.5px solid var(--c);border-radius:999px;background:#fff;color:#15110f;font:700 13px/1 sans-serif;cursor:pointer}.sp-chip[aria-pressed=false]{opacity:.45;background:transparent}.sp-chip i{font-style:normal;font-weight:600;opacity:.7}" +
          ".sp-note{margin:8px 0 0;font-size:12px;line-height:1.5;opacity:.75}";
        document.head.appendChild(st);
      }
      var groups = {}, counts = {}, seen = {}, want = {}, byKey = {};
      function refresh() {
        var z = map.getZoom();
        Object.keys(groups).forEach(function (key) {
          var show = want[key] && z >= MZ[key];
          if (show && !map.hasLayer(groups[key])) groups[key].addTo(map);
          if (!show && map.hasLayer(groups[key])) map.removeLayer(groups[key]);
        });
      }
      list.forEach(function (s) {
        var k = KIND[s[0]]; if (!k) return;
        var key = s[0] + ":" + s[1].toFixed(4) + ":" + s[2].toFixed(4);  // 같은 종류가 약 10m 안에 겹치면 하나만
        if (seen[key]) return; seen[key] = 1;
        var g = groups[s[0]] || (groups[s[0]] = L.layerGroup()); if (want[s[0]] === undefined) want[s[0]] = !DEFOFF[s[0]]; counts[s[0]] = (counts[s[0]] || 0) + 1;
        var ic = L.divIcon({ className: "", iconSize: [28, 28], iconAnchor: [14, 14],
          html: '<span class="sp" style="--c:' + k.c + '">' + sign(s[0], 18) + '</span>' });
        var mk = L.marker([s[1], s[2]], { icon: ic, keyboard: false, zIndexOffset: s[0] === "danger" ? 500 : 0 })
          .bindTooltip(k.label + " · 자료상 지점").addTo(g);
        if (s[3]) byKey[s[3]] = { m: mk, label: k.label };
      });
      map.on("zoomend", refresh); refresh();
      // 이 코스에서 사람들이 직접 확인한 기록(닉네임·횟수·최근 날짜)을 마커 설명에 붙인다.
      var cm = /course-(dr|ft)-(.+)\.html/.exec(location.pathname), routeKey = cm ? cm[1] + "-" + cm[2] : (m ? "mt-" + m[1] : null);
      if (routeKey && Object.keys(byKey).length) {
        var tries = 0, wait = setInterval(function () {
          if (!window.CalrankAuth && ++tries < 40) return; clearInterval(wait); if (!window.CalrankAuth) return;
          CalrankAuth.rpc("poi_check_summary", { p_route: routeKey }).then(function (r) {
            if (!r || r.error || !Array.isArray(r.data)) return;
            window.CalrankChecks = window.CalrankChecks || {};
            r.data.forEach(function (x) {
              window.CalrankChecks[x.poi_key] = { first_name: x.first_name || "", yes_n: x.yes_n || 0, no_n: x.no_n || 0 };
              var e = byKey[x.poi_key]; if (!e || !(x.yes_n || x.no_n)) return;
              var days = x.last_at ? Math.max(0, Math.floor((Date.now() - new Date(x.last_at)) / 864e5)) : null;
              var who = String(x.first_name || "").replace(/[^가-힣A-Za-z0-9_]/g, "");
              var h = '<div class="sp-pop"><b>' + e.label + "</b> · 자료상 지점";
              if (who) h += '<div class="by">' + who + " 님이 처음 확인</div>";
              if (x.yes_n) h += '<div class="cnt">' + x.yes_n + "명이 있다고 확인" + (days == null ? "" : " · 최근 " + (days === 0 ? "오늘" : days + "일 전")) + "</div>";
              if (x.no_n >= 2) h += '<div class="cnt">없다는 기록 ' + x.no_n + "명</div>";
              if (who) h += '<button type="button" class="rep">닉네임 신고</button><div class="rmsg" aria-live="polite"></div>';
              h += "</div>";
              e.m.unbindTooltip(); e.m.bindPopup(h, { maxWidth: 240 });
              e.m.on("popupopen", function (ev) {
                var root = ev.popup.getElement(), btn = root && root.querySelector(".rep"), msg = root && root.querySelector(".rmsg");
                if (!btn || btn._b) return; btn._b = 1;
                btn.addEventListener("click", function () {
                  if (!window.CalrankAuth || !CalrankAuth.user()) { msg.textContent = "로그인하면 신고할 수 있습니다."; return; }
                  btn.disabled = true; msg.textContent = "신고하는 중…";
                  CalrankAuth.rpc("report_nickname", { p_route: routeKey, p_poi: x.poi_key }).then(function (rr) {
                    var v = rr && !rr.error ? rr.data : "err";
                    msg.textContent = v === "ok" ? "신고했습니다. 여러 명이 신고하면 자동으로 가려집니다."
                      : v === "self" ? "내 닉네임은 신고할 수 없습니다."
                      : v === "none" ? "신고할 닉네임이 없습니다."
                      : v === "slow" ? "신고가 많습니다. 잠시 뒤에 다시 해 주세요."
                      : v === "login" ? "로그인하면 신고할 수 있습니다." : "지금은 신고하지 못했습니다.";
                    btn.disabled = v !== "ok" && v !== "self" && v !== "none" ? false : true;
                  }, function () { btn.disabled = false; msg.textContent = "지금은 신고하지 못했습니다."; });
                });
              });
            });
          });
        }, 250);
      }
      var bar = document.createElement("div"); bar.className = "sp-bar"; bar.setAttribute("role", "group"); bar.setAttribute("aria-label", "지도에 표시할 시설");
      Object.keys(KIND).forEach(function (key) {
        if (!counts[key]) return;
        var k = KIND[key], b = document.createElement("button"); b.type = "button"; b.className = "sp-chip"; b.style.setProperty("--c", k.c);
        b.setAttribute("aria-pressed", want[key] ? "true" : "false");
        b.innerHTML = '<span class="sp-dot" style="--c:' + k.c + '">' + sign(key, 16) + '</span>' + k.label + " <i>" + counts[key] + "</i>";
        b.addEventListener("click", function () {
          want[key] = b.getAttribute("aria-pressed") !== "true"; b.setAttribute("aria-pressed", want[key] ? "true" : "false");
          if (want[key] && map.getZoom() < MZ[key]) map.setZoom(MZ[key]);
          refresh();
        });
        bar.appendChild(b);
      });
      var note = document.createElement("p"); note.className = "sp-note";
      note.textContent = noteText;
      box.parentNode.insertBefore(bar, box.nextSibling); bar.parentNode.insertBefore(note, bar.nextSibling);
    });
  }

  // 전체화면·내 위치(GPS)·방위는 map-tools.js 가 붙인다(메인 대회 지도와 같은 코드).
  function controls(L, map, all, secs) {
    function go() { if (window.CalrankMapTools) window.CalrankMapTools.attach(L, map, { wrap: box, all: all, secs: secs, spots: mtSpots }); }
    if (window.CalrankMapTools) return go();
    var t = document.createElement("script"); t.src = "/map-tools.js"; t.onload = go; document.head.appendChild(t);
  }
  if (location.hash === "#trailmap") setTimeout(function () { if (!btn.hidden) btn.click(); }, 0);
  btn.addEventListener("click", function () {
    btn.disabled = true; btn.textContent = "트레일루트 맵을 불러오는 중…";
    load(function () { box.hidden = false; draw(); btn.hidden = true; });
  });
})();
