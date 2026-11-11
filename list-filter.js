// 산·코스 목록에서 이름으로 거르는 검색 칸. 이 기기 안에서만 동작한다(입력을 어디에도 보내지 않는다).
(function () {
  "use strict";
  var q = document.getElementById("listQ"); if (!q) return;
  var items = Array.prototype.slice.call(document.querySelectorAll(".cp-list li"));
  var secs = Array.prototype.slice.call(document.querySelectorAll("section.tp-sec")).filter(function (s) { return s.querySelector(".cp-list li"); });
  var msg = document.getElementById("listMsg");
  function run() {
    var v = q.value.replace(/\s+/g, "").toLowerCase(), shown = 0;
    items.forEach(function (li) {
      var ok = !v || li.textContent.replace(/\s+/g, "").toLowerCase().indexOf(v) >= 0;
      li.hidden = !ok; if (ok) shown++;
    });
    secs.forEach(function (s) { s.hidden = !!v && !Array.prototype.some.call(s.querySelectorAll(".cp-list li"), function (li) { return !li.hidden; }); });
    if (msg) msg.textContent = v ? (shown ? shown + "곳을 찾았어요." : "맞는 곳이 없어요. 이름 일부만 적어 보세요.") : "";
  }
  q.addEventListener("input", run);
})();
