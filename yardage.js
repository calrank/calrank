// 대회 코스 야디지북 — 주최측 공식 GPX를 올리면 구간(km)마다 오르막·내리막·경사와 보정 페이스를 보여 준다.
// 파일은 이 브라우저 안에서만 읽고 서버로 보내지 않는다. 계산은 course.js(Minetti 2002)를 쓴다.
(function () {
  "use strict";
  var C = window.CalrankCourse, $ = function (id) { return document.getElementById(id); };
  if (!C || !$("ydFile")) return;
  var res = null;

  function fmt(sec) {
    sec = Math.round(sec);
    var h = Math.floor(sec / 3600), m = Math.floor(sec % 3600 / 60), s = sec % 60, p = function (n) { return n < 10 ? "0" + n : "" + n; };
    return h ? h + ":" + p(m) + ":" + p(s) : m + ":" + p(s);
  }
  function parseTime(t) {
    var a = String(t).trim().replace(/시간|시|분/g, ":").replace(/초/g, "").replace(/[.,;\s]+/g, ":").replace(/^:+|:+$/g, "").split(":").map(Number);
    if (a.some(isNaN) || a.length < 2 || a.length > 3) return 0;
    return a.length === 3 ? a[0] * 3600 + a[1] * 60 + a[2] : a[0] * 60 + a[1];
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  // 오르막 덩어리: 100m 이동평균 고도에서 내려가는 폭이 8m 안이면 같은 오르막으로 묶는다.
  function climbs(profile, scale) {
    var out = [], i = 0, n = profile.length;
    while (i < n - 1) {
      var lo = i, hi = i, peak = profile[i].y, j = i + 1;
      while (j < n) {
        if (profile[j].y > peak) { peak = profile[j].y; hi = j; }
        else if (peak - profile[j].y > 8) break;
        j++;
      }
      var gain = profile[hi].y - profile[lo].y, len = (profile[hi].x - profile[lo].x) * scale;
      if (gain >= 15 && len > 0 && gain / len >= 0.015) out.push({ from: profile[lo].x * scale / 1000, to: profile[hi].x * scale / 1000, gain: gain, grade: gain / len });
      i = Math.max(hi, i + 1);
      if (hi === lo) i = lo + 1;
    }
    return out.sort(function (a, b) { return b.gain - a.gain; }).slice(0, 5);
  }

  function render() {
    if (!res) return;
    var target = parseTime($("ydTime").value);
    if (!target) { $("ydMsg").textContent = "목표 기록을 3:30:00 처럼 적어 주세요."; return; }
    var official = parseFloat($("ydDist").value) * 1000, fileM = res.raw.distM;
    var scale = official > 0 ? official / fileM : 1;
    var unit = parseInt($("ydUnit").value, 10) * 1000;
    $("ydMsg").textContent = "";
    var segs = res.segs.map(function (s) { return { d: s.d * scale, g: s.g }; });
    var eq = 0, k; segs.forEach(function (s) { eq += s.d * C.factor(s.g, false); });
    var p0 = target / (eq / 1000);                           // 평지에서 같은 노력의 페이스(초/km)
    var rows = [], acc = 0, cur = null, cum = 0;
    segs.forEach(function (s) {
      var rem = s.d, g = s.g;
      while (rem > 1e-6) {
        if (!cur) cur = { from: acc, d: 0, up: 0, dn: 0, eq: 0 };
        var take = Math.min(rem, unit - cur.d);
        cur.d += take; if (g > 0) cur.up += take * g; else cur.dn -= take * g; cur.eq += take * C.factor(g, false);
        rem -= take; acc += take;
        if (cur.d >= unit - 1e-6) { rows.push(cur); cur = null; }
      }
    });
    if (cur && cur.d > 50) rows.push(cur);
    var t = 0, html = "";
    rows.forEach(function (r, i) {
      var sec = r.eq / 1000 * p0, pace = sec / (r.d / 1000); t += sec;
      var avg = (r.up - r.dn) / r.d * 100, cls = avg > 1.5 ? "yd-up" : avg < -1.5 ? "yd-dn" : "";
      var to = (r.from + r.d) / 1000;
      html += '<tr class="' + cls + '"><th>' + (r.from / 1000).toFixed(r.from % 1000 ? 1 : 0).replace(/\.0$/, "") + "–" + (Math.abs(to - Math.round(to)) < 0.01 ? Math.round(to) : to.toFixed(1)) + "</th><td>+" + Math.round(r.up) + "/−" + Math.round(r.dn) + "</td><td>" +
        (avg > 0 ? "+" : "") + avg.toFixed(1) + "%</td><td>" + fmt(pace) + "</td><td>" + fmt(t) + "</td></tr>";
    });
    $("ydBody").innerHTML = html;
    var cl = climbs(res.profile, scale);
    $("ydClimbs").innerHTML = cl.length ? cl.map(function (c) {
      return "<li>" + c.from.toFixed(1) + "–" + c.to.toFixed(1) + "km 구간, 오르막 약 " + Math.round(c.gain) + "m (평균 " + (c.grade * 100).toFixed(1) + "%)</li>";
    }).join("") : "<li>눈에 띄는 오르막이 없습니다.</li>";
    var r2 = C.analyze(segs, { flatPaceSecPerKm: p0 });
    $("ydSum").textContent = "총 오르막 " + Math.round(r2.gainM) + "m, 내리막 " + Math.round(r2.lossM) + "m. 평지 기준 페이스 " + fmt(p0) + "/km에 해당하는 노력으로 달리는 계획입니다.";
    $("ydNote").textContent = Math.abs(scale - 1) > 0.002 ? "파일의 거리(" + (fileM / 1000).toFixed(2) + "km)를 공식 거리 " + (official / 1000).toFixed(3) + "km에 맞춰 늘이고 줄였습니다." : "";
    $("ydOut").hidden = false;
  }

  function onFile(f) {
    if (!f) return;
    var rd = new FileReader();
    rd.onload = function () {
      var r = C.segsFromPoints(C.parseGpx(String(rd.result)));
      if (!r) { $("ydMsg").textContent = "고도가 들어 있는 GPX 파일이 아니거나 점이 너무 적습니다."; return; }
      res = r;
      var d = r.raw.distM / 1000, pick = [[42.195, "풀"], [21.0975, "하프"], [10, "10"], [5, "5"]].filter(function (x) { return Math.abs(d - x[0]) / x[0] < 0.04; })[0];
      if (pick) $("ydDist").value = String(pick[0]);
      render();
    };
    rd.readAsText(f);
  }
  document.addEventListener("DOMContentLoaded", function () {
    $("ydFile").addEventListener("change", function (e) { onFile(e.target.files[0]); });
    ["ydTime", "ydDist", "ydUnit"].forEach(function (id) { $(id).addEventListener("change", render); });
  });
})();
