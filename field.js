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
  var C = null, P, PATH, TOT, SEG, XY, CUM, SC, LAT0, ZOOM = 0, pos = 0, lastDist = null, watch = null, lock = null, EMIN, EMAX;

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
        m.textContent = err && err.code === 1 ? "위치 권한이 꺼져 있습니다. 브라우저 설정에서 허용하면 따라갑니다. 지금은 슬라이더로 움직일 수 있습니다." : "위치를 가져오지 못했습니다. 하늘이 트인 곳에서 다시 눌러 주세요.";
      }, { enableHighAccuracy: true, maximumAge: 2000, timeout: 20000 });
      btn.textContent = "GPS 끄기";
      if (navigator.wakeLock) navigator.wakeLock.request("screen").then(function (l) { lock = l; }).catch(function () {});
    } catch (e) { m.textContent = "위치를 쓸 수 없습니다. 슬라이더로 움직여 주세요."; }
  }
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible" && watch !== null && navigator.wakeLock) navigator.wakeLock.request("screen").then(function (l) { lock = l; }).catch(function () {});
  });

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
    if (id) fetch("field/" + id + ".json").then(function (r) { if (!r.ok) throw 0; return r.json(); }).then(open).catch(function () { $("fdMsgTop").textContent = "이 코스의 자료를 불러오지 못했습니다. 아래에서 다른 코스를 골라 주세요."; });
  });
})();
