// 규정 원문 확인 현황 — data/source_watch.json (매주 자동 갱신)을 읽어 화면에 보여 준다.
// 파일이 없거나 받지 못하면 아무것도 바꾸지 않는다.
(function () {
  "use strict";
  var cache = null;
  function load() {
    if (cache) return cache;
    cache = fetch("data/source_watch.json").then(function (r) { return r.ok ? r.json() : {}; }).catch(function () { return {}; });
    return cache;
  }
  function recent(rec, days) {
    if (!rec || !rec.changed) return false;
    return (Date.now() - new Date(rec.changed).getTime()) / 864e5 <= days;
  }
  function paint() {
    var els = document.querySelectorAll("[data-watch]");
    if (!els.length) return;
    load().then(function (w) {
      [].forEach.call(els, function (el) {
        var rec = w[el.getAttribute("data-watch")];
        if (!rec || !rec.checked) return;
        var t = "원문 마지막 확인 " + rec.checked;
        if (recent(rec, 60)) t += " · " + rec.changed + "에 원문이 바뀌었을 수 있습니다. 원문을 다시 확인해 주세요.";
        el.textContent = t;
        if (recent(rec, 60)) el.classList.add("dq-changed");
      });
    });
  }
  window.CalrankWatch = { load: load, recent: recent };
  document.addEventListener("DOMContentLoaded", paint);
})();
