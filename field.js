// 코스 현장 보기 — 달리는 중 "지금 평지/오르막/내리막이고, 다음에 어떻게 바뀌는지"를 크게 보여 준다.
//
// 자료: field/<코스>.json (두루누비 코스 정보를 코스별로 쪼갠 것, 이용 제한 없음).
// 계산은 이 브라우저 안에서만 한다. 위치는 서버로 보내지 않는다.
//
// 구분 기준: 평균 경사 3% 이상이고 500m 이상이면 오르막/내리막으로 본다. Garmin ClimbPro가
// 오르막으로 치는 최소 길이 500m, 최소 평균 경사 3%를 참고했다. 연구 결과가 아니라 읽기 편하게
// 정한 표시 기준이며 화면에도 그렇게 적는다.
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var NAME = { up: "오르막", down: "내리막", flat: "평지" };
  var GL = { up: "▲", down: "▼", flat: "▶" };

  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function km(m) { return (m / 1000).toFixed(m < 1000 ? 2 : 1).replace(/\.0$/, "") + "km"; }
  function mm(m) { return Math.round(m / 10) * 10 + "m"; }

  // ── 구간 나누기 ──────────────────────────────────────────
  function segments(P) {
    var n = P.length, d = P.map(function (p) { return p[0]; }), e = P.map(function (p) { return p[1]; });
    var es = e.map(function (v, i) { var a = Math.max(0, i - 1), b = Math.min(n - 1, i + 1), s = 0, k = 0; for (var j = a; j <= b; j++) { s += e[j]; k++; } return s / k; });
    var lab = [];
    for (var i = 0; i < n - 1; i++) { var j2 = Math.min(i + 2, n - 1), g = (es[j2] - es[i]) / (d[j2] - d[i]); lab.push(g >= 0.03 ? "up" : g <= -0.03 ? "down" : "flat"); }
    var runs = [];
    lab.forEach(function (l, i) { var last = runs[runs.length - 1]; if (last && last.t === l) last.b = i + 1; else runs.push({ t: l, a: i, b: i + 1 }); });
    function dist(r) { return d[r.b] - d[r.a]; }
    var changed = true;
    while (changed && runs.length > 1) {
      changed = false;
      for (var i3 = 0; i3 < runs.length; i3++) {
        var minLen = runs[i3].t === "flat" ? 200 : 150;
        if (dist(runs[i3]) < minLen) { var tgt = i3 > 0 ? i3 - 1 : i3 + 1; runs[tgt].a = Math.min(runs[tgt].a, runs[i3].a); runs[tgt].b = Math.max(runs[tgt].b, runs[i3].b); runs.splice(i3, 1); changed = true; break; }
      }
      for (var k2 = runs.length - 1; k2 > 0; k2--) { if (runs[k2].t === runs[k2 - 1].t) { runs[k2 - 1].b = runs[k2].b; runs.splice(k2, 1); changed = true; } }
    }
    runs.forEach(function (r) { if (r.t !== "flat" && dist(r) < 500) r.t = "flat"; });
    for (var k3 = runs.length - 1; k3 > 0; k3--) { if (runs[k3].t === runs[k3 - 1].t) { runs[k3 - 1].b = runs[k3].b; runs.splice(k3, 1); } }
    for (var m = 1; m < runs.length - 1; m++) { if (runs[m].t === "flat" && dist(runs[m]) < 300 && runs[m - 1].t === runs[m + 1].t && runs[m - 1].t !== "flat") { runs[m - 1].b = runs[m + 1].b; runs.splice(m, 2); m--; } }
    return runs.map(function (r) { var len = d[r.b] - d[r.a], net = es[r.b] - es[r.a]; return { t: r.t, from: d[r.a], to: d[r.b], len: len, net: net, grade: net / len * 100 }; });
  }

  // ── 상태 ─────────────────────────────────────────────────
  var MAPON = false, C = null, P, PATH, TOT, SEG, XY, CUM, SC, LAT0, ZOOM = 0, pos = 0, lastDist = null, watch = null, lock = null, EMIN, EMAX;

  function elevAt(d) { for (var i = 1; i < P.length; i++) { if (P[i][0] >= d) { var a = P[i - 1], b = P[i], t = (d - a[0]) / (b[0] - a[0] || 1); return a[1] + (b[1] - a[1]) * t; } } return P[P.length - 1][1]; }
  function segAt(d) { for (var i = 0; i < SEG.length; i++) { if (d < SEG[i].to) return i; } return SEG.length - 1; }
  function xy(p) { return [(p[1] - PATH[0][1]) * 111320 * Math.cos(LAT0 * Math.PI / 180), (p[0] - LAT0) * 111320]; }
  function ptAt(d) { var t = d / SC; for (var i = 1; i < CUM.length; i++) { if (CUM[i] >= t) { var f = (t - CUM[i - 1]) / ((CUM[i] - CUM[i - 1]) || 1); return [XY[i - 1][0] + (XY[i][0] - XY[i - 1][0]) * f, XY[i - 1][1] + (XY[i][1] - XY[i - 1][1]) * f]; } } return XY[XY.length - 1]; }

  // 코스 선에서 가장 가까운 점을 찾는다. 직전 위치 근처를 우선해서, 같은 길을 두 번 지나는 코스에서 엉뚱한 쪽으로 튀지 않게 한다.
  function snap(lat, lon) {
    var p = xy([lat, lon]), best = { off: 1e18, dist: 0 }, near = { off: 1e18, dist: 0 };
    for (var i = 1; i < XY.length; i++) {
      var a = XY[i - 1], b = XY[i], dx = b[0] - a[0], dy = b[1] - a[1], L2 = dx * dx + dy * dy || 1,
        t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2)),
        off = Math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy)), dist = (CUM[i - 1] + t * Math.sqrt(L2)) * SC;
      if (off < best.off) best = { off: off, dist: dist };
      if (lastDist != null && dist >= lastDist - 150 && dist <= lastDist + 600 && off < near.off) near = { off: off, dist: dist };
    }
    return (lastDist != null && near.off <= Math.max(60, best.off + 30)) ? near : best;
  }

  // ── 그리기 ───────────────────────────────────────────────
  function drawChart() {
    var W = 360, H = 120, L = 8, R = 8, T = 8, B = 20;
    EMIN = 1e9; EMAX = -1e9; P.forEach(function (p) { EMIN = Math.min(EMIN, p[1]); EMAX = Math.max(EMAX, p[1]); });
    EMIN = Math.floor(EMIN / 10) * 10 - 10; EMAX = Math.ceil(EMAX / 10) * 10 + 10;
    var X = function (d) { return L + (W - L - R) * d / TOT; }, Y = function (e) { return T + (H - T - B) * (1 - (e - EMIN) / (EMAX - EMIN)); };
    var s = '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="코스 고도 단면. 오르막, 내리막, 평지를 색으로 구분">';
    SEG.forEach(function (sg) {
      var pts = P.filter(function (p) { return p[0] >= sg.from && p[0] <= sg.to; });
      if (pts.length < 2) return;
      var d = "M" + X(pts[0][0]) + "," + (H - B);
      pts.forEach(function (p) { d += " L" + X(p[0]).toFixed(1) + "," + Y(p[1]).toFixed(1); });
      d += " L" + X(pts[pts.length - 1][0]) + "," + (H - B) + " Z";
      s += '<path d="' + d + '" fill="var(--fd-' + sg.t + '-bg)" stroke="var(--fd-' + sg.t + ')" stroke-width="2" stroke-linejoin="round"/>';
    });
    s += '<line x1="' + L + '" x2="' + (W - R) + '" y1="' + (H - B) + '" y2="' + (H - B) + '" stroke="var(--line)"/>';
    var step = TOT > 30000 ? 5000 : TOT > 12000 ? 2000 : 1000;
    for (var k = 0; k <= TOT; k += step) s += '<text class="fd-ax" x="' + X(k) + '" y="' + (H - 5) + '" text-anchor="' + (k === 0 ? "start" : "middle") + '">' + (k / 1000) + "km</text>";
    s += '<line id="fdMkl" y1="' + T + '" y2="' + (H - B) + '" stroke="var(--ink)" stroke-width="2.5"/><circle id="fdMkc" r="5" fill="var(--ink)" stroke="var(--surface)" stroke-width="2"/></svg>';
    $("fdChart").innerHTML = s;
    drawChart.X = X; drawChart.Y = Y;
  }

  var ZW = [0, 1000, 250]; // 0=전체, 그 외 내 위치 앞뒤 몇 m를 보는지
  function drawMini(acc) {
    var W = 360, H = 190, pad = 14, me = ptAt(pos), s = '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="코스를 위에서 본 모양과 내 위치">', tx, ty, sc, cx, cy;
    if (!ZW[ZOOM]) {
      var xs = XY.map(function (p) { return p[0]; }), ys = XY.map(function (p) { return p[1]; }), x0 = Math.min.apply(0, xs), x1 = Math.max.apply(0, xs), y0 = Math.min.apply(0, ys), y1 = Math.max.apply(0, ys);
      sc = Math.min((W - 2 * pad) / ((x1 - x0) || 1), (H - 2 * pad) / ((y1 - y0) || 1));
      var ox = (W - (x1 - x0) * sc) / 2, oy = (H - (y1 - y0) * sc) / 2;
      tx = function (p) { return ox + (p[0] - x0) * sc; }; ty = function (p) { return H - (oy + (p[1] - y0) * sc); };
    } else {
      sc = (W / 2 - pad) / ZW[ZOOM];
      tx = function (p) { return W / 2 + (p[0] - me[0]) * sc; }; ty = function (p) { return H / 2 - (p[1] - me[1]) * sc; };
    }
    if (MAPON) s += tiles(tx, ty, sc, W, H);
    var d = ""; XY.forEach(function (p, i) { d += (i ? " L" : "M") + tx(p).toFixed(1) + "," + ty(p).toFixed(1); });
    s += '<path d="' + d + '" fill="none" stroke="var(--fd-flat)" stroke-width="' + (ZOOM ? 6 : 4) + '" stroke-linecap="round" stroke-linejoin="round"/>';
    // 지나온 길은 진하게, 남은 길은 옅게
    var passed = ""; XY.forEach(function (p, i) { if (CUM[i] * SC <= pos) passed += (passed ? " L" : "M") + tx(p).toFixed(1) + "," + ty(p).toFixed(1); });
    if (passed) { var q = tx(me).toFixed(1) + "," + ty(me).toFixed(1); s += '<path d="' + passed + " L" + q + '" fill="none" stroke="var(--ink)" stroke-width="' + (ZOOM ? 6 : 4) + '" stroke-linecap="round" stroke-linejoin="round"/>'; }
    var a = XY[0], b = XY[XY.length - 1];
    s += '<circle cx="' + tx(a) + '" cy="' + ty(a) + '" r="6" fill="var(--surface)" stroke="var(--ink)" stroke-width="2.5"/><text class="fd-ax" x="' + (tx(a) + 9) + '" y="' + (ty(a) + 4) + '" style="font-size:12px;fill:var(--ink)">출발</text>';
    s += '<circle cx="' + tx(b) + '" cy="' + ty(b) + '" r="6" fill="var(--ink)"/><text class="fd-ax" x="' + (tx(b) + 9) + '" y="' + (ty(b) + 4) + '" style="font-size:12px;fill:var(--ink)">도착</text>';
    if (acc) s += '<circle cx="' + tx(me) + '" cy="' + ty(me) + '" r="' + Math.max(8, Math.min(70, acc * sc)) + '" fill="var(--fd-down)" opacity=".18"/>';
    s += '<circle cx="' + tx(me) + '" cy="' + ty(me) + '" r="8" fill="var(--fd-up)" stroke="var(--surface)" stroke-width="3"/>';
    if (ZOOM) { var bar = ZOOM === 1 ? 500 : 100; s += '<line x1="' + pad + '" x2="' + (pad + bar * sc) + '" y1="' + (H - 12) + '" y2="' + (H - 12) + '" stroke="var(--ink)" stroke-width="3"/><text class="fd-ax" x="' + pad + '" y="' + (H - 18) + '" style="font-size:11px;fill:var(--ink)">' + bar + "m</text>"; }
    $("fdMini").innerHTML = s + "</svg>";
  }

  // 배경 지도: 켠 뒤에만 OpenStreetMap 타일 이미지를 요청한다. 코스 선을 그리는 좌표계(미터)와 타일 모서리를 같은 식으로 맞춘다.
  function tiles(tx, ty, sc, W, H) {
    var lat0 = LAT0, lon0 = PATH[0][1];
    function inv(x, y) { return [lat0 + y / 111320, lon0 + x / (111320 * Math.cos(lat0 * Math.PI / 180))]; }
    // 화면 모서리 → 지도 좌표
    var mx0, mx1, my0, my1;
    if (ZW[ZOOM]) { var me = ptAt(pos); mx0 = me[0] - (W / 2) / sc; mx1 = me[0] + (W / 2) / sc; my0 = me[1] - (H / 2) / sc; my1 = me[1] + (H / 2) / sc; }
    else { mx0 = (0 - tx([0, 0]) ) / sc; mx1 = (W - tx([0, 0])) / sc; my0 = (ty([0, 0]) - H) / sc; my1 = ty([0, 0]) / sc; }
    var a = inv(mx0, my0), b = inv(mx1, my1);
    // 화면에 타일이 9장 안팎이 되도록 줌을 고른다
    var z = 17; while (z > 8) { var n = Math.pow(2, z), tw = (b[1] - a[1]) / 360 * n; if (tw <= 3.2) break; z--; }
    var N = Math.pow(2, z);
    function tX(lon) { return (lon + 180) / 360 * N; }
    function tY(lat) { var r = lat * Math.PI / 180; return (1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2 * N; }
    function lon(x) { return x / N * 360 - 180; }
    function lat(y) { var n2 = Math.PI - 2 * Math.PI * y / N; return 180 / Math.PI * Math.atan(0.5 * (Math.exp(n2) - Math.exp(-n2))); }
    var x0 = Math.floor(tX(a[1])), x1 = Math.floor(tX(b[1])), y0 = Math.floor(tY(b[0])), y1 = Math.floor(tY(a[0])), out = "";
    if ((x1 - x0 + 1) * (y1 - y0 + 1) > 20) return "";
    for (var X = x0; X <= x1; X++) for (var Y = y0; Y <= y1; Y++) {
      var nw = xy([lat(Y), lon(X)]), se = xy([lat(Y + 1), lon(X + 1)]);
      out += '<image href="https://tile.openstreetmap.org/' + z + "/" + X + "/" + Y + '.png" x="' + tx(nw).toFixed(1) + '" y="' + ty(nw).toFixed(1) + '" width="' + (tx(se) - tx(nw)).toFixed(1) + '" height="' + (ty(se) - ty(nw)).toFixed(1) + '" opacity=".85"/>';
    }
    return out + '<rect x="0" y="' + (H - 15) + '" width="' + W + '" height="15" fill="#fff" opacity=".7"/><text class="fd-attr" x="' + (W - 6) + '" y="' + (H - 4) + '" text-anchor="end" style="fill:#333">© OpenStreetMap contributors</text>';
  }

  function paint(acc) {
    pos = Math.max(0, Math.min(TOT, pos));
    var i = segAt(pos), sg = SEG[i], rem = sg.to - pos, hero = $("fdHero");
    hero.setAttribute("data-t", sg.t);
    $("fdGlyph").textContent = GL[sg.t]; $("fdState").textContent = "지금 " + NAME[sg.t];
    $("fdNow").textContent = km(pos) + " 지점 · 전체의 " + Math.round(pos / TOT * 100) + "%";
    var e0 = elevAt(pos), e1 = elevAt(sg.to), rg = e1 - e0;
    $("fdBig").innerHTML = sg.t === "flat" ? mm(rem) + " <small>뒤에 지형이 바뀝니다</small>" : mm(rem) + " <small>더 " + (sg.t === "up" ? "오릅니다" : "내려갑니다") + "</small>";
    $("fdGain").textContent = sg.t === "flat" ? "-" : (rg >= 0 ? "+" : "") + Math.round(rg) + "m";
    $("fdGrade").textContent = sg.t === "flat" || rem < 20 ? "-" : ((rg / rem * 100 >= 0 ? "+" : "") + (rg / rem * 100).toFixed(1) + "%");
    $("fdElev").textContent = Math.round(e0) + "m";
    var nx = SEG[i + 1];
    $("fdNext").innerHTML = nx ? "다음 <b>" + NAME[nx.t] + " " + km(nx.len) + "</b>" + (nx.t === "flat" ? "" : " · " + (nx.net >= 0 ? "+" : "") + Math.round(nx.net) + "m · 평균 " + (nx.grade >= 0 ? "+" : "") + nx.grade.toFixed(1) + "%") + (nx.t !== "flat" && Math.abs(nx.grade) >= 10 ? ' · <b class="fd-nw">급경사</b>' : "") : "마지막 구간입니다. 도착까지 " + mm(TOT - pos);
    [].forEach.call(document.querySelectorAll("#fdSegs li"), function (li, k) { li.classList.toggle("cur", k === i); });
    $("fdPos").value = pos;
    var X = drawChart.X, Y = drawChart.Y;
    $("fdMkl").setAttribute("x1", X(pos)); $("fdMkl").setAttribute("x2", X(pos)); $("fdMkc").setAttribute("cx", X(pos)); $("fdMkc").setAttribute("cy", Y(e0));
    drawMini(acc);
  }

  function setConf(s, t) { var c = $("fdConf"); c.setAttribute("data-s", s); c.textContent = t; }

  // ── GPS ──────────────────────────────────────────────────
  function toggleGps() {
    var m = $("fdMsg"), btn = $("fdGps");
    if (watch !== null) { navigator.geolocation.clearWatch(watch); watch = null; btn.textContent = "GPS로 따라가기"; m.textContent = "GPS를 껐습니다."; if (lock) { try { lock.release(); } catch (e) {} lock = null; } return; }
    if (!navigator.geolocation) { m.textContent = "이 브라우저는 위치를 지원하지 않습니다. 슬라이더로 위치를 맞춰 주세요."; return; }
    m.textContent = "위치를 찾는 중입니다.";
    try {
      watch = navigator.geolocation.watchPosition(function (g) {
        var r = snap(g.coords.latitude, g.coords.longitude), acc = Math.round(g.coords.accuracy || 0);
        if (r.off > 100) { setConf("off", "코스에서 약 " + Math.round(r.off) + "m 벗어나 있습니다. 길을 다시 확인해 주세요. (GPS 오차 ±" + acc + "m)"); return; }
        pos = r.dist; lastDist = pos; paint(acc);
        if (acc <= 25 && r.off <= 30) setConf("ok", "코스 위에 있습니다. 코스에서 " + Math.round(r.off) + "m, GPS 오차 ±" + acc + "m");
        else setConf("warn", "위치가 대략 맞습니다. 코스에서 " + Math.round(r.off) + "m, GPS 오차 ±" + acc + "m. 갈림길에서는 표지와 함께 확인해 주세요.");
        m.textContent = "GPS로 따라가는 중";
      }, function (err) {
        watch = null; btn.textContent = "GPS로 따라가기";
        m.textContent = err && err.code === 1 ? "위치 권한이 꺼져 있습니다. 주소창 왼쪽 자물쇠(또는 aA)에서 위치를 허용하고 폰의 위치 서비스도 켜 주세요. 앱 안의 브라우저(카카오톡 등)에서는 막혀 있으니 크롬·사파리에서 열어야 합니다. 지금은 슬라이더로 움직일 수 있습니다." : "위치를 가져오지 못했습니다. 하늘이 트인 곳에서 다시 눌러 주세요.";
      }, { enableHighAccuracy: true, maximumAge: 2000, timeout: 20000 });
      btn.textContent = "GPS 끄기";
      if (navigator.wakeLock) navigator.wakeLock.request("screen").then(function (l) { lock = l; }).catch(function () {});
    } catch (e) { m.textContent = "위치를 쓸 수 없습니다. 슬라이더로 움직여 주세요."; }
  }
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible" && watch !== null && navigator.wakeLock) navigator.wakeLock.request("screen").then(function (l) { lock = l; }).catch(function () {});
  });


  // ── 내 GPX ───────────────────────────────────────────────
  // 파일은 이 브라우저 안에서만 읽고 localStorage에만 저장한다(서버 전송 없음).
  var STORE = "calrank.field.gpx.v1";
  function loadMine() { try { return JSON.parse(localStorage.getItem(STORE) || "[]"); } catch (e) { return []; } }
  function saveMine(list) { try { localStorage.setItem(STORE, JSON.stringify(list)); return true; } catch (e) { return false; } }
  function hav(a, b) { var R = 6371000, r = Math.PI / 180, dl = (b[0] - a[0]) * r, dn = (b[1] - a[1]) * r, x = Math.sin(dl / 2) * Math.sin(dl / 2) + Math.cos(a[0] * r) * Math.cos(b[0] * r) * Math.sin(dn / 2) * Math.sin(dn / 2); return 2 * R * Math.asin(Math.sqrt(x)); }

  function parseGpx(text, fname) {
    var doc = new DOMParser().parseFromString(text, "application/xml");
    if (doc.getElementsByTagName("parsererror").length) throw new Error("GPX 파일을 읽지 못했습니다. 파일이 깨졌거나 GPX 형식이 아닙니다.");
    var nodes = doc.getElementsByTagName("trkpt"); if (!nodes.length) nodes = doc.getElementsByTagName("rtept");
    if (nodes.length < 10) throw new Error("코스 좌표가 너무 적습니다. 경로(track)가 들어 있는 GPX가 필요합니다.");
    var pts = [], withEle = 0;
    for (var i = 0; i < nodes.length; i++) {
      var la = parseFloat(nodes[i].getAttribute("lat")), lo = parseFloat(nodes[i].getAttribute("lon")), ee = nodes[i].getElementsByTagName("ele")[0], ev = ee ? parseFloat(ee.textContent) : NaN;
      if (isNaN(la) || isNaN(lo)) continue;
      if (!isNaN(ev)) withEle++;
      pts.push([la, lo, ev]);
    }
    if (pts.length < 10 || withEle < pts.length * 0.8) throw new Error("고도 값이 없는 GPX입니다. 고도가 들어 있어야 오르막과 내리막을 나눌 수 있습니다.");
    // 고도가 빠진 점은 앞 값으로 채운다
    var lastE = null; pts.forEach(function (p) { if (isNaN(p[2])) p[2] = lastE == null ? 0 : lastE; lastE = p[2]; });
    var cum = [0]; for (var k = 1; k < pts.length; k++) cum.push(cum[k - 1] + hav(pts[k - 1], pts[k]));
    var total = cum[cum.length - 1];
    if (total < 500) throw new Error("코스가 500m보다 짧습니다.");
    // 50m 간격으로 다시 뽑는다
    var STEP = 50, out = [], path = [], j = 1;
    for (var d = 0; d < total; d += STEP) {
      while (j < cum.length - 1 && cum[j] < d) j++;
      var t = (d - cum[j - 1]) / ((cum[j] - cum[j - 1]) || 1), a = pts[j - 1], b = pts[j];
      out.push([d, a[2] + (b[2] - a[2]) * t]); path.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]);
    }
    out.push([total, pts[pts.length - 1][2]]); path.push([pts[pts.length - 1][0], pts[pts.length - 1][1]]);
    // GPS 고도는 흔들리므로 5점 이동평균으로 누른다
    var sm = out.map(function (p, i) { var s = 0, c = 0; for (var q = Math.max(0, i - 2); q <= Math.min(out.length - 1, i + 2); q++) { s += out[q][1]; c++; } return [Math.round(p[0]), Math.round(s / c * 10) / 10]; });
    var nm = doc.getElementsByTagName("name")[0];
    var name = ((nm && nm.textContent.trim()) || fname.replace(/\.(gpx|xml)$/i, "") || "내 코스").slice(0, 60);
    return { id: "gpx-" + Date.now().toString(36), name: name, region: "내 GPX", km: Math.round(total / 100) / 10, profile: sm, path: path.map(function (p) { return [Math.round(p[0] * 1e5) / 1e5, Math.round(p[1] * 1e5) / 1e5]; }), src: "내가 올린 GPX 파일(이 기기에만 저장)" };
  }

  function renderMine() {
    var ul = $("fdMine"); if (!ul) return; var list = loadMine();
    ul.innerHTML = list.length ? list.map(function (c) { return '<li class="fd-mine-row"><a href="field.html?c=' + encodeURIComponent(c.id) + '">' + esc(c.name) + "<span>내 GPX · " + c.km + 'km</span></a><button type="button" class="fd-del" data-del="' + esc(c.id) + '" aria-label="' + esc(c.name) + ' 삭제">삭제</button></li>'; }).join("") : "";
    [].forEach.call(ul.querySelectorAll("[data-del]"), function (b) { b.addEventListener("click", function () { saveMine(loadMine().filter(function (c) { return c.id !== b.getAttribute("data-del"); })); renderMine(); }); });
  }

  function wireUpload() {
    var f = $("fdFile"); if (!f) return; renderMine();
    f.addEventListener("change", function () {
      var file = f.files && f.files[0], m = $("fdUpMsg"); if (!file) return;
      if (file.size > 8 * 1024 * 1024) { m.textContent = "파일이 너무 큽니다(8MB 이하)."; return; }
      m.textContent = "파일을 읽는 중입니다.";
      var rd = new FileReader();
      rd.onload = function () {
        try {
          var c = parseGpx(String(rd.result), file.name), list = loadMine();
          list.unshift(c); list = list.slice(0, 6);
          if (!saveMine(list)) { m.textContent = "읽었지만 이 기기에 저장하지 못했습니다. 이번에만 볼 수 있습니다."; } else { m.textContent = ""; }
          history.replaceState(null, "", "field.html?c=" + encodeURIComponent(c.id)); open(c); renderMine();
        } catch (e) { m.textContent = e.message || "파일을 열지 못했습니다."; }
        f.value = "";
      };
      rd.onerror = function () { m.textContent = "파일을 읽지 못했습니다."; };
      rd.readAsText(file);
    });
  }

  // ── 코스 열기 ────────────────────────────────────────────
  function open(c) {
    C = c; P = c.profile; PATH = c.path; TOT = P[P.length - 1][0]; SEG = segments(P); LAT0 = PATH[0][0];
    XY = PATH.map(xy); CUM = [0];
    for (var q = 1; q < XY.length; q++) CUM.push(CUM[q - 1] + Math.hypot(XY[q][0] - XY[q - 1][0], XY[q][1] - XY[q - 1][1]));
    SC = TOT / CUM[CUM.length - 1];
    pos = 0; lastDist = null; ZOOM = 0;
    $("fdName").textContent = c.name; $("fdTotal").textContent = "전체 " + km(TOT);
    $("fdPos").max = TOT;
    $("fdSegs").innerHTML = SEG.map(function (sg, i) {
      return '<li data-t="' + sg.t + '"><span class="fd-chip">' + GL[sg.t] + " " + NAME[sg.t] + '</span><span class="fd-rng">' + km(sg.from) + " → " + km(sg.to) + ' <span class="fd-dt">(' + km(sg.len) + ')</span></span><span class="fd-dt">' +
        (sg.t === "flat" ? "" : (sg.net >= 0 ? "+" : "") + Math.round(sg.net) + "m · " + (sg.grade >= 0 ? "+" : "") + sg.grade.toFixed(1) + "%") + "</span></li>";
    }).join("");
    $("fdSrc").textContent = c.src ? "코스 자료: " + c.src + "." : "";
    $("fdPick").hidden = true; $("fdApp").hidden = false;
    setConf("manual", "위치를 직접 맞추는 중입니다. GPS를 켜면 코스 위 확인 상태가 여기에 표시됩니다.");
    drawChart(); paint();
    document.title = c.name + " 현장 보기 | 칼랭크 CALRANK";
  }

  function wire() {
    $("fdPos").addEventListener("input", function () { pos = +this.value; lastDist = null; paint(); });
    $("fdBack").addEventListener("click", function () { pos -= 100; lastDist = null; paint(); });
    $("fdFwd").addEventListener("click", function () { pos += 100; lastDist = null; paint(); });
    $("fdGps").addEventListener("click", toggleGps);
    [].forEach.call(document.querySelectorAll("[data-z]"), function (b) {
      b.addEventListener("click", function () {
        ZOOM = +b.getAttribute("data-z");
        [].forEach.call(document.querySelectorAll("[data-z]"), function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
        paint();
      });
    });
    var mb = $("fdMapBtn");
    if (mb) mb.addEventListener("click", function () {
      MAPON = !MAPON; mb.setAttribute("aria-pressed", MAPON ? "true" : "false"); mb.textContent = MAPON ? "배경 지도 끄기" : "배경 지도 켜기"; paint();
    });
    $("fdOther").addEventListener("click", function (e) { e.preventDefault(); if (watch !== null) toggleGps(); history.replaceState(null, "", "field.html"); $("fdApp").hidden = true; $("fdPick").hidden = false; });
  }

  function picker(index) {
    var q = $("fdQ"), ul = $("fdList");
    function show() {
      var t = q.value.trim().replace(/\s+/g, "").toLowerCase();
      var rows = index.filter(function (r) { return !t || (r[1] + r[2]).replace(/\s+/g, "").toLowerCase().indexOf(t) >= 0; }).slice(0, 60);
      ul.innerHTML = rows.length ? rows.map(function (r) { return '<li><a href="field.html?c=' + encodeURIComponent(r[0]) + '">' + esc(r[1]) + "<span>" + esc(r[2]) + " · " + r[3] + "km</span></a></li>"; }).join("") : '<li class="fd-small">찾는 코스가 없습니다. 코스 이름이나 지역으로 다시 찾아 보세요.</li>';
    }
    q.addEventListener("input", show); show();
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!$("fdApp")) return;
    wire();
    var id = (location.search.match(/[?&]c=([\w-]+)/) || [])[1];
    fetch("field/index.json").then(function (r) { return r.json(); }).then(picker).catch(function () { $("fdList").innerHTML = '<li class="fd-small">코스 목록을 불러오지 못했습니다. 잠시 뒤 다시 열어 주세요.</li>'; });
    wireUpload();
    if (id && id.indexOf("gpx-") === 0) { var mine = loadMine().filter(function (c) { return c.id === id; })[0]; if (mine) open(mine); else $("fdMsgTop").textContent = "이 기기에 저장된 GPX가 없습니다. 아래에서 다시 올려 주세요."; }
    else if (id) fetch("field/" + id + ".json").then(function (r) { if (!r.ok) throw 0; return r.json(); }).then(open).catch(function () { $("fdMsgTop").textContent = "이 코스의 자료를 불러오지 못했습니다. 아래에서 다른 코스를 골라 주세요."; });
  });
})();
