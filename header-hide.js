/* 위로 올릴 때만 메뉴를 보여 준다.
   처음에는 메뉴가 보이고, 아래로 내려 읽기 시작하면 위로 사라진다.
   조금이라도 위로 올리면 다시 나온다. 맨 위에서는 항상 보인다. */
(function () {
  "use strict";
  var h = document.querySelector(".site-header");
  if (!h || !window.requestAnimationFrame) return;
  var reduce = false;
  try { reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) {}
  if (!reduce) h.style.transition = "transform .25s ease";
  var last = window.pageYOffset || 0, hidden = false, ticking = false;
  function set(v) {
    if (v === hidden) return;
    hidden = v;
    h.style.transform = v ? "translateY(-100%)" : "";
  }
  function onFrame() {
    ticking = false;
    var y = Math.max(0, window.pageYOffset || 0), d = y - last;
    if (y <= 8) set(false);                                   // 맨 위
    else if (Math.abs(d) >= 6) {                              // 손 떨림은 무시
      if (d > 0 && y > h.offsetHeight) set(true);             // 내리는 중
      else if (d < 0) set(false);                             // 올리는 중
      last = y;
    }
  }
  window.addEventListener("scroll", function () {
    if (!ticking) { ticking = true; window.requestAnimationFrame(onFrame); }
  }, { passive: true });
  // 키보드로 메뉴에 들어오면 보여 준다.
  h.addEventListener("focusin", function () { set(false); });
})();
