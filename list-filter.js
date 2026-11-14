// 산·코스 목록에서 이름·지역으로 거르는 검색 칸. 입력은 이 기기 안에서만 쓰고 어디에도 보내지 않는다.
// 이 목록에 없으면 짝이 되는 목록(코스 ↔ 산)에서도 찾아 링크로 보여 준다.
(function () {
  "use strict";
  var q = document.getElementById("listQ"); if (!q) return;
  var items = Array.prototype.slice.call(document.querySelectorAll(".cp-list li")).filter(function (li) { return !li.closest("#listMore"); });
  var secs = Array.prototype.slice.call(document.querySelectorAll("section.tp-sec")).filter(function (s) { return s.querySelector(".cp-list li") && !s.querySelector("#listQ"); });
  var msg = document.getElementById("listMsg");
  var more = document.getElementById("listMore");
  var otherUrl = more && more.getAttribute("data-other");
  var otherLabel = otherUrl === "mountains.html" ? "산별 등산로" : "트레일루트 코스";
  var other = null, loading = false;
  function norm(t) { return t.replace(/\s+/g, "").toLowerCase(); }
  function loadOther(cb) {
    if (other) return cb();
    if (loading || !otherUrl || !window.fetch) return;
    loading = true;
    fetch(otherUrl).then(function (r) { return r.text(); }).then(function (t) {
      var d = new DOMParser().parseFromString(t, "text/html"), seen = {};
      other = [];
      Array.prototype.forEach.call(d.querySelectorAll(".cp-list li a.cp-row"), function (a) {
        var href = a.getAttribute("href"); if (seen[href] || !/^(mountain|course)-/.test(href)) return;
        seen[href] = 1; other.push({ href: href, name: (a.querySelector(".cp-name") || a).textContent.trim(), sub: ((a.querySelector(".cp-near") || {}).textContent || "").trim(), key: norm(a.textContent) });
      });
      cb();
    }).catch(function () { loading = false; });
  }
  function showOther(v, ownShown) {
    if (!more) return;
    more.innerHTML = "";
    if (!v || !other) return;
    var hits = other.filter(function (o) { return o.key.indexOf(v) >= 0; });
    if (!hits.length) return;
    var li0 = document.createElement("li"); li0.className = "cp-un";
    li0.textContent = otherLabel + "에서 " + hits.length + "곳이 더 일치합니다" + (hits.length > 8 ? " (8곳 표시)" : "") + ".";
    more.appendChild(li0);
    hits.slice(0, 8).forEach(function (o) {
      var li = document.createElement("li"), a = document.createElement("a");
      a.href = o.href; a.textContent = o.name + (o.sub ? " · " + o.sub : "");
      li.appendChild(a); more.appendChild(li);
    });
    if (!ownShown && msg) msg.textContent = "이 목록에는 일치하는 곳이 없습니다. " + otherLabel + "에서 찾았습니다.";
  }
  function run() {
    var v = norm(q.value), shown = 0;
    items.forEach(function (li) {
      var ok = !v || norm(li.textContent).indexOf(v) >= 0;
      li.hidden = !ok; if (ok) shown++;
    });
    secs.forEach(function (s) { s.hidden = !!v && !Array.prototype.some.call(s.querySelectorAll(".cp-list li"), function (li) { return !li.closest("#listMore") && !li.hidden; }); });
    if (msg) msg.textContent = v ? (shown ? shown + "곳이 일치합니다." : "일치하는 곳이 없습니다. 이름이나 지역의 일부만 입력해 보세요.") : "";
    if (v) loadOther(function () { showOther(v, shown); }); else if (more) more.innerHTML = "";
  }
  q.addEventListener("input", run);
})();
