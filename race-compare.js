/* 마라톤 대회 비교: 페이지에 실린 값(#rcData)만으로 그린다. 서버로 보내는 것은 없다. */
(function () {
  var el = document.getElementById("rcData");
  if (!el) return;
  var D;
  try { D = JSON.parse(el.textContent); } catch (e) { return; }
  if (!D.length) return;
  var sel = [0, 1, 2].map(function (i) { return document.getElementById("rcS" + i); });
  if (sel.some(function (s) { return !s; })) return;
  function lab(x) { return x.date.slice(5).replace("-", "/") + " · " + x.name.replace(/^제\d+회\s*/, ""); }
  function esc(t) { return String(t).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  var today = new Date(Date.now() + 9 * 36e5).toISOString().slice(0, 10);
  var start = D.findIndex(function (x) { return x.date >= today; });
  if (start < 0 || start > D.length - 3) start = Math.max(0, D.length - 3);
  var step = Math.max(1, Math.floor((D.length - start) / 3));  // 처음 보는 사람에게 계절이 다른 대회를 보여 준다
  // 공유 링크의 #r=아이디,아이디,아이디 로 같은 비교를 다시 연다. 아이디가 목록에 없으면 기본 선택을 쓴다.
  var ids = [];
  try { var m = /(?:^|[#&])r=([^&]+)/.exec(location.hash); if (m) ids = decodeURIComponent(m[1]).split(","); } catch (e) {}
  sel.forEach(function (s, i) {
    D.forEach(function (x, k) { var o = document.createElement("option"); o.value = k; o.textContent = lab(x); s.appendChild(o); });
    var at = D.findIndex(function (x) { return x.id === ids[i]; });
    s.value = at >= 0 ? at : Math.min(start + i * step, D.length - 1);
    s.addEventListener("change", draw);
  });
  var shareBtn = document.getElementById("rcShare"), shareMsg = document.getElementById("rcShareMsg");
  function shareUrl() {
    var r = sel.map(function (s) { return D[+s.value].id; }).join(",");
    return location.origin + location.pathname + "?utm_source=share#r=" + encodeURIComponent(r);
  }
  if (shareBtn) shareBtn.addEventListener("click", function () {
    var url = shareUrl(), E = sel.map(function (s) { return D[+s.value].name; });
    var title = "마라톤 대회 비교: " + E.join(" · ");
    function copied() { if (shareMsg) shareMsg.textContent = " 링크를 복사했습니다."; }
    if (navigator.share) { navigator.share({ title: title, url: url }).catch(function () {}); return; }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(copied, function () { if (shareMsg) shareMsg.textContent = " " + url; });
    else if (shareMsg) shareMsg.textContent = " " + url;
  });
  var SH = ["circle", "square", "diamond"];
  function mark(sh, x, y, r) {
    if (sh === "circle") return '<circle cx="' + x + '" cy="' + y + '" r="' + r + '"/>';
    if (sh === "square") return '<rect x="' + (x - r) + '" y="' + (y - r) + '" width="' + 2 * r + '" height="' + 2 * r + '" rx="2"/>';
    return '<path d="M' + x + " " + (y - r - 1) + "L" + (x + r + 1) + " " + y + "L" + x + " " + (y + r + 1) + "L" + (x - r - 1) + " " + y + 'Z"/>';
  }
  function draw() {
    var E = sel.map(function (s) { return D[+s.value]; });
    var W = 360, L = 12, R = 12, T = 26, RH = 46, H = T + RH * 3 + 26, mn = -10, mx = 40;
    function X(v) { return L + (v - mn) / (mx - mn) * (W - L - R); }
    var g = "", t, i;
    for (t = -10; t <= 40; t += 10) g += '<line class="rc-ax" x1="' + X(t) + '" x2="' + X(t) + '" y1="' + (T - 6) + '" y2="' + (T + RH * 3) + '"/><text x="' + X(t) + '" y="' + (T + RH * 3 + 16) + '" text-anchor="middle">' + t + "°</text>";
    g += '<line class="rc-ref" x1="' + X(15) + '" x2="' + X(15) + '" y1="' + (T - 8) + '" y2="' + (T + RH * 3) + '"/><text class="rc-reft" x="' + X(15) + '" y="12" text-anchor="middle">기준 15도</text>';
    E.forEach(function (e, i) {
      var y = T + i * RH + RH / 2, w = Math.max(X(e.hi) - X(e.lo), 2);
      g += '<g class="rc-s' + i + '"><rect class="rc-bar" x="' + X(e.lo) + '" y="' + (y - 6) + '" width="' + w + '" height="12" rx="6"/>' + mark(SH[i], X(e.hot), y, 5) + "</g>" +
        '<text x="' + X(e.lo) + '" y="' + (y - 12) + '" text-anchor="' + (e.lo < -5 ? "start" : "middle") + '">' + e.lo.toFixed(1) + "°</text>" +
        '<text x="' + X(e.hi) + '" y="' + (y - 12) + '" text-anchor="middle">' + e.hi.toFixed(1) + "°</text>";
    });
    var c = document.getElementById("rcChart");
    c.setAttribute("viewBox", "0 0 " + W + " " + H); c.innerHTML = g;
    document.getElementById("rcNames").innerHTML = E.map(function (e, i) {
      return '<li><span class="rc-dot rc-d' + i + '"></span><span><b>' + esc(e.name) + "</b> · " + e.date.replace(/-/g, ".") + " · " + esc(e.region) + " · 최고 " + e.hot.toFixed(1) + "°(" + e.hotY + ')<br><span class="tp-small">' + esc(e.st) + " 관측소, 대회장에서 약 " + e.km + "km</span></span></li>";
    }).join("");
    document.getElementById("rcHeat").innerHTML = E.map(function (e, i) {
      var t = e.over > 0
        ? "일평균을 어림하면 약 " + e.avg.toFixed(1) + "도로 기준보다 <b>" + e.over.toFixed(1) + "도 높습니다.</b> 같은 몸 상태라면 시원한 날보다 약 <b>" + e.pct.toFixed(1) + "%</b> 느려질 수 있습니다" + (e.capped ? " (23도까지만 계산)." : ".")
        : "일평균을 어림하면 약 " + e.avg.toFixed(1) + "도로 기준보다 낮아 더위로 깎이는 계산은 붙이지 않았습니다.";
      return '<div class="rc-row"><span class="rc-dot rc-d' + i + '"></span><p><b>' + esc(e.name) + "</b><br>" + t + "</p></div>";
    }).join("");
    document.getElementById("rcRain").innerHTML = E.map(function (e, i) {
      var s = "", k;
      for (k = 0; k < e.yrs; k++) s += '<i class="' + (k < e.rain ? "on" : "") + '"></i>';
      return '<div class="rc-row"><span class="rc-dot rc-d' + i + '"></span><p><b>' + esc(e.name) + "</b> · " + e.yrs + "년 중 " + e.rain + '번<span class="rc-dots" aria-hidden="true">' + s + "</span></p></div>";
    }).join("");
  }
  draw();
})();
