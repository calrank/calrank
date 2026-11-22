/* 등급 페이지 안에서 바로 내 등급을 보는 입력창.
   계산은 이 페이지 안에서 끝나고 기록은 저장하지 않는다. 등급 경계(data-tiers)는
   페이지 생성기가 TIER_BOUNDS 에서 그대로 넣는다. wma-standards.js 가 먼저 불려 있어야 한다. */
(function () {
  var box = document.getElementById("grQuick");
  if (!box || typeof wmaStandard !== "function") return;
  var dist = box.getAttribute("data-dist"), km = box.getAttribute("data-km");
  var fixed = box.getAttribute("data-gender") || "";
  var label = box.getAttribute("data-label") || "";
  var tiers;
  try { tiers = JSON.parse(box.getAttribute("data-tiers")); } catch (e) { return; }
  var RANGE = { "5km": [700, 3600], "10km": [1500, 7200], "half": [3300, 14400], "full": [7200, 25200] }[dist];
  if (!RANGE || !tiers || !tiers.length) return;

  box.innerHTML =
    '<h2 class="gq-h">내 기록을 넣어 보세요</h2>' +
    '<p class="gq-sub">표를 찾지 않아도 ' + label + ' 등급과 다음 등급까지 남은 시간이 바로 나옵니다.</p>' +
    '<form class="gq-form" novalidate>' +
    '<label>완주 기록<input type="text" id="gqTime" inputmode="numeric" placeholder="' + (dist === "full" ? "3:45:00" : dist === "half" ? "1:55:00" : "55:00") + '" autocomplete="off"></label>' +
    '<label>나이<input type="number" id="gqAge" inputmode="numeric" placeholder="42" min="10" max="99"></label>' +
    (fixed ? "" : '<label>성별<select id="gqSex"><option value="male">남성</option><option value="female">여성</option></select></label>') +
    '<button type="submit" class="gq-go">등급 확인</button></form>' +
    '<p class="gq-err" role="alert" hidden></p><div class="gq-out" aria-live="polite" hidden></div>';

  var form = box.querySelector(".gq-form"), err = box.querySelector(".gq-err"), out = box.querySelector(".gq-out");

  function sec(t) {
    var m = String(t || "").trim().match(/^(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?$/);
    if (!m) return null;
    var a = +m[1], b = +m[2], c = m[3] === undefined ? null : +m[3];
    if (b > 59 || (c !== null && c > 59)) return null;
    return c === null ? a * 60 + b : a * 3600 + b * 60 + c;
  }
  function clock(s) {
    s = Math.round(s);
    var h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60;
    function p(n) { return String(n).padStart(2, "0"); }
    return h ? h + ":" + p(m) + ":" + p(x) : m + ":" + p(x);
  }
  function fail(msg) { err.textContent = msg; err.hidden = false; out.hidden = true; }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    err.hidden = true;
    var s = sec(form.querySelector("#gqTime").value);
    var age = parseInt(form.querySelector("#gqAge").value, 10);
    var sex = fixed || form.querySelector("#gqSex").value;
    if (!s) return fail("완주 기록을 " + (dist === "full" || dist === "half" ? "1:55:00" : "55:00") + " 형식으로 넣어 주세요.");
    if (!(age >= 10 && age <= 99)) return fail("나이를 10에서 99 사이로 넣어 주세요.");
    if (s < RANGE[0] || s > RANGE[1]) return fail(label + " 기록으로 보기 어렵습니다. " + clock(RANGE[0]) + "에서 " + clock(RANGE[1]) + " 사이로 확인해 주세요.");
    var std = wmaStandard(sex, dist, age), pct = std / s * 100, name = tiers[tiers.length - 1][1], idx = tiers.length - 1;
    for (var i = 0; i < tiers.length; i++) { if (pct >= tiers[i][0]) { name = tiers[i][1]; idx = i; break; } }
    var h = '<div class="gq-card"><span class="gq-k">칼랭크 등급</span><b>' + name + '</b>' +
            '<span class="gq-v">연령등급 ' + pct.toFixed(1) + '% · ' + age + '세 ' + (sex === "male" ? "남성" : "여성") + '</span></div>';
    if (idx > 0) {
      var need = std / (tiers[idx - 1][0] / 100);
      h += '<p class="gq-next">다음 등급 <b>‘' + tiers[idx - 1][1] + '’</b>까지 <b>' + clock(need) + '</b> — 지금보다 <b>' + clock(s - need) + '</b> 줄이면 됩니다.</p>';
    } else {
      h += '<p class="gq-next">가장 높은 등급입니다.</p>';
    }
    var by = new Date().getFullYear() - age;
    var q = "level.html?d=" + encodeURIComponent(km) + "&t=" + encodeURIComponent(clock(s)) + "&g=" + sex + "&by=" + by + "#now";
    h += '<a class="gq-more" href="' + q + '">공유 카드 만들고 다른 거리 등급도 보기 →</a>' +
         '<p class="gq-note">계산은 이 페이지 안에서 끝납니다. 기록은 저장되지 않습니다.</p>';
    out.innerHTML = h; out.hidden = false;
    try { if (window.calrankMark) window.calrankMark("gq-calc"); } catch (x) {}
  });
})();
