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
    water: { label: "식수·샘터", icon: "droplet", c: "#0ea5e9" },
    spring: { label: "샘터", icon: "droplet", c: "#0891b2" },
    shelter: { label: "쉼터", icon: "umbrella-on-ground", c: "#16a34a" },
    view: { label: "조망", icon: "camera", c: "#8b5cf6" },
    danger: { label: "위험", icon: "warning", c: "#e5484d" },
    peak: { label: "정상", icon: "mountain", c: "#92400e" }
  };
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
      var list = []; r.pois.forEach(function (p) { var k = KOR[p[1]]; if (!k) return; var ll = pointAt(path, cum, Math.min(p[0], cum[cum.length - 1])); list.push([k, ll[0], ll[1]]); });
      cb(list, "OpenStreetMap 기여자가 등록한 지점(" + (j.built || "") + " 수집)입니다. 현장 확인은 하지 않았고, 목록에 없다고 실제로 없다는 뜻은 아닙니다. 가기 전에 최신 안내를 확인해 주세요.");
    }).catch(function () { cb(null); });
  }
  function spots(L, map) {
    if (!window.fetch) return;
    var m = /mountain-(\d+)\.html/.exec(location.pathname);
    var get = m ? function (cb) {
      fetch("/data/mountain_spots.json").then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
        cb(j && j.mountains && j.mountains[m[1]], "산림청 등산로 자료의 지점(2016년 12월 기준)입니다. 현장 확인은 하지 않았으니 가기 전에 최신 안내를 확인해 주세요. 지도 바탕의 작은 심볼은 OpenStreetMap 기본 표시입니다.");
      }).catch(function () { cb(null); });
    } : courseList;
    var MZ = m ? MINZ : COURSEZ;
    get(function (list, noteText) {
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
