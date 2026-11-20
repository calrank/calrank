// 경로 지도. 버튼을 눌렀을 때만 Leaflet 과 OpenStreetMap 지도를 불러온다(누르기 전에는 외부로 요청하지 않는다).
// 자료는 #mapData(JSON)에 들어 있다. {"path": [[lat,lon],...]} 또는 {"secs": [{"p": [[lat,lon],...], "g": 평균경사%}, ...]}
(function () {
  "use strict";
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
    water: { label: "음수대", icon: "droplet", c: "#0ea5e9" },
    shelter: { label: "쉼터", icon: "umbrella-on-ground", c: "#16a34a" },
    view: { label: "조망", icon: "camera", c: "#8b5cf6" },
    danger: { label: "위험", icon: "warning", c: "#e5484d" },
    peak: { label: "정상", icon: "mountain", c: "#92400e" }
  };
  // 처음에는 꼭 필요한 것만 보여 주고, 확대할수록 더 보인다. 조망은 기본으로 꺼 둔다(버튼으로 켠다).
  var MINZ = { peak: 0, danger: 0, toilet: 14, water: 14, shelter: 15, view: 16 }, DEFOFF = { view: 1 };
  function spots(L, map) {
    var m = /mountain-(\d+)\.html/.exec(location.pathname);
    if (!m || !window.fetch) return;
    fetch("/data/mountain_spots.json").then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
      var list = j && j.mountains && j.mountains[m[1]];
      if (!list || !list.length) return;
      if (!document.getElementById("spStyle")) {
        var st = document.createElement("style"); st.id = "spStyle";
        st.textContent = ".sp{display:flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:50%;background:#fff;border:2px solid var(--c);box-shadow:0 2px 6px rgba(0,0,0,.28)}.sp img{width:16px;height:16px;margin:0;display:block}" +
          ".sp-bar{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 0;padding:0}.sp-chip{display:inline-flex;align-items:center;gap:6px;min-height:40px;padding:0 14px 0 8px;border:1.5px solid var(--c);border-radius:999px;background:#fff;color:#15110f;font:700 13px/1 sans-serif;cursor:pointer}.sp-chip img{width:20px;height:20px;margin:0}.sp-chip[aria-pressed=false]{opacity:.45;background:transparent}.sp-chip i{font-style:normal;font-weight:600;opacity:.7}" +
          ".sp-note{margin:8px 0 0;font-size:12px;line-height:1.5;opacity:.75}";
        document.head.appendChild(st);
      }
      var groups = {}, counts = {}, seen = {}, want = {};
      function refresh() {
        var z = map.getZoom();
        Object.keys(groups).forEach(function (key) {
          var show = want[key] && z >= MINZ[key];
          if (show && !map.hasLayer(groups[key])) groups[key].addTo(map);
          if (!show && map.hasLayer(groups[key])) map.removeLayer(groups[key]);
        });
      }
      list.forEach(function (s) {
        var k = KIND[s[0]]; if (!k) return;
        var key = s[0] + ":" + s[1].toFixed(4) + ":" + s[2].toFixed(4);  // 같은 종류가 약 10m 안에 겹치면 하나만
        if (seen[key]) return; seen[key] = 1;
        var g = groups[s[0]] || (groups[s[0]] = L.layerGroup()); if (want[s[0]] === undefined) want[s[0]] = !DEFOFF[s[0]]; counts[s[0]] = (counts[s[0]] || 0) + 1;
        var ic = L.divIcon({ className: "", iconSize: [26, 26], iconAnchor: [13, 13],
          html: '<span class="sp" style="--c:' + k.c + '"><img src="/emoji/' + k.icon + '.svg" alt="" width="16" height="16"></span>' });
        L.marker([s[1], s[2]], { icon: ic, keyboard: false, zIndexOffset: s[0] === "danger" ? 500 : 0 })
          .bindTooltip(k.label + " · 자료상 지점").addTo(g);
      });
      map.on("zoomend", refresh); refresh();
      var bar = document.createElement("div"); bar.className = "sp-bar"; bar.setAttribute("role", "group"); bar.setAttribute("aria-label", "지도에 표시할 시설");
      Object.keys(KIND).forEach(function (key) {
        if (!counts[key]) return;
        var k = KIND[key], b = document.createElement("button"); b.type = "button"; b.className = "sp-chip"; b.style.setProperty("--c", k.c);
        b.setAttribute("aria-pressed", want[key] ? "true" : "false");
        b.innerHTML = '<img src="/emoji/' + k.icon + '.svg" alt="" width="20" height="20">' + k.label + " <i>" + counts[key] + "</i>";
        b.addEventListener("click", function () {
          want[key] = b.getAttribute("aria-pressed") !== "true"; b.setAttribute("aria-pressed", want[key] ? "true" : "false");
          if (want[key] && map.getZoom() < MINZ[key]) map.setZoom(MINZ[key]);
          refresh();
        });
        bar.appendChild(b);
      });
      var note = document.createElement("p"); note.className = "sp-note";
      note.textContent = "산림청 등산로 자료의 지점(2016년 12월 기준)입니다. 현장 확인은 하지 않았으니 가기 전에 최신 안내를 확인해 주세요. 지도 바탕의 작은 심볼은 OpenStreetMap 기본 표시입니다.";
      box.parentNode.insertBefore(bar, box.nextSibling); bar.parentNode.insertBefore(note, bar.nextSibling);
    }).catch(function () {});
  }

  // 전체화면·내 위치(GPS)·방위는 map-tools.js 가 붙인다(메인 대회 지도와 같은 코드).
  function controls(L, map, all, secs) {
    function go() { if (window.CalrankMapTools) window.CalrankMapTools.attach(L, map, { wrap: box, all: all, secs: secs }); }
    if (window.CalrankMapTools) return go();
    var t = document.createElement("script"); t.src = "/map-tools.js"; t.onload = go; document.head.appendChild(t);
  }
  if (location.hash === "#trailmap") setTimeout(function () { if (!btn.hidden) btn.click(); }, 0);
  btn.addEventListener("click", function () {
    btn.disabled = true; btn.textContent = "트레일루트 맵을 불러오는 중…";
    load(function () { box.hidden = false; draw(); btn.hidden = true; });
  });
})();
