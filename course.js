// 코스 판정 — 거리와 오르내림으로 코스가 평지 몇 km에 해당하는지 환산하고, 내 평지 페이스로 걸리는 시간을 계산한다.
//
// 근거: Minetti AE, Moia C, Roi GS, Susta D, Ferretti G. Energy cost of walking and running at
// extreme uphill and downhill slopes. J Appl Physiol 93:1039–1046, 2002.
// 산악 러너 10명이 트레드밀 −45%~+45% 경사에서 달릴 때 쓴 에너지(Cr, J·kg⁻¹·m⁻¹)를 잰 연구다.
// 논문의 5차 다항식을 그대로 쓴다. 한계는 화면에도 적는다.
//   · 표본이 남성 엘리트 산악 러너 10명이다.
//   · 바위·뿌리·진흙 같은 노면과 날씨, 고도(공기), 피로는 들어 있지 않다.
//   · 가파른 구간에서 걷는 것은 반영하지 않고 달리는 비용으로 계산한다.
// 불러온 GPX 파일은 이 브라우저 안에서만 읽고 서버로 보내지 않는다.
(function (root) {
  "use strict";

  var LEVEL = 3.4;                 // 평지에서 달릴 때 비용 (논문 3.40)
  var LIM = 0.45;                  // 논문이 잰 경사 범위

  function cr(i) {
    if (i > LIM) i = LIM; if (i < -LIM) i = -LIM;
    return 155.4 * Math.pow(i, 5) - 30.4 * Math.pow(i, 4) - 43.3 * Math.pow(i, 3) + 46.3 * i * i + 19.5 * i + 3.6;
  }

  // 한 구간의 비용(평지 대비 배수). 내리막 이득을 빼면 내리막은 평지와 같다고 본다.
  function factor(i, downhillBenefit) {
    if (i < 0 && !downhillBenefit) return 1;
    return cr(i) / cr(0);          // 다항식의 평지 값(3.6)을 기준으로 맞춘다. 실측 평지 값은 3.40
  }

  // 구간 목록 [{d(m), g(경사 비율)}] → 지표
  function analyze(segs, opt) {
    opt = opt || {};
    var dist = 0, gain = 0, loss = 0, equiv = 0, maxG = 0, i, s;
    for (i = 0; i < segs.length; i++) {
      s = segs[i];
      dist += s.d;
      if (s.g > 0) gain += s.d * s.g; else loss += -s.d * s.g;
      equiv += s.d * factor(s.g, !!opt.downhillBenefit);
    }
    // 100m 창 최대 경사
    var acc = 0, up = 0, j = 0, win = [];
    for (i = 0; i < segs.length; i++) {
      win.push(segs[i]); acc += segs[i].d; up += segs[i].d * segs[i].g;
      while (acc - win[0].d >= 100) { acc -= win[0].d; up -= win[0].d * win[0].g; win.shift(); }
      if (acc >= 100 && up / acc > maxG) maxG = up / acc;
    }
    var out = { distM: dist, gainM: gain, lossM: loss, equivM: equiv, maxGrade: maxG,
      index: dist ? equiv / dist : 1 };
    if (opt.flatPaceSecPerKm) out.timeSec = equiv / 1000 * opt.flatPaceSecPerKm;
    return out;
  }

  // 수동 입력: 오르막·내리막이 각각 일정한 경사라고 가정해 구간을 만든다.
  function fromTotals(distKm, gainM, lossM, climbGrade) {
    var D = distKm * 1000, g = climbGrade || 0.12;
    var dUp = gainM / g, dDown = lossM / g, scale = 1;
    if (dUp + dDown > D) scale = D / (dUp + dDown);   // 합이 총거리를 넘으면 줄인다
    dUp *= scale; dDown *= scale;
    var segs = [];
    if (dUp > 0) segs.push({ d: dUp, g: gainM * scale / dUp });
    if (dDown > 0) segs.push({ d: dDown, g: -lossM * scale / dDown });
    var flat = D - dUp - dDown;
    if (flat > 0) segs.push({ d: flat, g: 0 });
    return segs;
  }

  // GPX 문자열 → 25m 간격 구간. 고도는 이동평균으로 다듬는다(GPS 고도 잡음이 오르막을 부풀리기 때문).
  function parseGpx(text) {
    var doc = new DOMParser().parseFromString(text, "application/xml");
    var pts = doc.getElementsByTagName("trkpt");
    if (!pts.length) pts = doc.getElementsByTagName("rtept");
    var P = [], k, e, el;
    for (k = 0; k < pts.length; k++) {
      el = pts[k].getElementsByTagName("ele")[0];
      e = el ? parseFloat(el.textContent) : NaN;
      P.push({ lat: parseFloat(pts[k].getAttribute("lat")), lon: parseFloat(pts[k].getAttribute("lon")), ele: e });
    }
    return P;
  }

  function hav(a, b) {
    var R = 6371000, r = Math.PI / 180;
    var dLat = (b.lat - a.lat) * r, dLon = (b.lon - a.lon) * r;
    var x = Math.sin(dLat / 2) * Math.sin(dLat / 2) + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return 2 * R * Math.asin(Math.sqrt(x));
  }

  function segsFromPoints(P) {
    var good = P.filter(function (p) { return isFinite(p.lat) && isFinite(p.lon) && isFinite(p.ele); });
    if (good.length < 10) return null;
    var cum = [0], i;
    for (i = 1; i < good.length; i++) cum.push(cum[i - 1] + hav(good[i - 1], good[i]));
    var total = cum[cum.length - 1], step = 25, n = Math.floor(total / step);
    if (n < 8) return null;
    var el = [], j = 0, t, f;
    for (i = 0; i <= n; i++) {
      t = i * step;
      while (j < cum.length - 2 && cum[j + 1] < t) j++;
      f = cum[j + 1] > cum[j] ? (t - cum[j]) / (cum[j + 1] - cum[j]) : 0;
      el.push(good[j].ele + (good[j + 1].ele - good[j].ele) * f);
    }
    var sm = el.map(function (_, idx) {                      // 앞뒤 2칸(약 100m) 이동평균
      var a = Math.max(0, idx - 2), b = Math.min(el.length - 1, idx + 2), s = 0, c = 0, q;
      for (q = a; q <= b; q++) { s += el[q]; c++; }
      return s / c;
    });
    var segs = [];
    for (i = 1; i < sm.length; i++) segs.push({ d: step, g: Math.max(-LIM, Math.min(LIM, (sm[i] - sm[i - 1]) / step)) });
    return { segs: segs, profile: sm.map(function (e, idx) { return { x: idx * step, y: e }; }) };
  }

  // 코스 부하 지수 구분. 연구가 정한 기준이 아니라 칼랭크가 나눈 구간이다.
  function band(index) {
    if (index < 1.15) return "평지에 가까움";
    if (index < 1.4) return "오르내림 있는 코스";
    if (index < 1.8) return "산악 코스";
    return "매우 힘든 산악 코스";
  }

  var api = { cr: cr, factor: factor, analyze: analyze, fromTotals: fromTotals, parseGpx: parseGpx, segsFromPoints: segsFromPoints, band: band, LEVEL: LEVEL };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CalrankCourse = api;

  // ── 화면 ────────────────────────────────────────────────
  if (typeof document === "undefined") return;
  var $ = function (id) { return document.getElementById(id); };
  var profile = null, segs = null, source = "예시 값";

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function fmtTime(sec) {
    sec = Math.round(sec); var h = Math.floor(sec / 3600), m = Math.floor(sec % 3600 / 60);
    return h ? h + "시간 " + (m < 10 ? "0" : "") + m + "분" : m + "분";
  }
  function parsePace(s) {
    var m = /^(\d{1,2}):([0-5]?\d)$/.exec(String(s).trim());
    return m ? parseInt(m[1], 10) * 60 + parseInt(m[2], 10) : null;
  }

  function drawProfile(pr) {
    var W = 640, H = 220, L = 70, R = 14, T = 14, B = 36;
    var xs = pr[pr.length - 1].x, mn = Infinity, mx = -Infinity, i;
    for (i = 0; i < pr.length; i++) { if (pr[i].y < mn) mn = pr[i].y; if (pr[i].y > mx) mx = pr[i].y; }
    var pad = Math.max(10, (mx - mn) * 0.1); mn -= pad; mx += pad;
    var X = function (x) { return L + x / xs * (W - L - R); };
    var Y = function (y) { return T + (1 - (y - mn) / (mx - mn)) * (H - T - B); };
    var d = "M" + X(pr[0].x).toFixed(1) + " " + Y(pr[0].y).toFixed(1);
    for (i = 1; i < pr.length; i++) d += "L" + X(pr[i].x).toFixed(1) + " " + Y(pr[i].y).toFixed(1);
    var area = d + "L" + X(xs).toFixed(1) + " " + (H - B) + "L" + L + " " + (H - B) + "Z";
    var g = "", yt = [mn + pad, (mn + mx) / 2, mx - pad];
    yt.forEach(function (v) {
      g += '<line x1="' + L + '" x2="' + (W - R) + '" y1="' + Y(v).toFixed(1) + '" y2="' + Y(v).toFixed(1) + '" stroke="var(--line)" stroke-width="1"/>' +
        '<text x="' + (L - 8) + '" y="' + (Y(v) + 6).toFixed(1) + '" text-anchor="end" font-size="19" fill="var(--ink-faint)">' + Math.round(v) + "m</text>";
    });
    var step = xs > 30000 ? 10000 : xs > 12000 ? 5000 : 2000, x;
    for (x = 0; x <= xs; x += step) g += '<text x="' + X(x).toFixed(1) + '" y="' + (H - 10) + '" text-anchor="middle" font-size="19" fill="var(--ink-faint)">' + (x / 1000) + "km</text>";
    return '<svg viewBox="0 0 ' + W + " " + H + '" width="100%" role="img" aria-label="코스 고도 단면">' + g +
      '<path d="' + area + '" fill="var(--tint-2)" stroke="none"/><path d="' + d + '" fill="none" stroke="var(--accent)" stroke-width="2"/></svg>';
  }

  function render() {
    var pace = parsePace($("cvPace").value);
    if (!pace) { $("cvMsg").textContent = "평지 페이스를 6:30 처럼 적어 주세요."; return; }
    $("cvMsg").textContent = "";
    var r = analyze(segs, { flatPaceSecPerKm: pace, downhillBenefit: $("cvDown").checked });
    var km = r.distM / 1000;
    $("cvOut").hidden = false;
    $("cvSource").textContent = source;
    $("cvIndex").textContent = r.index.toFixed(2);
    $("cvBand").textContent = band(r.index);
    $("cvTable").innerHTML = [
      ["거리", km.toFixed(1) + " km"],
      ["누적 상승 / 하강", Math.round(r.gainM) + " m / " + Math.round(r.lossM) + " m"],
      ["1km당 상승", (r.gainM / km).toFixed(0) + " m"],
      ["100m 구간 최대 경사", (r.maxGrade * 100).toFixed(0) + " %"],
      ["평지로 환산한 거리", (r.equivM / 1000).toFixed(1) + " km"],
      ["이 페이스로 걸리는 시간", fmtTime(r.timeSec)]
    ].map(function (x) { return "<tr><th>" + x[0] + "</th><td>" + x[1] + "</td></tr>"; }).join("");
    $("cvChart").innerHTML = profile ? drawProfile(profile) : "";
    $("cvChartWrap").hidden = !profile;
  }

  function manual() {
    var km = parseFloat($("cvDist").value), gn = parseFloat($("cvGain").value), ls = parseFloat($("cvLoss").value), g = parseFloat($("cvUpg").value);
    if (!(km > 0) || !(gn >= 0) || !(ls >= 0)) { $("cvMsg").textContent = "거리와 누적 상승, 누적 하강을 적어 주세요."; return; }
    segs = fromTotals(km, gn, ls, g); profile = null; source = "직접 입력한 값(오르막·내리막이 일정한 경사라고 가정)";
    render();
  }

  function onFile(f) {
    if (!f) return;
    var rd = new FileReader();
    rd.onload = function () {
      var res = segsFromPoints(parseGpx(String(rd.result)));
      if (!res) { $("cvMsg").textContent = "고도가 들어 있는 GPX 파일이 아니거나 점이 너무 적습니다."; return; }
      segs = res.segs; profile = res.profile; source = "불러온 GPX 파일 (이 브라우저 안에서만 읽었습니다)";
      render();
    };
    rd.readAsText(f);
  }

  document.addEventListener("DOMContentLoaded", function () {
    $("cvRun").addEventListener("click", manual);
    $("cvFile").addEventListener("change", function (e) { onFile(e.target.files[0]); });
    $("cvDown").addEventListener("change", function () { if (segs) render(); });
    $("cvPace").addEventListener("change", function () { if (segs) render(); });
    manual();                       // 예시 값으로 열린다
  });
})(typeof window !== "undefined" ? window : globalThis);
