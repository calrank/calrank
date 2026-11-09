// 기어 판정 화면. 축이 둘이라 화면도 셋이다.
//
//   ?        → 허브. 종목 × 두 축 교차표.
//   ?r=<id>  → 규정 판정. 내 수치가 연맹 규정을 통과하는지.
//   ?c=<id>  → 효과 판정. 내 조건에서 그 장비가 얼마나 작동하는지.
//
// 계산은 gear-rules.js 와 gear-model.js 가 한다. 여기는 읽을 수 있게
// 늘어놓는 일만 한다.
//
// 화면에서 지키는 것.
//  · 근거 등급을 숫자 옆에서 떼지 않는다.
//  · 유의하지 않은 근거는 점추정을 크게 쓰지 않는다. "0 ~ X" 로 적는다.
//  · 규정은 통과·위반으로 단정하되, 언제 기준인지와 원문 링크를 함께 낸다.
//    규정은 거의 매년 바뀌고, 옛 숫자로 장비를 사면 그게 손해다.
//  · 근거도 규정도 없으면 빈칸으로 둔다. 옆 칸 숫자를 끌어오지 않는다.
(function () {
  "use strict";

  var CLAIMS = null, RULES = null, CLAIM = null, RULE = null;

  var GRADE_TEXT = {
    A: "메타분석 또는 복수의 무작위 대조 연구",
    B: "동료심사를 거친 단일 연구",
    C: "소규모 연구·학회 초록·관찰 연구",
    D: "제조사 자료 또는 검증되지 않은 주장"
  };

  var VERDICT = {
    pass:      { word: "통과",            cls: "ok" },
    fail:      { word: "위반",            cls: "no" },
    partial:   { word: "종목에 따라 갈린다", cls: "mix" },
    unknown:   { word: "확인 필요",        cls: "un" },
    forbidden: { word: "착용 금지",        cls: "no" },
    mandatory: { word: "착용 의무",        cls: "mix" },
    optional:  { word: "착용 선택",        cls: "ok" }
  };

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function num(v) {
    if (!isFinite(v)) return "";
    return (Math.round(v * 100) / 100).toLocaleString("ko-KR");
  }
  function clock(sec) {
    sec = Math.abs(Math.round(sec));
    var h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
    if (h) return h + ":" + String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
    return m + ":" + String(s).padStart(2, "0");
  }
  function minSec(sec) {
    sec = Math.abs(Math.round(sec));
    var m = Math.floor(sec / 60), s = sec % 60;
    if (!m) return s + "초";
    return s ? m + "분 " + s + "초" : m + "분";
  }
  function parseTime(text) {
    var p = String(text || "").trim().split(":").map(Number);
    if (!p.length || p.some(function (n) { return !isFinite(n) || n < 0; })) return 0;
    if (p.length === 3) return p[0] * 3600 + p[1] * 60 + p[2];
    if (p.length === 2) return p[0] * 60 + p[1];
    return 0;
  }

  // ── 허브: 종목 × 두 축 ──────────────────────────────────────────
  // 빈 칸을 숨기지 않는다. "사이클링 효과근거 0" 이 그대로 보여야
  // 다음에 뭘 채워야 하는지가 사이트에도, 나에게도 남는다.
  function buildHub() {
    var hub = $("gearHub");
    if (!hub || !CLAIMS || !RULES) return;
    var rows = window.calrankRules.coverage(CLAIMS, RULES);

    hub.innerHTML = rows.map(function (s) {
      var bodies = s.bodies.map(function (b) {
        var bd = RULES.bodies[b];
        return bd ? esc(bd.label) : "";
      }).filter(Boolean).join(" · ");

      var ruleList = s.rules.length
        ? s.rules.map(function (r) {
            return '<a class="gh-item" href="gear.html?r=' + encodeURIComponent(r.id) + '">' +
              '<b>' + esc(r.label) + "</b>" +
              (r.checkable ? '<span class="gh-tag">내 수치로 확인</span>' : "") +
              '<span class="gh-q">' + esc(r.question || "") + "</span></a>";
          }).join("")
        : '<p class="gh-empty">아직 없습니다.</p>';

      var claimList = s.claims.length
        ? s.claims.map(function (c) {
            return '<a class="gh-item" href="gear.html?c=' + encodeURIComponent(c.id) + '">' +
              "<b>" + esc(c.label) + "</b>" +
              '<span class="gh-q">' + esc(c.question || "") + "</span></a>";
          }).join("")
        : '<p class="gh-empty">연구 자료를 모으는 중입니다. 숫자가 설 때까지 비워 둡니다.</p>';

      return '<section class="gh-sport">' +
        '<h2>' + esc(s.label) +
        (bodies ? '<span class="gh-body">' + bodies + "</span>" : "") + "</h2>" +
        '<div class="gh-cols">' +
          '<div class="gh-col"><h3>규정 <small>세계 최고 대회에서 쓸 수 있나</small></h3>' +
            ruleList + "</div>" +
          '<div class="gh-col"><h3>효과 <small>연구가 뭐라고 하나</small></h3>' +
            claimList + "</div>" +
        "</div></section>";
    }).join("");
  }

  // ── 규정 판정 ───────────────────────────────────────────────────
  function renderRule() {
    var out = $("gearResult");
    if (!out || !RULE) return;
    var chk = RULE.check;
    if (!chk) { out.innerHTML = ""; return; }

    var vEl = $("grValue");
    var raw = vEl ? vEl.value : "";
    var value = parseFloat(String(raw).replace(/,/g, ""));
    var cEl = $("grChoice");
    var choice = cEl ? cEl.value : null;

    if (!isFinite(value)) {
      out.innerHTML = '<p class="gr-hint">내 장비 수치를 넣으면 통과·위반이 바로 나옵니다.</p>';
      return;
    }

    var res = window.calrankRules.judge({ rule: RULE, value: value, choice: choice });
    if (!res) { out.innerHTML = ""; return; }
    var v = VERDICT[res.verdict] || VERDICT.unknown;

    var html = '<div class="gr-verdict gr-' + v.cls + '">' +
      '<span class="gr-word">' + v.word + "</span>" +
      '<span class="gr-input">' + num(value) + esc(chk.unit) + "</span></div>";

    if (res.band) {
      var b = res.band;
      html += '<p class="gr-band">이 수온에서는 ' +
        (res.verdict === "forbidden" ? "<b>입을 수 없습니다</b>" :
         res.verdict === "mandatory" ? "<b>반드시 입어야 합니다</b>" :
                                       "<b>입어도 되고 안 입어도 됩니다</b>") + ". " +
        esc(res.option ? res.option.label : "") + " 기준으로 " +
        num(b.forbiddenAt) + "℃ 이상은 금지, " + num(b.mandatoryAt) + "℃ 이하는 의무입니다.</p>";
    } else if (res.results && res.results.length) {
      html += '<ul class="gr-rows">' + res.results.map(function (r) {
        var rv = VERDICT[r.result.verdict] || VERDICT.unknown;
        var tail = "";
        if (r.result.unlimited) {
          tail = '<span class="gr-free">상한 없음</span>';
        } else if (isFinite(r.result.limit)) {
          var lim = (r.result.compare === "max" ? "최대 " : "최소 ") +
                    num(r.result.limit) + esc(chk.unit);
          if (r.result.verdict === "pass") {
            tail = '<span class="gr-lim">' + lim +
              (r.result.margin === 0 ? ' · <em>한계치에 딱 걸립니다</em>'
               : r.result.margin > 0 ? " · 여유 " + num(r.result.margin) + esc(chk.unit) : "") +
              "</span>";
          } else {
            tail = '<span class="gr-lim">' + lim + " · " +
              num(Math.abs(r.result.margin)) + esc(chk.unit) + " 초과</span>";
          }
        }
        return '<li class="gr-' + rv.cls + '"><span class="gr-scope">' + esc(r.scope) + "</span>" +
          '<span class="gr-mark">' + rv.word + "</span>" + tail +
          (r.note ? '<span class="gr-rnote">' + esc(r.note) + "</span>" : "") + "</li>";
      }).join("") + "</ul>";
    }

    if (res.verdict === "partial") {
      html += '<p class="gr-mixnote">같은 장비가 어떤 종목에서는 되고 어떤 종목에서는 안 됩니다. ' +
        "두 종목을 다 뛰면 장비를 나눠야 합니다.</p>";
    }
    out.innerHTML = html;
  }

  function buildRuleForm() {
    var box = $("gearForm");
    if (!box || !RULE || !RULE.check) return;
    var chk = RULE.check;
    var rows = [];
    var extra = (chk.extra && chk.extra[0]) || null;
    if (extra && extra.options) {
      rows.push('<label for="grChoice">' + esc(extra.label) + "</label>" +
        '<select id="grChoice">' + extra.options.map(function (o) {
          return '<option value="' + esc(o.value) + '">' + esc(o.label) + "</option>";
        }).join("") + "</select>");
    }
    rows.push('<label for="grValue">' + esc(chk.label) +
      ' <span class="gf-unit">(' + esc(chk.unit) + ")</span></label>" +
      '<input id="grValue" type="number" inputmode="decimal"' +
      (chk.step ? ' step="' + esc(chk.step) + '"' : ' step="any"') +
      ' placeholder="' + esc(chk.placeholder || "") + '" autocomplete="off">');
    box.innerHTML = rows.join("");
    box.querySelectorAll("input,select").forEach(function (el) {
      el.addEventListener("input", renderRule);
      el.addEventListener("change", renderRule);
    });
  }

  function ruleMeta() {
    var box = $("gearMeta");
    if (!box || !RULE) return;
    var body = window.calrankRules.bodyOf(RULES, RULE);
    var html = "";
    if (RULE.surprise) html += '<p class="gm-surprise">' + esc(RULE.surprise) + "</p>";

    if (RULE.limits && RULE.limits.length) {
      html += '<h2>규정 전문의 숫자</h2><table class="gm-table"><tbody>' +
        RULE.limits.map(function (l) {
          var val = l.max === null ? "제한 없음"
                  : isFinite(l.max) ? "최대 " + num(l.max) + (RULE.check ? esc(RULE.check.unit) : "")
                  : isFinite(l.min) ? "최소 " + num(l.min) + (RULE.check ? esc(RULE.check.unit) : "")
                  : (l.min_text || "");
          return "<tr><th>" + esc(l.scope) + "</th><td>" + esc(val) +
            (l.note ? '<span class="gm-note">' + esc(l.note) + "</span>" : "") + "</td></tr>";
        }).join("") + "</tbody></table>";
    }
    if (RULE.measure_note) {
      html += '<h2>재는 방법과 덧붙는 조건</h2><p class="gm-measure">' +
        esc(RULE.measure_note) + "</p>";
    }
    if (body) {
      html += '<h2>이 규정을 쓰는 곳</h2><p class="gm-body"><b>' + esc(body.label) +
        "</b> (" + esc(body.label_ko) + ")<br>" + esc(body.governs) +
        (body.note ? '<span class="gm-note">' + esc(body.note) + "</span>" : "") + "</p>";
    }
    html += '<p class="gm-src">출처 · ' + esc(RULE.source) +
      (RULE.url ? ' <a href="' + esc(RULE.url) + '" target="_blank" rel="noopener">규정 원문 →</a>' : "") +
      '<span class="gm-note">장비 규정은 거의 매년 바뀝니다. 중요한 결정 전에는 원문을 한 번 더 확인해 주세요.</span></p>';
    box.innerHTML = html;
  }

  // ── 효과 판정 (근거 축) ─────────────────────────────────────────
  // 조건(속도·경사)에 따른 효과와 근거 등급을 그대로 옮긴 차트. 그림이 아니라
  // 자료라서, 숫자가 바뀌면 그림도 같이 바뀐다. 띠가 없는 구간은 근거가
  // 없다는 뜻이고, 그 빈칸이 보이는 게 이 차트의 요점이다.
  function evidenceChart(claim, effectId, myValue, unit) {
    var rows = window.calrankGear.evidenceMap(claim, effectId);
    if (!rows.length) return "";
    var xs = [];
    rows.forEach(function (r) {
      if (r.lo != null) xs.push(r.lo);
      if (r.hi != null) xs.push(r.hi);
    });
    if (isFinite(myValue)) xs.push(myValue);
    if (!xs.length) return "";
    var xMin = Math.min.apply(null, xs), xMax = Math.max.apply(null, xs);
    var pad = Math.max((xMax - xMin) * 0.18, 1.2);
    xMin = Math.max(0, xMin - pad); xMax = xMax + pad;

    var yMax = 0;
    rows.forEach(function (r) { if (r.range && r.range.hi > yMax) yMax = r.range.hi; });
    yMax = Math.max(yMax * 1.25, 1);

    var W = 680, H = 230, L = 46, R = 14, T = 16, B = 42;
    var pw = W - L - R, ph = H - T - B;
    function px(v) { return L + (v - xMin) / (xMax - xMin) * pw; }
    function py(v) { return T + ph - (v / yMax) * ph; }

    var parts = [];
    for (var g = 0; g <= 4; g++) {
      var val = yMax * g / 4, y = py(val);
      parts.push('<line class="gc-grid" x1="' + L + '" y1="' + y.toFixed(1) +
                 '" x2="' + (W - R) + '" y2="' + y.toFixed(1) + '"/>');
      parts.push('<text class="gc-ytick" x="' + (L - 7) + '" y="' + (y + 3.5).toFixed(1) +
                 '">' + val.toFixed(1) + '%</text>');
    }
    rows.forEach(function (r) {
      var lo = r.lo == null ? xMin : Math.max(r.lo, xMin);
      var hi = r.hi == null ? xMax : Math.min(r.hi, xMax);
      if (hi <= lo) return;
      var x0 = px(lo), x1 = px(hi);
      var yTop = py(r.range.hi), yBot = py(r.range.lo);
      var h = Math.max(yBot - yTop, 2.5);
      parts.push('<rect class="gc-band gc-' + r.grade + (r.significant ? "" : " gc-ns") +
                 '" x="' + x0.toFixed(1) + '" y="' + yTop.toFixed(1) +
                 '" width="' + (x1 - x0).toFixed(1) + '" height="' + h.toFixed(1) + '" rx="2"/>');
      parts.push('<text class="gc-badge" x="' + ((x0 + x1) / 2).toFixed(1) + '" y="' +
                 (yTop - 5).toFixed(1) + '">' + r.grade + (r.significant ? "" : " ·") + "</text>");
    });
    if (isFinite(myValue) && myValue >= xMin && myValue <= xMax) {
      var mx = px(myValue);
      parts.push('<line class="gc-me" x1="' + mx.toFixed(1) + '" y1="' + T +
                 '" x2="' + mx.toFixed(1) + '" y2="' + (T + ph) + '"/>');
      parts.push('<text class="gc-melabel" x="' + mx.toFixed(1) + '" y="' + (T + ph + 26) +
                 '">내 위치 ' + myValue.toFixed(1) + esc(unit) + "</text>");
    }
    parts.push('<text class="gc-xtick" x="' + L + '" y="' + (T + ph + 15) + '">' +
               xMin.toFixed(0) + esc(unit) + "</text>");
    parts.push('<text class="gc-xtick gc-end" x="' + (W - R) + '" y="' + (T + ph + 15) + '">' +
               xMax.toFixed(0) + esc(unit) + "</text>");

    return '<figure class="gc-wrap"><svg class="gc" viewBox="0 0 ' + W + " " + H +
           '" role="img" aria-label="조건에 따른 효과 크기와 근거 등급">' + parts.join("") + "</svg>" +
           '<figcaption class="gc-cap">띠의 높이가 보고된 효과 구간, 글자가 근거 등급입니다. ' +
           '· 표시는 통계적으로 유의하지 않았다는 뜻입니다. 띠가 없는 구간은 근거가 없습니다.' +
           "</figcaption></figure>";
  }

  function evidenceCard(ev) {
    if (!ev) return "";
    return '<div class="ge-src">' +
      '<span class="ge-grade ge-' + esc(ev.grade) + '">근거 ' + esc(ev.grade) + "</span>" +
      '<span class="ge-meta">' + esc(GRADE_TEXT[ev.grade] || "") +
      (ev.studies ? " · 연구 " + ev.studies + "편" : "") +
      (ev.n ? " · 참가자 " + ev.n + "명" : "") + "</span>" +
      (ev.note ? '<p class="ge-note">' + esc(ev.note) + "</p>" : "") +
      '<p class="ge-cite">' + esc(ev.source) +
      (ev.url ? ' <a href="' + esc(ev.url) + '" target="_blank" rel="noopener">원문 →</a>' : "") +
      "</p></div>";
  }

  function effectBlock(e, claim, condValue, unit) {
    // 연구가 아예 없는 구간. "0% 나빠짐"으로 적으면 "영향 없음"으로 읽히는데,
    // 사실은 모른다는 뜻이다. 둘을 갈라 놓는다. 비어 있다는 사실 자체가
    // 알려 줄 가치가 있는 정보이기도 하다.
    if (e.noData) {
      return '<section class="ge-eff ge-empty"><h3>' + esc(e.label) + "</h3>" +
        '<p class="ge-gap"><b>이 구간에는 연구가 없습니다.</b> 효과가 없다는 뜻이 아니라, ' +
        '얼마인지 아무도 재 보지 않았다는 뜻입니다.</p>' +
        (e.gap && e.gap.note ? '<p class="ge-note">' + esc(e.gap.note) + "</p>" : "") +
        "</section>";
    }
    if (!e.hasEvidence) {
      return '<section class="ge-eff ge-empty"><h3>' + esc(e.label) + "</h3>" +
        '<p class="ge-none">이 조건에서는 근거가 없습니다. 다른 구간의 숫자를 끌어다 쓰지 않았습니다.</p></section>';
    }

    // 모델로 계산한 효과. 보고된 구간이 아니라 식을 푼 결과라서 "0~X%" 꼴이
    // 아니다. 대신 넣은 값과 나온 값을 같이 보여 준다 — 식이 투명해야
    // 숫자를 믿을 수 있고, 기본값이 마음에 안 들면 바꿔 넣을 수 있다.
    if (e.computed && e.aero) {
      var a = e.aero, body = "";
      if (e.computed === "aero_share") {
        body = '<p class="ge-big"><strong>' + a.sharePct.toFixed(1) + "%</strong>가 " +
          "바람과 싸우는 데 쓰입니다</p>" +
          '<p class="ge-time">그 속도를 유지하는 데 드는 힘이 약 <b>' +
          Math.round(a.watts) + "W</b>입니다. 나머지는 구름저항과 베어링 몫이고요.</p>";
      } else if (e.computed === "cda_time") {
        body = '<p class="ge-big"><strong>' + minSec(a.cutSec) + "</strong> 빨라집니다</p>" +
          '<p class="ge-time">같은 힘으로 <b>' + a.speedBefore.toFixed(1) + " → " +
          a.speedAfter.toFixed(1) + "㎞/h</b> (" + a.gainPct.toFixed(2) + "%), " +
          "CdA " + a.cdaBefore.toFixed(3) + " → " + a.cdaAfter.toFixed(3) + "㎡ 기준입니다.</p>";
        if (e.wonPerSecond) {
          body += '<p class="ge-value">' + num(e.priceKrw) + "원이면 <b>1초에 " +
            num(Math.round(e.wonPerSecond)) + "원</b>입니다.</p>";
        }
      }
      return '<section class="ge-eff"><h3>' + esc(e.label) +
        (e.detail ? ' <span class="ge-detail">' + esc(e.detail) + "</span>" : "") + "</h3>" +
        body + evidenceCard(e.evidence) + "</section>";
    }
    var r = e.range, ns = e.evidence.significant === false;
    var dirWord = e.direction === "worse" ? "나빠집니다" : "좋아집니다";
    var headline = ns ? "0 ~ " + r.hi.toFixed(1) + "%"
                      : r.lo.toFixed(1) + " ~ " + r.hi.toFixed(1) + "%";

    var html = '<section class="ge-eff"><h3>' + esc(e.label) +
      (e.detail ? ' <span class="ge-detail">' + esc(e.detail) + "</span>" : "") + "</h3>" +
      '<p class="ge-big"><strong>' + headline + "</strong> " + dirWord +
      (ns ? ' <em class="ge-ns">통계적으로 유의하지 않음 — 효과가 없을 가능성을 배제하지 못합니다</em>' : "") +
      "</p>";

    if (e.cutSec) {
      var sign = e.cutSec.point >= 0 ? "빨라집니다" : "느려집니다";
      var lo = Math.abs(e.cutSec.lo), hi = Math.abs(e.cutSec.hi);
      html += '<p class="ge-time">기록으로 바꾸면 <strong>' +
        (ns ? "0초 ~ " + minSec(hi)
            : minSec(Math.min(lo, hi)) + " ~ " + minSec(Math.max(lo, hi))) +
        "</strong> " + sign + "</p>";
      if (e.grade) {
        html += '<p class="ge-grade-move">연령등급 ' + e.grade.before.toFixed(1) + "% → <b>" +
          e.grade.after.toFixed(1) + "%</b>, 등급은 " +
          (e.grade.moved ? esc(e.grade.tierBefore) + " → <b>" + esc(e.grade.tierAfter) + "</b>"
                         : "<b>" + esc(e.grade.tierBefore) + "</b> 그대로") + "입니다.</p>";
      }
      if (e.wonPerSecond) {
        html += '<p class="ge-value">' + num(e.priceKrw) + "원이면 <b>1초에 " +
          num(Math.round(e.wonPerSecond)) + "원</b>입니다.</p>";
      }
      if (claim.transfer_note) html += '<p class="ge-note">' + esc(claim.transfer_note) + "</p>";
    }
    return html + evidenceChart(claim, e.id, condValue, unit) + evidenceCard(e.evidence) + "</section>";
  }

  function unitFor(claim) {
    return claim.condition === "speed_kmh" ? "㎞/h"
         : claim.condition === "gradient_pct" ? "%"
         : claim.condition === "intensity_pct_vt2" ? "%" : "";
  }

  function renderClaim() {
    var out = $("gearResult");
    if (!out || !CLAIM) return;
    var input = { claim: CLAIM };
    var km = parseFloat($("geDistance") && $("geDistance").value);
    var sec = parseTime($("geTime") && $("geTime").value);
    var by = parseInt($("geBirthYear") && $("geBirthYear").value, 10);
    var price = parseInt(($("gePrice") && $("gePrice").value || "").replace(/\D/g, ""), 10);

    if (CLAIM.model) {
      var kmh = parseFloat($("geCond") && $("geCond").value);
      if (!isFinite(kmh) || kmh <= 0) {
        out.innerHTML = '<p class="gr-hint">평균 속도를 넣으면 판정이 나옵니다.</p>'; return;
      }
      input.speed_kmh = kmh;
      input.distanceKm = parseFloat($("geDistance") && $("geDistance").value);
      var cda = parseFloat($("geCda") && $("geCda").value);
      if (isFinite(cda) && cda > 0) input.cda = cda;
      var dl = parseFloat($("geCdaDelta") && $("geCdaDelta").value);
      if (isFinite(dl) && dl > 0) input.cdaDelta = dl;
      if (isFinite(price) && price > 0) input.priceKrw = price;
      var mres = window.calrankGear.judge(input);
      if (!mres) { out.innerHTML = '<p class="gr-hint">입력을 확인해 주세요.</p>'; return; }
      out.innerHTML = '<p class="ge-cond">평균 <b>' + kmh.toFixed(1) + "㎞/h</b>로 " +
        (isFinite(input.distanceKm) ? input.distanceKm + "km" : "") + " 달릴 때</p>" +
        mres.effects.map(function (e) {
          return effectBlock(e, CLAIM, kmh, "㎞/h");
        }).join("");
      return;
    }

    if (CLAIM.condition === "speed_kmh") {
      if (!sec) { out.innerHTML = '<p class="gr-hint">완주 기록을 넣으면 판정이 나옵니다.</p>'; return; }
      input.finishSec = sec; input.distanceKm = km;
    } else {
      input[CLAIM.condition] = parseFloat($("geCond") && $("geCond").value);
      if (sec) { input.finishSec = sec; input.distanceKm = km; }
    }
    if (isFinite(by)) input.age = new Date().getFullYear() - by;
    var g = $("geGender"); if (g) input.gender = g.value;
    if (isFinite(price) && price > 0) input.priceKrw = price;

    var res = window.calrankGear.judge(input);
    if (!res) { out.innerHTML = '<p class="gr-hint">입력을 확인해 주세요.</p>'; return; }

    var unit = unitFor(CLAIM), head = "";
    if (res.speedKmh && CLAIM.condition === "speed_kmh") {
      head = '<p class="ge-cond">내 페이스 <b>' + clock(res.paceSecPerKm) + "/km</b> · " +
             res.speedKmh.toFixed(1) + unit + "</p>";
    } else if (isFinite(res.conditionValue)) {
      head = '<p class="ge-cond">' + esc(CLAIM.condition_label) + " <b>" +
             res.conditionValue + unit + "</b></p>";
    }
    out.innerHTML = head + res.effects.map(function (e) {
      return effectBlock(e, CLAIM, res.conditionValue, unit);
    }).join("");
  }

  function buildClaimForm() {
    var box = $("gearForm");
    if (!box || !CLAIM) return;
    var speed = CLAIM.condition === "speed_kmh";
    var timed = CLAIM.effects.some(function (e) { return e.affects_time; });
    var modelled = !!CLAIM.model;
    var rows = [];

    // 모델로 푸는 주장은 기록이 아니라 평속과 거리를 받는다. 자전거는
    // 기록을 외우는 사람보다 평속을 외우는 사람이 훨씬 많다.
    if (modelled) {
      rows.push(
        '<label for="geCond">평균 속도 <span class="gf-unit">(㎞/h)</span></label>' +
        '<input id="geCond" type="number" step="0.5" min="5" max="70" value="30">',
        '<label for="geDistance">거리 <span class="gf-unit">(km)</span></label>' +
        '<input id="geDistance" type="number" step="5" min="1" max="500" value="40">',
        '<label for="geCda">내 CdA <span class="gf-unit">(㎡, 모르면 그대로)</span></label>' +
        '<input id="geCda" type="number" step="0.005" min="0.15" max="0.6" value="0.264">',
        '<label for="geCdaDelta">휠이 줄여 준다는 CdA <span class="gf-unit">(㎡)</span></label>' +
        '<input id="geCdaDelta" type="number" step="0.001" min="0.001" max="0.1" value="0.010">',
        '<label for="gePrice">가격 (원)</label>' +
        '<input id="gePrice" type="text" inputmode="numeric" placeholder="1200000" value="1200000">'
      );
      box.innerHTML = rows.join("");
      box.querySelectorAll("input,select").forEach(function (el) {
        el.addEventListener("input", renderClaim);
        el.addEventListener("change", renderClaim);
      });
      return;
    }

    if (!speed) {
      rows.push('<label for="geCond">' + esc(CLAIM.condition_label) + "</label>" +
        '<input id="geCond" type="number" step="1" value="10">');
    }
    if (speed || timed) {
      rows.push(
        '<label for="geDistance">거리</label><select id="geDistance">' +
        '<option value="5">5km</option><option value="10" selected>10km</option>' +
        '<option value="21.0975">하프(21.1km)</option><option value="42.195">풀(42.2km)</option></select>',
        '<label for="geTime">완주 기록</label>' +
        '<input id="geTime" type="text" inputmode="numeric" placeholder="52:30" autocomplete="off">',
        '<label for="geGender">성별</label><select id="geGender">' +
        '<option value="male">남성</option><option value="female">여성</option></select>',
        '<label for="geBirthYear">출생연도</label>' +
        '<input id="geBirthYear" type="number" min="1930" max="2020" placeholder="1986">'
      );
    }
    if (timed) {
      rows.push('<label for="gePrice">가격 (원)</label>' +
        '<input id="gePrice" type="text" inputmode="numeric" placeholder="300000" value="300000">');
    }
    box.innerHTML = rows.join("");
    box.querySelectorAll("input,select").forEach(function (el) {
      el.addEventListener("input", renderClaim);
      el.addEventListener("change", renderClaim);
    });
  }

  function claimMeta() {
    var box = $("gearMeta");
    if (!box || !CLAIM) return;
    var html = "";
    if (CLAIM.surprise) {
      html += '<p class="gm-surprise">' + esc(CLAIM.surprise) + "</p>";
    }
    if (CLAIM.model_note) {
      html += "<h2>이 숫자를 어떻게 냈나</h2><p class=\"gm-measure\">" +
        esc(CLAIM.model_note) + "</p>";
    }
    if (CLAIM.transfer_note) {
      html += "<h2>기록으로 바꿀 때의 가정</h2><p class=\"gm-measure\">" +
        esc(CLAIM.transfer_note) + "</p>";
    }
    html += '<p class="gm-src">효과 수치의 출처는 위 각 항목에 적어 두었습니다.' +
      '<span class="gm-note">연구에서 보고된 값이며, 개인의 결과를 보장하지 않습니다. ' +
      '새 연구가 나오면 이 판정도 함께 갱신합니다.</span></p>';
    box.innerHTML = html;
  }

  // ── 시작 ────────────────────────────────────────────────────────
  function setHead(title, question) {
    var t = $("gearTitle"); if (t) t.textContent = title;
    var q = $("gearQuestion"); if (q) q.textContent = question || "";
    if (title) document.title = title + " — 기어 판정 | calrank";
  }

  function init() {
    Promise.all([
      fetch("data/gear_claims.json").then(function (r) { return r.json(); }),
      fetch("data/gear_rules.json").then(function (r) { return r.json(); })
    ]).then(function (d) {
      CLAIMS = d[0]; RULES = d[1];
      var q = new URLSearchParams(location.search);
      var rid = q.get("r"), cid = q.get("c");
      RULE = rid ? window.calrankRules.findRule(RULES, rid) : null;
      CLAIM = cid ? window.calrankGear.findClaim(CLAIMS, cid) : null;

      if (RULE) {
        document.body.classList.add("ge-detail-mode", "ge-rule-mode");
        setHead(RULE.label, RULE.question);
        var hl = $("gearHeadline");
        if (hl && RULE.headline) hl.textContent = RULE.headline;
        buildRuleForm(); ruleMeta(); renderRule();
      } else if (CLAIM) {
        document.body.classList.add("ge-detail-mode", "ge-claim-mode");
        setHead(CLAIM.label, CLAIM.question);
        var chl = $("gearHeadline");
        if (chl && CLAIM.headline) chl.textContent = CLAIM.headline;
        buildClaimForm(); claimMeta(); renderClaim();
      } else {
        document.body.classList.add("ge-hub-mode");
        buildHub();
      }
    }).catch(function () {
      var out = $("gearResult");
      if (out) out.innerHTML = '<p class="gr-hint">자료를 불러오지 못했습니다. 새로고침해 주세요.</p>';
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else { init(); }
})();
