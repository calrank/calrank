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
    controls(L, map, all);
  }

  // 전체화면·내 위치(GPS)·방위는 map-tools.js 가 붙인다(메인 대회 지도와 같은 코드).
  function controls(L, map, all) {
    function go() { if (window.CalrankMapTools) window.CalrankMapTools.attach(L, map, { wrap: box, all: all }); }
    if (window.CalrankMapTools) return go();
    var t = document.createElement("script"); t.src = "/map-tools.js"; t.onload = go; document.head.appendChild(t);
  }
  if (location.hash === "#trailmap") setTimeout(function () { if (!btn.hidden) btn.click(); }, 0);
  btn.addEventListener("click", function () {
    btn.disabled = true; btn.textContent = "트레일루트 맵을 불러오는 중…";
    load(function () { box.hidden = false; draw(); btn.hidden = true; });
  });
})();
