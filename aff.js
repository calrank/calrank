/* 제휴 링크를 누른 횟수를 센다(어느 페이지에서 눌렀는지만, 사람은 식별하지 않는다).
   funnel.js 의 calrankMark 가 /_f/aff-click 조회로 기록한다. */
(function () {
  document.addEventListener("click", function (e) {
    var a = e.target && e.target.closest ? e.target.closest("a[data-aff]") : null;
    if (!a) return;
    try { if (window.calrankMark) window.calrankMark("aff-click"); } catch (x) {}
  });
})();
