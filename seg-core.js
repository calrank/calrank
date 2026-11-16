// 코스 계산 공용 — 구간 나누기(평지/오르막/내리막), 코스 위 위치 찾기, 일몰 시각.
// 쓰는 곳: field.js(현장 보기), map-tools.js(지도 전체화면). 계산은 모두 이 브라우저 안에서만 한다.
//
// 구간 기준: 100m 창의 평균 경사 3% 이상이고 500m 이상이면 오르막/내리막으로 본다.
// Garmin ClimbPro가 오르막으로 치는 최소 길이 500m, 최소 평균 경사 3%를 참고했다.
// 연구 결과가 아니라 읽기 편하게 정한 표시 기준이며 화면에도 그렇게 적는다.
(function () {
  "use strict";

  // P = [[누적거리 m, 고도 m], ...]
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

  // 코스 선(위경도 목록)을 미터 좌표로 바꿔 두고, 한 점이 코스의 몇 m 지점에 가장 가까운지 찾는다.
  // total 을 주면 코스 선의 길이를 그 값에 맞춰(고도 자료의 거리와 같은 눈금) 계산한다.
  function course(path, total) {
    var lat0 = path[0][0], lon0 = path[0][1], k = 111320, c = Math.cos(lat0 * Math.PI / 180);
    var XY = path.map(function (p) { return [(p[1] - lon0) * k * c, (p[0] - lat0) * k]; }), CUM = [0];
    for (var q = 1; q < XY.length; q++) CUM.push(CUM[q - 1] + Math.hypot(XY[q][0] - XY[q - 1][0], XY[q][1] - XY[q - 1][1]));
    var len = CUM[CUM.length - 1], SC = total ? total / len : 1, TOT = total || len;
    function xy(lat, lon) { return [(lon - lon0) * k * c, (lat - lat0) * k]; }
    // 직전 위치 근처를 우선해서, 같은 길을 두 번 지나는 코스에서 엉뚱한 쪽으로 튀지 않게 한다.
    function snap(lat, lon, lastDist) {
      var p = xy(lat, lon), best = { off: 1e18, dist: 0 }, near = { off: 1e18, dist: 0 };
      for (var i = 1; i < XY.length; i++) {
        var a = XY[i - 1], b = XY[i], dx = b[0] - a[0], dy = b[1] - a[1], L2 = dx * dx + dy * dy || 1,
          t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2)),
          off = Math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy)), dist = (CUM[i - 1] + t * Math.sqrt(L2)) * SC;
        if (off < best.off) best = { off: off, dist: dist };
        if (lastDist != null && dist >= lastDist - 150 && dist <= lastDist + 600 && off < near.off) near = { off: off, dist: dist };
      }
      return (lastDist != null && near.off <= Math.max(60, best.off + 30)) ? near : best;
    }
    // 코스의 d m 지점의 위경도
    function at(d) {
      var t = d / SC;
      for (var i = 1; i < CUM.length; i++) if (CUM[i] >= t) { var f = (t - CUM[i - 1]) / ((CUM[i] - CUM[i - 1]) || 1); return [path[i - 1][0] + (path[i][0] - path[i - 1][0]) * f, path[i - 1][1] + (path[i][1] - path[i - 1][1]) * f]; }
      return path[path.length - 1];
    }
    // from~to m 구간의 선
    function slice(from, to) {
      var out = [at(from)];
      for (var i = 1; i < CUM.length; i++) { var d = CUM[i] * SC; if (d > from && d < to) out.push(path[i]); }
      out.push(at(to)); return out;
    }
    return { total: TOT, snap: snap, at: at, slice: slice };
  }

  // 일출·일몰. Wikipedia 'Sunrise equation'의 근사식(수 분 이내). 위도·경도는 도 단위(동경·북위 +).
  function sun(lat, lon, date) {
    var r = Math.PI / 180, J1970 = 2440588, J2000 = 2451545;
    var jd = date.valueOf() / 86400000 - 0.5 + J1970, n = Math.ceil(jd - J2000 + 0.0008), Js = n - lon / 360;
    var M = (357.5291 + 0.98560028 * Js) % 360, C = 1.9148 * Math.sin(M * r) + 0.02 * Math.sin(2 * M * r) + 0.0003 * Math.sin(3 * M * r);
    var lam = (M + C + 180 + 102.9372) % 360, Jt = J2000 + Js + 0.0053 * Math.sin(M * r) - 0.0069 * Math.sin(2 * lam * r);
    var dec = Math.asin(Math.sin(lam * r) * Math.sin(23.4397 * r)), cw = (Math.sin(-0.833 * r) - Math.sin(lat * r) * Math.sin(dec)) / (Math.cos(lat * r) * Math.cos(dec));
    if (cw < -1 || cw > 1) return null;
    var w = Math.acos(cw) / r / 360;
    function toDate(J) { return new Date((J - J1970 + 0.5) * 86400000); }
    return { rise: toDate(Jt - w), set: toDate(Jt + w) };
  }

  window.CalrankSeg = { segments: segments, course: course, sun: sun };
})();
