// 예상 기록 노트 — 대회 전에 적은 예측을 대회 뒤 실제 기록과 맞춰 본다.
//
// 칼랭크가 맞혔는지를 보여 주는 노트가 아니라, 내 예측이 얼마나 맞는지를 보여 준다.
// 예측은 두 가지로 적을 수 있다.
//   · 내 감으로: 기록 하나를 적는다.
//   · 카본화 효과 환산: 지금 신발로 낸 최근 기록을 넣으면, 연구 근거(gear-model.js)로
//     신었을 때 줄어드는 시간의 범위를 계산해 함께 저장한다. 대회 뒤에는 실제로
//     줄어든 시간이 그 범위 안이었는지를 본다.
// 저장은 이 기기 안에서만 한다(calrank-local.js). 필요한 스크립트:
// wma-standards.js, grade-model.js, gear-model.js, calrank-local.js
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var L = window.CalrankLocal, G = window.CalrankGrade;
  var KM = { "5km": 5, "10km": 10, "half": 21.0975, "full": 42.195 };
  var KM_LABEL = { "5km": "5km", "10km": "10km", "half": "하프", "full": "풀코스" };
  var CLAIMS = null;

  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function fmt(sec) { return G.formatTime(sec); }
  function gap(sec) {
    sec = Math.round(Math.abs(sec)); var m = Math.floor(sec / 60), s = sec % 60;
    return m ? m + "분" + (s ? " " + s + "초" : "") : s + "초";
  }

  function loadClaims() {
    if (CLAIMS) return Promise.resolve(CLAIMS);
    return fetch("data/gear_claims.json").then(function (r) { return r.json(); }).then(function (d) { CLAIMS = d; return d; })
      .catch(function () { CLAIMS = { claims: [] }; return CLAIMS; });
  }

  // 카본화 환산: 효과 구간이 없거나(근거 없음) 계산이 안 되면 null.
  function carbonRange(baseSec, km) {
    if (!window.calrankGear || !CLAIMS) return null;
    var claim = window.calrankGear.findClaim(CLAIMS, "carbon-plate");
    if (!claim) return null;
    var res = window.calrankGear.judge({ claim: claim, finishSec: baseSec, distanceKm: km });
    var e = res && res.effects && res.effects[0];
    if (!e || !e.hasEvidence || !e.cutSec) return null;
    var a = Math.abs(e.cutSec.lo), b = Math.abs(e.cutSec.hi), pt = Math.abs(e.cutSec.point);
    return { cutLo: Math.min(a, b), cutHi: Math.max(a, b), cutPoint: pt, grade: e.evidence.grade,
             ns: e.evidence.significant === false };
  }

  // ── 입력 ────────────────────────────────────────────────
  function syncBasis() {
    var carbon = $("lgBasis").value === "carbon";
    $("lgPredWrap").hidden = carbon;
    $("lgBaseWrap").hidden = !carbon;
    $("lgCarbonNote").hidden = !carbon;
  }

  function add() {
    var name = $("lgName").value.trim(), date = $("lgDate").value, dk = $("lgDist").value, km = KM[dk];
    var basis = $("lgBasis").value, msg = $("lgMsg");
    if (!name) { msg.textContent = "대회 이름을 적어 주세요."; return; }
    var p = { name: name, date: date || null, dist: dk, km: km, basis: basis };
    if (basis === "carbon") {
      var base = G.parseTime($("lgBase").value);
      if (!base) { msg.textContent = "지금 신발로 낸 기록을 1:02:30 처럼 적어 주세요."; return; }
      var r = carbonRange(base, km);
      if (!r) { msg.textContent = "이 속도 구간에는 카본화 효과를 계산할 연구 근거가 없어서 감으로 적는 쪽만 가능합니다."; return; }
      p.baseSec = base; p.cutLo = Math.round(r.cutLo); p.cutHi = Math.round(r.cutHi); p.cutPoint = Math.round(r.cutPoint);
      p.grade = r.grade; p.ns = r.ns;
      p.predSec = Math.round(base - r.cutPoint);
    } else {
      var t = G.parseTime($("lgPred").value);
      if (!t) { msg.textContent = "예측 기록을 1:02:30 처럼 적어 주세요."; return; }
      p.predSec = t;
    }
    L.addPrediction(p);
    msg.textContent = "저장했습니다. 대회가 끝나면 아래에서 실제 기록을 넣어 비교해 보세요.";
    $("lgName").value = ""; $("lgPred").value = ""; $("lgBase").value = "";
    render();
  }

  // ── 채점 ────────────────────────────────────────────────
  function score(p) {
    var err = p.actualSec - p.predSec;               // +면 예측보다 느렸다
    var out = { err: err, pct: err / p.predSec * 100 };
    if (p.basis === "carbon") {
      var real = p.baseSec - p.actualSec;            // 실제로 줄어든 시간
      out.real = real;
      out.inRange = real >= p.cutLo && real <= p.cutHi;
    }
    return out;
  }

  function itemHtml(p) {
    var head = '<p class="lg-name">' + esc(p.name) + '</p><p class="lg-line">' + (p.date ? esc(p.date) + " · " : "") + esc(KM_LABEL[p.dist]) +
      " · 예측 <b>" + fmt(p.predSec) + "</b>" + (p.basis === "carbon" ? " (카본화 환산, 근거 " + esc(p.grade) + ")" : " (내 감)") + "</p>";
    if (p.basis === "carbon") {
      head += '<p class="lg-line">지금 신발 기록 ' + fmt(p.baseSec) + " 기준, 줄어들 시간 " + (p.ns ? "0초" : gap(p.cutLo)) + " ~ " + gap(p.cutHi) + "</p>";
    }
    if (p.actualSec) {
      var s = score(p);
      var line = '<p class="lg-line">실제 <b>' + fmt(p.actualSec) + "</b> · 예측보다 <b>" + gap(s.err) + (s.err > 0 ? " 느렸습니다" : s.err < 0 ? " 빨랐습니다" : " 차이 없습니다") + "</b> (" + (s.pct >= 0 ? "+" : "") + s.pct.toFixed(1) + "%)</p>";
      if (p.basis === "carbon") {
        line += '<p class="lg-line">실제로 줄어든 시간 <b>' + (s.real >= 0 ? gap(s.real) : "늘어난 시간 " + gap(s.real)) + "</b> → 연구 범위 " + (s.inRange ? "<b>안</b>입니다." : "<b>밖</b>입니다. 컨디션, 코스, 날씨 같은 다른 요인이 더 컸을 수 있습니다.") + "</p>";
      }
      return '<div class="lg-item">' + head + line + '<p class="lg-line"><button type="button" class="tp-btn ghost" data-del="' + esc(p.id) + '">지우기</button></p></div>';
    }
    return '<div class="lg-item">' + head +
      '<div class="kit-row"><input type="text" inputmode="numeric" placeholder="실제 기록 1:02:30" data-act="' + esc(p.id) + '" aria-label="실제 기록">' +
      '<button type="button" class="tp-btn" data-settle="' + esc(p.id) + '">비교하기</button>' +
      '<button type="button" class="tp-btn ghost" data-del="' + esc(p.id) + '">지우기</button></div>' +
      '<p class="tp-small">기록증 사진이 있다면 <a href="cert.html">기록증으로 기록 읽기</a>에서 시간을 확인한 뒤 적어도 됩니다.</p></div>';
  }

  function summary(list) {
    var done = list.filter(function (p) { return p.actualSec; });
    var box = $("lgSum");
    if (!done.length) { box.hidden = true; return; }
    var errs = done.map(function (p) { return Math.abs(score(p).pct); });
    var mean = errs.reduce(function (a, b) { return a + b; }, 0) / errs.length;
    var car = done.filter(function (p) { return p.basis === "carbon"; });
    var hits = car.filter(function (p) { return score(p).inRange; }).length;
    box.hidden = false;
    box.innerHTML = '<div class="lg-sum"><div><b>' + done.length + '회</b><span>비교한 예측</span></div><div><b>' + mean.toFixed(1) +
      '%</b><span>평균 오차(절댓값)</span></div><div><b>' + (car.length ? hits + "/" + car.length : "—") + "</b><span>카본화 범위 안에 든 횟수</span></div></div>" +
      '<p class="tp-small" style="margin-top:8px">' + (done.length < 3 ? "세 번 이상 쌓이면 내 예측이 어느 쪽으로 치우치는지 보입니다." : "예측이 실제보다 빠른 쪽이 많은지 느린 쪽이 많은지 위 목록에서 부호를 보세요.") + "</p>";
  }

  function render() {
    var list = L.ledger().sort(function (a, b) { return (b.date || b.madeAt || "").localeCompare(a.date || a.madeAt || ""); });
    $("lgList").innerHTML = list.length ? list.map(itemHtml).join("") : '<p class="tp-p">아직 적어 둔 예측이 없습니다.</p>';
    summary(list);
    [].forEach.call($("lgList").querySelectorAll("[data-settle]"), function (b) {
      b.addEventListener("click", function () {
        var id = b.getAttribute("data-settle");
        var t = G.parseTime(document.querySelector('[data-act="' + id + '"]').value);
        if (!t) { alert("기록을 1:02:30 처럼 적어 주세요."); return; }
        L.settle(id, t); render();
      });
    });
    [].forEach.call($("lgList").querySelectorAll("[data-del]"), function (b) {
      b.addEventListener("click", function () { if (confirm("이 예측을 지울까요?")) { L.removePrediction(b.getAttribute("data-del")); render(); } });
    });
  }

  function datalist() {
    fetch("events.json").then(function (r) { return r.json(); }).then(function (ev) {
      var t = L.today(), names = [];
      (Array.isArray(ev) ? ev : []).forEach(function (e) { if (e.date >= t && names.length < 400) names.push(e.name); });
      $("lgNames").innerHTML = names.map(function (n) { return '<option value="' + esc(n) + '">'; }).join("");
    }).catch(function () {});
  }

  document.addEventListener("DOMContentLoaded", function () {
    loadClaims().then(function () {});
    $("lgBasis").addEventListener("change", syncBasis);
    $("lgAdd").addEventListener("click", add);
    syncBasis(); render(); datalist();
    $("lgStore").textContent = L.isPersistent()
      ? "이 기기의 브라우저 안에만 저장됩니다. 서버로 보내지 않습니다."
      : "지금 브라우저가 저장을 막고 있어서, 이 탭을 닫으면 사라집니다.";
  });
})();
