// 내 장비 서랍 — 내 장비 수치를 한 번 적어 두면 연맹 규정에 맞는지 한 화면에서 본다.
//
// 수치는 이 기기에만 저장한다(calrank-local.js). 서버로 보내지 않는다.
//
// 규정 개정 감지: 규정 값(check + limits)의 지문을 처음 본 때 저장해 두고, 다시 열었을 때
// 지문이 다르면 알린다. 이것은 "연맹이 규정을 바꿨다"가 아니라 "칼랭크가 가진 값이
// 바뀌었다"는 뜻이다. 연맹이 바꿨을 수도 있고 칼랭크가 잘못된 값을 고쳤을 수도
// 있어서, 알림 문구도 그렇게만 말한다.
//
// 필요한 스크립트: gear-rules.js, calrank-local.js
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var L = window.CalrankLocal;
  var SPORTS = [["running", "러닝"], ["trail", "트레일러닝"], ["cycling", "사이클링"], ["triathlon", "철인3종"], ["inline", "인라인"]];
  var DATA = null;

  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  function checkable() {
    return DATA.rules.filter(function (r) { return r.check && r.check.type === "number" && (r.check.compare === "max" || r.check.compare === "min"); });
  }
  function fpOf(r) { return L.fingerprint(JSON.stringify({ c: r.check, l: r.limits })); }

  function verdictHtml(res) {
    if (!res || res.verdict === "unknown") return '<span class="kit-v unknown">수치를 넣으면 판정합니다</span>';
    var lines = (res.results || []).map(function (x) {
      var v = x.result;
      if (v.unlimited) return esc(x.scope) + " 제한 없음";
      var m = v.margin != null ? " (" + (v.margin >= 0 ? "여유 " : "초과 ") + Math.abs(Math.round(v.margin * 100) / 100) + res.unit + ")" : "";
      return esc(x.scope) + " " + (v.verdict === "pass" ? "통과" : v.verdict === "fail" ? "기준 밖" : "확인 필요") + m;
    });
    if (res.results && res.results.length > 1) {
      return '<span class="kit-v ' + (res.verdict === "fail" ? "fail" : "pass") + '">' +
        (res.verdict === "pass" ? "모두 통과" : res.verdict === "fail" ? "모두 기준 밖" : "일부만 통과") + "</span>" +
        '<div class="kit-meta">' + lines.join("<br>") + "</div>";
    }
    var v = res.results && res.results[0] && res.results[0].result;
    var cls = res.verdict === "fail" ? "fail" : "pass";
    var tail = v && v.margin != null ? " (" + (v.margin >= 0 ? "여유 " : "초과 ") + Math.abs(Math.round(v.margin * 100) / 100) + res.unit + ")" : "";
    return '<span class="kit-v ' + cls + '">' + esc((v && v.unlimited ? "제한 없음" : "") + tail).trim() + "</span>";
  }

  function itemHtml(r, saved) {
    var c = r.check;
    var body = r.body ? (DATA.bodies[r.body] || {}).label_ko || "" : "";
    return '<div class="kit-item" data-id="' + esc(r.id) + '">' +
      '<p class="kit-name">' + esc(c.label) + "</p>" +
      '<p class="kit-q">' + esc(r.question) + "</p>" +
      '<div class="kit-row"><input type="number" inputmode="decimal" step="' + esc(c.step || "any") + '" placeholder="' + esc(c.placeholder || "") + '" value="' + (saved != null ? esc(saved) : "") + '" aria-label="' + esc(c.label) + '">' +
      '<span class="kit-unit">' + esc(c.unit) + '</span><span class="kit-out"></span></div>' +
      '<p class="kit-meta">' + esc(body) + " · " + esc(r.source) + ' · <a href="gear-' + esc(r.id) + '.html">판정 자세히</a></p></div>';
  }

  function paintOne(el) {
    var id = el.getAttribute("data-id");
    var r = window.calrankRules.findRule(DATA, id);
    var v = parseFloat(el.querySelector("input").value);
    var res = window.calrankRules.judge({ rule: r, value: isNaN(v) ? null : v });
    el.querySelector(".kit-out").innerHTML = verdictHtml(res);
    return res;
  }

  function summary() {
    var items = [].slice.call(document.querySelectorAll(".kit-item"));
    var filled = 0, bad = [];
    items.forEach(function (el) {
      var inp = el.querySelector("input");
      if (inp.value !== "") {
        filled++;
        var out = el.querySelector(".kit-v");
        if (out && out.classList.contains("fail")) bad.push(el.querySelector(".kit-name").textContent);
      }
    });
    var s = $("kitSummary");
    if (!filled) { s.textContent = "아직 넣은 장비가 없습니다. 아래에서 가진 장비의 수치를 넣어 보세요."; return; }
    s.innerHTML = "장비 <b>" + filled + "개</b>를 넣었고, " + (bad.length ? "기준 밖인 것은 <b>" + bad.map(esc).join(", ") + "</b>입니다." : "기준 밖인 것은 없습니다.");
  }

  function renderChanges() {
    var seen = L.seen(), changed = [], first = {};
    DATA.rules.forEach(function (r) {
      var fp = fpOf(r);
      if (seen[r.id] == null) first[r.id] = fp;
      else if (seen[r.id] !== fp) changed.push(r);
    });
    if (Object.keys(first).length) L.setSeen(first);
    var box = $("kitChanges");
    if (window.CalrankWatch) {
      window.CalrankWatch.load().then(function (w) {
        var hit = DATA.rules.filter(function (r) { return r.url && window.CalrankWatch.recent(w[r.url], 60); });
        if (!hit.length) return;
        var p = document.createElement("div"); p.className = "tp-alert";
        p.innerHTML = "규정 원문(연맹 문서)이 최근 바뀌었을 수 있는 항목: <b>" +
          hit.map(function (r) { return esc(r.check ? r.check.label : r.label); }).join(", ") +
          "</b>. 자동 확인에서 문서 내용이 지난번과 달랐다는 뜻이라, 어디가 달라졌는지는 원문에서 확인해 주세요.";
        box.parentNode.insertBefore(p, box);
      });
    }
    if (!changed.length) { box.hidden = true; return; }
    box.hidden = false;
    box.innerHTML = "칼랭크가 가진 규정 값이 지난번 이후 바뀐 항목이 있습니다: <b>" +
      changed.map(function (r) { return esc(r.check ? r.check.label : r.label); }).join(", ") +
      "</b>. 연맹의 개정일 수도 있고 칼랭크가 값을 고친 것일 수도 있으니, 판정을 다시 확인해 주세요." +
      ' <button type="button" class="tp-btn ghost" id="kitAck">확인했어요</button>';
    $("kitAck").addEventListener("click", function () {
      var m = {}; changed.forEach(function (r) { m[r.id] = fpOf(r); }); L.setSeen(m); box.hidden = true;
    });
  }

  function render() {
    var kit = L.kit(), html = "";
    var rules = checkable();
    SPORTS.forEach(function (s) {
      var rs = rules.filter(function (r) { return r.sport === s[0]; });
      if (!rs.length) return;
      html += '<section class="tp-card"><h2 class="tp-h2">' + s[1] + "</h2>" + rs.map(function (r) { return itemHtml(r, kit[r.id]); }).join("") + "</section>";
    });
    $("kitList").innerHTML = html;
    [].forEach.call(document.querySelectorAll(".kit-item"), function (el) {
      paintOne(el);
      el.querySelector("input").addEventListener("input", function () {
        var v = parseFloat(this.value);
        L.setKit(el.getAttribute("data-id"), isNaN(v) ? null : v);
        paintOne(el); summary();
      });
    });
    summary();
    $("kitStore").textContent = L.isPersistent()
      ? "이 기기의 브라우저 안에만 저장됩니다. 서버로 보내지 않고, 다른 기기에서는 보이지 않습니다."
      : "지금 브라우저가 저장을 막고 있어서, 이 탭을 닫으면 입력한 값이 사라집니다.";
  }

  document.addEventListener("DOMContentLoaded", function () {
    fetch("data/gear_rules.json").then(function (r) { return r.json(); }).then(function (d) {
      DATA = d; renderChanges(); render();
    }).catch(function () { $("kitList").innerHTML = '<p class="tp-p">규정 자료를 불러오지 못했습니다. 잠시 뒤 다시 열어 주세요.</p>'; });
    $("kitCopy").addEventListener("click", function () {
      var lines = [];
      [].forEach.call(document.querySelectorAll(".kit-item"), function (el) {
        var v = el.querySelector("input").value;
        if (v === "") return;
        var out = el.querySelector(".kit-v");
        var st = out ? (out.classList.contains("fail") ? "기준 밖" : out.classList.contains("pass") ? "통과" : "") : "";
        lines.push(el.querySelector(".kit-name").textContent + " " + v + el.querySelector(".kit-unit").textContent + (st ? " — " + st : ""));
      });
      var msg = $("kitCopyMsg");
      if (!lines.length) { msg.textContent = "복사할 수치가 아직 없습니다."; return; }
      var text = "내 장비 점검 (칼랭크 · 연맹 규정 기준)\n" + lines.join("\n") + "\n" + location.href.split("#")[0];
      var done = function (ok) { msg.textContent = ok ? "복사했습니다." : "복사하지 못했습니다. 직접 선택해 복사해 주세요."; };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(function () { done(true); }, function () { done(false); });
      else done(false);
    });
    $("kitClear").addEventListener("click", function () {
      if (!confirm("이 기기에 저장된 장비 수치를 모두 지울까요?")) return;
      var kit = L.kit(); Object.keys(kit).forEach(function (k) { L.setKit(k, null); }); render();
    });
  });
})();
