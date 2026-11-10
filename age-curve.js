// 내 등급의 나이 곡선 — 같은 기록을 유지한다고 가정하고, 나이별 연령등급을 보여 준다.
//
// 예측이 아니다. 나이가 들면 WMA 기준기록이 느려지므로 같은 기록의 연령등급은
// 올라가고, 같은 등급을 지키는 데 필요한 기록은 느려진다. 이 환산 한 가지만 한다.
// 개인이 나이 들면서 실제로 얼마나 느려지는지는 사람마다 크게 다르고, 여기서는
// 다루지 않는다. 그래서 화면에도 "환산"이라고만 적는다.
//
// 필요한 스크립트: wma-standards.js, grade-model.js, calrank-local.js
(function () {
  "use strict";
  var G = window.CalrankGrade;
  var $ = function (id) { return document.getElementById(id); };
  var KM = { "5km": 5, "10km": 10, "half": 21.0975, "full": 42.195 };
  var KM_LABEL = { 5: "5km", 10: "10km", 21.0975: "하프", 42.195: "풀코스" };
  var A_MIN = 20, A_MAX = 85;

  function tierBoundFor(pct) {
    for (var i = 0; i < G.TIER_BOUNDS.length; i++) if (pct >= G.TIER_BOUNDS[i][0]) return G.TIER_BOUNDS[i];
    return G.TIER_BOUNDS[G.TIER_BOUNDS.length - 1];
  }

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  function fmtGap(sec) {
    sec = Math.round(Math.abs(sec));
    var m = Math.floor(sec / 60), s = sec % 60;
    return m ? m + "분" + (s ? " " + s + "초" : "") : s + "초";
  }

  function read() {
    var g = $("acGender").value, km = KM[$("acDist").value];
    var sec = G.parseTime($("acTime").value);
    var age = parseInt($("acAge").value, 10);
    if (!sec || sec < 60 || !age || age < 15 || age > 95) return null;
    return { gender: g, km: km, sec: sec, age: age };
  }

  function series(inp) {
    var pts = [];
    for (var a = A_MIN; a <= A_MAX; a++) pts.push({ age: a, pct: G.ageGradePct(inp.sec, inp.km, a, inp.gender) });
    return pts;
  }

  function chart(inp, pts) {
    var W = 640, H = 300, L = 44, R = 96, T = 14, B = 34;
    var min = Math.min.apply(null, pts.map(function (p) { return p.pct; }));
    var max = Math.max.apply(null, pts.map(function (p) { return p.pct; }));
    var lo = Math.floor((min - 3) / 5) * 5, hi = Math.ceil((max + 3) / 5) * 5;
    var x = function (a) { return L + (a - A_MIN) / (A_MAX - A_MIN) * (W - L - R); };
    var y = function (v) { return T + (hi - v) / (hi - lo) * (H - T - B); };
    var grid = "", ticks = "";
    for (var v = lo; v <= hi; v += 5) {
      grid += '<line class="g" x1="' + L + '" x2="' + (W - R) + '" y1="' + y(v) + '" y2="' + y(v) + '"/>';
      ticks += '<text class="ac-lab" x="' + (L - 6) + '" y="' + (y(v) + 4) + '" text-anchor="end">' + v + "</text>";
    }
    for (var a = 20; a <= 80; a += 10) {
      ticks += '<text class="ac-lab" x="' + x(a) + '" y="' + (H - 12) + '" text-anchor="middle">' + a + "세</text>";
    }
    var tiers = "";
    G.TIER_BOUNDS.forEach(function (b) {
      if (b[0] > lo && b[0] < hi) {
        tiers += '<line class="ac-tier" x1="' + L + '" x2="' + (W - R) + '" y1="' + y(b[0]) + '" y2="' + y(b[0]) + '"/>' +
          '<text class="ac-labs" x="' + (W - R + 6) + '" y="' + (y(b[0]) + 4) + '">' + esc(b[1]) + "</text>";
      }
    });
    var d = pts.map(function (p, i) { return (i ? "L" : "M") + x(p.age).toFixed(1) + " " + y(p.pct).toFixed(1); }).join(" ");
    var cur = pts.filter(function (p) { return p.age === inp.age; })[0];
    var dot = cur ? '<circle class="ac-dot" cx="' + x(cur.age) + '" cy="' + y(cur.pct) + '" r="5"/>' : "";
    var svg = '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="' + esc(KM_LABEL[inp.km]) + " " + esc(G.formatTime(inp.sec)) +
      ' 기록을 유지할 때 나이별 연령등급 곡선. 나이가 들수록 올라갑니다. 아래 표에 같은 값이 있습니다.">' +
      grid + ticks + tiers + '<path class="ac-line" d="' + d + '"/>' + dot + '<g id="acHover"></g></svg>';
    return { svg: svg, x: x, y: y, W: W, H: H, L: L, R: R };
  }

  function wireHover(box, c, pts) {
    var svg = box.querySelector("svg"), hov = box.querySelector("#acHover");
    var tip = document.createElement("div"); tip.className = "ac-tip"; tip.hidden = true; box.appendChild(tip);
    function at(ev) {
      var r = svg.getBoundingClientRect();
      var px = (ev.clientX - r.left) / r.width * c.W;
      var a = Math.round(A_MIN + (px - c.L) / (c.W - c.L - c.R) * (A_MAX - A_MIN));
      a = Math.max(A_MIN, Math.min(A_MAX, a));
      var p = pts[a - A_MIN];
      var b = tierBoundFor(p.pct);
      hov.innerHTML = '<line class="ac-tier" x1="' + c.x(a) + '" x2="' + c.x(a) + '" y1="14" y2="266"/><circle class="ac-dot" cx="' + c.x(a) + '" cy="' + c.y(p.pct) + '" r="5"/>';
      tip.hidden = false; tip.textContent = a + "세 · " + p.pct.toFixed(1) + "% · " + b[1];
      var left = (c.x(a) / c.W) * r.width; tip.style.left = Math.min(left + 8, r.width - 150) + "px"; tip.style.top = "4px";
    }
    svg.addEventListener("pointermove", at);
    svg.addEventListener("pointerleave", function () { hov.innerHTML = ""; tip.hidden = true; });
  }

  function table(inp, pts) {
    var p0 = pts[inp.age - A_MIN];
    var b0 = tierBoundFor(p0.pct);
    var ages = [];
    for (var a = inp.age; a <= 80; a += (a === inp.age ? 5 - (inp.age % 5 || 5) || 5 : 5)) ages.push(a);
    if (ages.indexOf(80) < 0 && inp.age < 80) ages.push(80);
    var rows = ages.map(function (a) {
      var p = pts[a - A_MIN], b = tierBoundFor(p.pct);
      var hold = G.boundarySeconds(b0[0], inp.km, a, inp.gender);
      return '<tr class="' + (a === inp.age ? "cur" : "") + '"><td>' + a + "세" + (a === inp.age ? " (지금)" : "") + "</td><td>" + p.pct.toFixed(1) +
        "%</td><td>" + esc(b[1]) + "</td><td>" + (hold ? G.formatTime(hold) + " 이내" : "—") + "</td></tr>";
    }).join("");
    return '<div class="tp-table-wrap"><table class="tp-table"><thead><tr><th>나이</th><th>같은 기록의 연령등급</th><th>등급</th><th>지금 등급 \'' + esc(b0[1]) + '\'을 지키는 기록</th></tr></thead><tbody>' + rows + "</tbody></table></div>";
  }

  function summary(inp, pts) {
    var p0 = pts[inp.age - A_MIN], b0 = tierBoundFor(p0.pct);
    var t = inp.age + 15 <= A_MAX ? inp.age + 15 : A_MAX;
    var p1 = pts[t - A_MIN], b1 = tierBoundFor(p1.pct);
    var hold = G.boundarySeconds(b0[0], inp.km, t, inp.gender);
    var slack = hold - inp.sec;
    var lead = KM_LABEL[inp.km] + " " + G.formatTime(inp.sec) + ", " + inp.age + "세 기준 연령등급은 <b>" + p0.pct.toFixed(1) + "%</b>, <b>" + esc(b0[1]) + "</b>입니다. ";
    var mid = "같은 기록을 " + t + "세까지 유지한다고 하면 연령등급은 <b>" + p1.pct.toFixed(1) + "%</b>(" + esc(b1[1]) + ")가 됩니다. ";
    var tail = slack > 0
      ? "반대로 지금 등급을 " + t + "세에도 지키려면 " + G.formatTime(hold) + " 이내면 되고, 그러면 지금보다 <b>" + fmtGap(slack) + "</b> 늦어도 됩니다."
      : "지금 등급을 " + t + "세에도 지키려면 " + G.formatTime(hold) + " 이내여야 합니다.";
    return lead + mid + tail;
  }

  function run() {
    var inp = read(), out = $("acOut");
    if (!inp) { out.hidden = true; return; }
    var pts = series(inp), c = chart(inp, pts);
    $("acSummary").innerHTML = summary(inp, pts);
    var box = $("acChart"); box.innerHTML = c.svg; wireHover(box, c, pts);
    $("acTable").innerHTML = table(inp, pts);
    out.hidden = false;
  }

  function prefill() {
    var q = new URLSearchParams(location.search), last = null;
    try { var rs = window.CalrankLocal ? window.CalrankLocal.results() : []; last = rs[rs.length - 1] || null; } catch (e) {}
    var set = function (id, v) { if (v != null && v !== "") $(id).value = v; };
    var key = function (km) { return Object.keys(KM).filter(function (k) { return Math.abs(KM[k] - km) < 0.05; })[0]; };
    if (q.get("g")) set("acGender", q.get("g")); else if (last) set("acGender", last.gender);
    if (q.get("d")) set("acDist", q.get("d")); else if (last && key(last.km)) set("acDist", key(last.km));
    if (q.get("t")) set("acTime", q.get("t")); else if (last) set("acTime", G.formatTime(last.sec));
    if (q.get("age")) set("acAge", q.get("age")); else if (last) set("acAge", last.age);
  }

  document.addEventListener("DOMContentLoaded", function () {
    prefill();
    ["acGender", "acDist", "acTime", "acAge"].forEach(function (id) { $(id).addEventListener("input", run); });
    run();
  });
})();
