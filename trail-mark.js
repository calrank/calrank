// 코스·산 페이지의 '가 보고 싶어요 / 다녀왔어요' 표시와, 허브의 '내 목록'.
// 표시는 이 기기의 브라우저에만 저장한다(calrank-local.js). 서버로 보내지 않는다.
(function () {
  "use strict";
  var L = window.CalrankLocal; if (!L || !L.trails) return;
  function el(t, c, x) { var e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; }
  function stateOf(href) { var r = L.trails().filter(function (x) { return x.href === href; })[0]; return r ? r.state : ""; }

  var box = document.getElementById("trMark");
  if (box) {
    var href = box.getAttribute("data-href"), name = box.getAttribute("data-name");
    var msg = el("p", "tp-small"); msg.setAttribute("role", "status"); msg.setAttribute("aria-live", "polite");
    var row = el("p"), btns = {};
    [["want", "가 보고 싶어요"], ["done", "다녀왔어요"]].forEach(function (d) {
      var b = el("button", "tp-btn ghost", d[1]); b.type = "button"; btns[d[0]] = b; row.appendChild(b); row.appendChild(document.createTextNode(" "));
      b.addEventListener("click", function () { L.setTrail(href, name, stateOf(href) === d[0] ? "" : d[0]); paint(); });
    });
    var paint = function () {
      var s = stateOf(href);
      Object.keys(btns).forEach(function (k) { btns[k].setAttribute("aria-pressed", s === k ? "true" : "false"); btns[k].className = "tp-btn" + (s === k ? "" : " ghost"); });
      msg.textContent = s === "want" ? "가 보고 싶은 곳에 담았어요. 트레일루트 목록에서 모아 볼 수 있어요."
        : s === "done" ? "다녀온 곳으로 표시했어요." : "표시는 이 기기에만 저장되고 서버로 보내지 않아요.";
    };
    box.appendChild(row); box.appendChild(msg); paint();
  }

  var mine = document.getElementById("trMine");
  if (mine) {
    var list = L.trails();
    if (list.length) {
      mine.hidden = false;
      [["want", "가 보고 싶은 곳"], ["done", "다녀온 곳"]].forEach(function (d) {
        var items = list.filter(function (x) { return x.state === d[0]; }).reverse();
        if (!items.length) return;
        mine.appendChild(el("h3", "tp-h3", d[1] + " (" + items.length + ")"));
        var ul = el("ul", "cp-list");
        items.forEach(function (x) { var li = el("li"), a = el("a", "", x.name); a.href = x.href; li.appendChild(a); ul.appendChild(li); });
        mine.appendChild(ul);
      });
      mine.appendChild(el("p", "tp-small", "이 목록은 이 기기의 브라우저에만 있어요. 칼랭크 서버로 보내지 않습니다."));
    }
  }
})();
