// 경로 지도. 버튼을 눌렀을 때만 Leaflet 과 OpenStreetMap 지도를 불러온다(누르기 전에는 외부로 요청하지 않는다).
// 자료는 #mapData(JSON)에 들어 있다. {"path": [[lat,lon],...]} 또는 {"secs": [{"p": [[lat,lon],...], "g": 평균경사%}, ...]}
(function () {
  "use strict";
  var btn = document.getElementById("mapBtn"), box = document.getElementById("mapBox"), el = document.getElementById("mapData");
  if (!btn || !box || !el) return;
  var data; try { data = JSON.parse(el.textContent); } catch (e) { return; }
  var V = "1.9.4", BASE = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/" + V + "/";
  var COL = [[5, "#b9c7a0"], [10, "#e3c46a"], [15, "#e08a45"], [999, "#c4433a"]];
  function colorOf(g) { g = Math.abs(g); for (var i = 0; i < COL.length; i++) if (g < COL[i][0]) return COL[i][1]; return COL[3][1]; }
  function load(cb) {
    if (window.L) return cb();
    var css = document.createElement("link"); css.rel = "stylesheet"; css.href = BASE + "leaflet.css"; document.head.appendChild(css);
    var s = document.createElement("script"); s.src = BASE + "leaflet.js"; s.onload = cb;
    s.onerror = function () { btn.disabled = false; btn.textContent = "지도를 불러오지 못했어요. 다시 눌러 보세요"; };
    document.head.appendChild(s);
  }
  function draw() {
    var L = window.L, map = L.map(box, { scrollWheelZoom: false }), all = [];
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 17, attribution: "© OpenStreetMap contributors" }).addTo(map);
    if (data.secs) {
      data.secs.forEach(function (s) {
        if (!s.p || s.p.length < 2) return;
        L.polyline(s.p, { color: colorOf(s.g), weight: 4, opacity: 0.95 }).addTo(map); all = all.concat(s.p);
      });
    } else if (data.path && data.path.length > 1) {
      L.polyline(data.path, { color: "#c4433a", weight: 4, opacity: 0.95 }).addTo(map);
      L.circleMarker(data.path[0], { radius: 7, color: "#fff", weight: 2, fillColor: "#3b7d4f", fillOpacity: 1 }).addTo(map).bindTooltip("출발");
      L.circleMarker(data.path[data.path.length - 1], { radius: 7, color: "#fff", weight: 2, fillColor: "#2f5d8a", fillOpacity: 1 }).addTo(map).bindTooltip("도착");
      all = data.path;
    }
    if (all.length) map.fitBounds(L.latLngBounds(all), { padding: [16, 16] });
    setTimeout(function () { map.invalidateSize(); }, 50);
  }
  btn.addEventListener("click", function () {
    btn.disabled = true; btn.textContent = "지도를 불러오는 중…";
    load(function () { box.hidden = false; draw(); btn.hidden = true; });
  });
})();
