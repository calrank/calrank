// 대회 페이지의 장비 점검 카드 — 일정 × 날씨 × 연맹 규정을 한 화면에서 잇는다.
//
// 규정 숫자는 data/gear_rules.json 에서 그대로 읽는다. 이 파일에 숫자를 적지 않는다.
// 숫자를 두 군데 적으면 한쪽만 고쳐졌을 때 대회 페이지가 틀린 규정을 말한다.
//
// 이 카드가 하지 않는 것
//  - 대회 주최측이 따로 정한 규정은 모른다. 연맹 규정이 그 대회에 적용되는지는
//    카드 맨 아래에 "요강에서 확인"으로 남긴다.
//  - 날씨로 규정이 바뀐다고 말하지 않는다. 날씨는 "이 규정을 볼 이유"로만 붙인다.
//  - 수온 예보를 만들지 않는다. 바다 근처일 때 해양 모델 값을 참고로 채우되,
//    강·호수 대회에서는 이 값을 믿지 말라고 적는다.
(function (g) {
  "use strict";
  var RULES = null;

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function loadRules() {
    if (RULES) return Promise.resolve(RULES);
    return fetch("data/gear_rules.json").then(function (r) { return r.json(); })
      .then(function (d) { RULES = d; return d; });
  }

  var DQ = null;
  function loadDq() {
    if (DQ) return Promise.resolve(DQ);
    return fetch("data/gear_dq.json").then(function (r) { return r.json(); })
      .then(function (d) { DQ = d; return d; }).catch(function () { return null; });
  }
  // 출발 전 점검표: 체크 상태는 이 기기에만 저장한다(대회마다 따로).
  var CHECK_KEY = "calrank.check.v1";
  var CHECK_IDS = ["wt-helmet", "wt-device", "wt-bib", "wt-draft-zone", "wt-draft-penalty"];
  function checkKey(ev) { return String(ev.id || (ev.name + "|" + ev.date)); }
  function readChecks(ev) {
    try { var o = JSON.parse(localStorage.getItem(CHECK_KEY) || "{}"); return o[checkKey(ev)] || []; } catch (e) { return []; }
  }
  function writeChecks(ev, ids) {
    try {
      var o = JSON.parse(localStorage.getItem(CHECK_KEY) || "{}");
      o[checkKey(ev)] = ids; localStorage.setItem(CHECK_KEY, JSON.stringify(o));
    } catch (e) {}
  }
  function checklistRow(ev) {
    var items = DQ && DQ.sports && DQ.sports.triathlon && DQ.sports.triathlon.items;
    if (!items) return "";
    var done = readChecks(ev);
    var lis = CHECK_IDS.map(function (id) {
      var it = items.filter(function (x) { return x.id === id; })[0];
      if (!it) return "";
      return '<li><label><input type="checkbox" data-ck="' + esc(id) + '"' + (done.indexOf(id) >= 0 ? " checked" : "") + "> " +
        "<b>" + esc(it.title) + "</b> <span class=\"gv-small\">" + esc(it.severity) + " · " + esc(it.clause) + "</span></label>" +
        ' <a href="standards-triathlon.html#' + esc(id) + '">조항 보기</a></li>';
    }).join("");
    return row("출발 전 점검표",
      '<ul class="gv-ul gv-ck">' + lis + "</ul>" +
      '<p class="gv-small">에이지그룹 기준입니다. 체크는 이 기기에만 저장됩니다. 대회 요강이 더 엄격할 수 있습니다.</p>',
      "standards-triathlon.html", "실격·벌칙 조항 전체");
  }
  function wireChecks(ev) {
    var boxes = document.querySelectorAll("[data-ck]");
    [].forEach.call(boxes, function (b) {
      b.addEventListener("change", function () {
        var ids = [].filter.call(document.querySelectorAll("[data-ck]"), function (x) { return x.checked; })
          .map(function (x) { return x.getAttribute("data-ck"); });
        writeChecks(ev, ids);
      });
    });
  }

  function find(id) {
    var rs = (RULES && RULES.rules) || [];
    for (var i = 0; i < rs.length; i++) if (rs[i].id === id) return rs[i];
    return null;
  }

  function dday(date) {
    var t = new Date(date + "T00:00:00");
    var n = new Date(); n.setHours(0, 0, 0, 0);
    return Math.round((t - n) / 86400000);
  }

  function getForecast(ev, d) {
    if (!ev.lat || !ev.lng || d < 0 || d > 15) return Promise.resolve(null);
    var u = "https://api.open-meteo.com/v1/forecast?latitude=" + ev.lat + "&longitude=" + ev.lng +
      "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=Asia%2FSeoul" +
      "&start_date=" + ev.date + "&end_date=" + ev.date;
    return fetch(u).then(function (r) { return r.json(); }).then(function (j) {
      var x = j && j.daily;
      if (!x || !x.time || !x.time.length) return null;
      return { tmax: x.temperature_2m_max[0], tmin: x.temperature_2m_min[0], pop: x.precipitation_probability_max[0] };
    }).catch(function () { return null; });
  }

  // 해양 모델의 수온. 시간별 값뿐이라 대회 아침(06~10시) 평균을 쓴다.
  function getSea(ev, d) {
    if (!ev.lat || !ev.lng || d < 0 || d > 7) return Promise.resolve(null);
    var u = "https://marine-api.open-meteo.com/v1/marine?latitude=" + ev.lat + "&longitude=" + ev.lng +
      "&hourly=sea_surface_temperature&timezone=Asia%2FSeoul&start_date=" + ev.date + "&end_date=" + ev.date;
    return fetch(u).then(function (r) { return r.json(); }).then(function (j) {
      var h = j && j.hourly;
      if (!h || !h.time) return null;
      var vals = [];
      for (var i = 0; i < h.time.length; i++) {
        var hr = parseInt(h.time[i].slice(11, 13), 10);
        var v = h.sea_surface_temperature[i];
        if (hr >= 6 && hr <= 10 && typeof v === "number") vals.push(v);
      }
      if (!vals.length) return null;
      return Math.round(vals.reduce(function (a, b) { return a + b; }, 0) / vals.length * 10) / 10;
    }).catch(function () { return null; });
  }

  function limitsText(rule, scopes) {
    var out = [];
    (rule.limits || []).forEach(function (l) {
      if (scopes && scopes.indexOf(l.scope) < 0) return;
      var v = l.min_text || (l.max != null ? "최대 " + l.max : l.min != null ? "최소 " + l.min : "");
      if (v) out.push("<li><b>" + esc(l.scope) + "</b> " + esc(v) + (l.note ? " — " + esc(l.note) : "") + "</li>");
    });
    return out.join("");
  }

  function row(title, bodyHtml, linkHref, linkLabel) {
    return '<div class="gv-row"><h3 class="gv-h">' + esc(title) + "</h3>" + bodyHtml +
      (linkHref ? '<p class="gv-link"><a href="' + esc(linkHref) + '">' + esc(linkLabel) + "</a></p>" : "") + "</div>";
  }

  function wx(f) {
    if (!f) return "";
    return "예보 " + Math.round(f.tmin) + "° / " + Math.round(f.tmax) + "°C, 강수확률 " + f.pop + "%";
  }

  function sections(ev, f, sea) {
    var s = [], r;
    if (ev.sport === "marathon") {
      r = find("wa-stack-height");
      if (r) {
        var road = (r.limits || [])[0];
        s.push(row("신발 밑창 두께",
          "<p>World Athletics 기준으로 로드 신발의 밑창 두께 상한은 <b>" + esc(road.max) + "mm</b>입니다. " +
          "이 기준은 연맹 공인 경기 규정입니다. 이 대회 일반 부문에도 같은 제한이 있는지는 요강에서 확인하세요.</p>",
          "gear-wa-stack-height.html", "내 신발 두께 판정하기"));
      }
      s.push(row("카본화를 신을까",
        "<p>카본 플레이트의 효과는 달리는 속도에 따라 근거 등급이 갈립니다. 내 기록에서 얼마나 줄이고 등급이 바뀌는지는 아래에서 볼 수 있습니다.</p>",
        "gear-carbon-plate.html", "카본화 효과와 근거 등급"));
      if (f) {
        var hot = f.tmax >= 16;
        s.push(row("당일 기온",
          "<p>" + esc(wx(f)) + ". " + (hot
            ? "기록이 가장 잘 나오는 기온대(약 3.8~9.9℃)보다 높습니다. 같은 몸이면 기록이 조금 늦어질 수 있습니다."
            : "기록이 잘 나오는 기온대에 가깝습니다.") + "</p>",
          "level.html", "내 기록을 날씨에 맞춰 보기"));
      }
    } else if (ev.sport === "trail") {
      r = find("utmb-kit");
      if (r) {
        s.push(row("UTMB 기준 필수 장비",
          "<ul class=\"gv-ul\">" + limitsText(r, ["물", "개인 컵", "생존담요", "탄력 붕대", "보온 상의"]) + "</ul>" +
          "<p class=\"gv-small\">UTMB 월드시리즈 기준입니다. 이 대회가 같은 목록을 쓰는지는 요강을 확인하세요.</p>",
          "gear-utmb-kit.html", "필수 장비 목록 전체"));
      }
      r = find("utmb-jacket");
      if (r) {
        var why = f ? (f.pop >= 40
          ? "예보 강수확률이 " + f.pop + "%입니다. 재킷의 방수·투습 기준을 미리 확인해 두세요."
          : "예보 강수확률은 " + f.pop + "%입니다.") + " " + esc(wx(f)) + "." : "";
        s.push(row("방수 재킷", "<p>" + why + " 방수 10,000 Schmerber 이상, 투습 RET 13 이하가 UTMB 기준입니다.</p>",
          "gear-utmb-jacket.html", "내 재킷 판정하기"));
      }
      s.push(row("장비 무게와 폴",
        "<p>배낭 무게와 폴은 기록에 주는 영향이 연구마다 다릅니다. 근거 등급과 함께 정리해 두었습니다.</p>",
        "gear-trail-poles.html", "트레일 폴 효과와 근거 등급"));
    } else if (ev.sport === "cycling") {
      r = find("uci-min-weight");
      if (r) {
        var lim = (r.limits || [])[0] || {};
        s.push(row("자전거 무게 기준",
          "<p>UCI 기준 최소 무게는 <b>" + esc(lim.min) + "kg</b>입니다. UCI 공인 경기에 적용되는 기준이라, 이 대회에 해당하는지는 요강에서 확인하세요.</p>",
          "gear-uci-min-weight.html", "내 자전거 무게 판정하기"));
      }
      s.push(row("타이어와 휠",
        "<p>" + (f ? esc(wx(f)) + ". " : "") + "타이어의 구름저항과 에어로 휠은 속도 구간별로 효과가 달라집니다.</p>",
        "gear-tyre-rolling.html", "타이어와 구름저항"));
    } else if (ev.sport === "triathlon") {
      r = find("wt-wetsuit-temp");
      if (r) {
        var opts = r.check.extra[0].options;
        var optHtml = opts.map(function (o, i) {
          return '<option value="' + esc(o.value) + '"' + (o.value === "ag_long" ? " selected" : "") + ">" + esc(o.label) + "</option>";
        }).join("");
        var seaNote = sea != null
          ? '<p class="gv-small">해양 모델이 보는 대회 아침 수온은 ' + sea + "℃입니다. 바다 근처가 아니라면 맞지 않습니다. 강·호수 대회는 주최측이 잰 값이 기준입니다.</p>"
          : '<p class="gv-small">수온은 예보 값을 믿기 어려워, 대회 전에 공지되는 값을 넣어 보세요.</p>';
        s.push(row("웻슈트, 입어도 되나",
          '<div class="gv-form"><label>참가 구분<select id="gvCat">' + optHtml + "</select></label>" +
          '<label>수온(℃)<input id="gvTemp" type="number" step="0.1" inputmode="decimal" value="' + (sea != null ? sea : "") + '" placeholder="21"></label></div>' +
          '<p class="gv-out" id="gvOut" aria-live="polite"></p>' + seaNote +
          "<p class=\"gv-small\">대회 당일의 공식 수온 측정값이 우선합니다.</p>",
          "gear-wt-wetsuit-temp.html", "수온 기준표 전체"));
      }
      r = find("wt-wetsuit-thickness");
      if (r) s.push(row("웻슈트 두께", "<p>어느 부위를 재도 5mm 이하여야 합니다.</p>",
        "gear-wt-wetsuit-thickness.html", "내 웻슈트 판정하기"));
      if (f) s.push(row("당일 기온", "<p>" + esc(wx(f)) + ".</p>", null, null));
      var ck = checklistRow(ev);
      if (ck) s.push(ck);
    }
    return s;
  }

  function wireWetsuit() {
    var cat = document.getElementById("gvCat"), tmp = document.getElementById("gvTemp"), out = document.getElementById("gvOut");
    if (!cat || !tmp || !out || !g.calrankRules) return;
    var rule = find("wt-wetsuit-temp");
    function paint() {
      var v = parseFloat(tmp.value);
      if (isNaN(v)) { out.textContent = "수온을 넣으면 금지·선택·의무 중 어디인지 알려 드립니다."; return; }
      var res = g.calrankRules.judge({ rule: rule, value: v, choice: cat.value });
      var b = res && res.band;
      if (!b) { out.textContent = ""; return; }
      var txt = { forbidden: "착용 금지", optional: "착용 선택", mandatory: "착용 의무" }[b.verdict];
      out.innerHTML = "<b>" + esc(v) + "℃ → " + txt + "</b> · 금지 " + esc(b.forbiddenAt) + "℃ 이상, 의무 " + esc(b.mandatoryAt) + "℃ 이하";
    }
    cat.addEventListener("change", paint);
    tmp.addEventListener("input", paint);
    paint();
  }

  function render(ev) {
    var box = document.getElementById("gearVerdict");
    if (!box || !ev || !ev.sport || !ev.date) return;
    var d = dday(ev.date);
    if (d < 0) return;
    Promise.all([loadRules(), getForecast(ev, d), ev.sport === "triathlon" ? getSea(ev, d) : Promise.resolve(null), ev.sport === "triathlon" ? loadDq() : Promise.resolve(null)])
      .then(function (res) {
        var f = res[1], sea = res[2];
        var list = sections(ev, f, sea);
        if (!list.length) return;
        var head = d === 0 ? "오늘이 대회일입니다" : "대회까지 D-" + d;
        box.innerHTML = '<section class="gv" aria-labelledby="gvTitle"><h2 class="gv-title" id="gvTitle">장비 점검 <span class="gv-d">' + head + "</span></h2>" +
          '<p class="gv-sub">연맹 규정과 연구 근거로 본 이 대회의 장비입니다. ' + (f ? "날씨 예보에 따라 매일 달라집니다." : (d > 15 ? "대회 15일 전부터 날씨 예보가 함께 나옵니다." : "")) + "</p>" +
          list.join("") +
          '<p class="gv-foot">규정은 연맹 문서 기준이며, 주최측이 따로 정한 규정이 있으면 그쪽이 우선합니다. 예보는 바뀔 수 있습니다. <a href="kit.html">내 장비 서랍에 저장해 두고 한 번에 보기</a></p></section>';
        wireWetsuit();
        wireChecks(ev);
      }).catch(function () {});
  }

  g.renderGearVerdict = render;
  if (g.__calrankEvent) render(g.__calrankEvent);
})(typeof window !== "undefined" ? window : globalThis);
