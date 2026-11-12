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
      b.addEventListener("click", function () {
        var km = parseFloat(box.getAttribute("data-km")), gain = parseFloat(box.getAttribute("data-gain"));
        L.setTrail(href, name, stateOf(href) === d[0] ? "" : d[0], isNaN(km) ? null : km, isNaN(gain) ? null : gain); paint();
      });
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
    var draw = function () {
      var list = L.trails();
      while (mine.children.length > 1) mine.removeChild(mine.lastChild);   // 제목만 남기고 다시 그린다
      mine.hidden = !list.length && !mine.getAttribute("data-open");
      if (!list.length) return;
      [["want", "가 보고 싶은 곳"], ["done", "다녀온 곳"]].forEach(function (d) {
        var items = list.filter(function (x) { return x.state === d[0]; }).reverse();
        if (!items.length) return;
        mine.appendChild(el("h3", "tp-h3", d[1] + " (" + items.length + ")"));
        if (d[0] === "done") {
          var withKm = items.filter(function (x) { return x.km > 0; }), tk = 0, tg = 0;
          withKm.forEach(function (x) { tk += x.km; tg += x.gain || 0; });
          if (withKm.length) mine.appendChild(el("p", "tp-small", "코스 " + withKm.length + "곳을 합치면 " + tk.toFixed(1) + "km를 걸었고, 누적 오르막은 " + Math.round(tg).toLocaleString("ko-KR") + "m입니다. (코스 기준, 산은 합치지 않습니다)"));
        }
        var ul = el("ul", "cp-list");
        items.forEach(function (x) {
          var li = el("li"), a = el("a", "", x.name); a.href = x.href; li.appendChild(a); li.appendChild(document.createTextNode(" "));
          var mv = el("button", "tp-btn ghost", d[0] === "want" ? "다녀왔어요로 옮기기" : "가 보고 싶어요로 옮기기"); mv.type = "button";
          mv.addEventListener("click", function () { L.setTrail(x.href, x.name, d[0] === "want" ? "done" : "want"); draw(); });
          var rm = el("button", "tp-btn ghost", "지우기"); rm.type = "button";
          rm.addEventListener("click", function () { L.setTrail(x.href, x.name, ""); draw(); });
          li.appendChild(mv); li.appendChild(document.createTextNode(" ")); li.appendChild(rm); ul.appendChild(li);
        });
        mine.appendChild(ul);
      });
      var bar = el("p"), sv = el("button", "tp-btn ghost", "백업 파일 저장"); sv.type = "button";
      sv.addEventListener("click", function () {
        try {
          var blob = new Blob([JSON.stringify({ calrankTrails: 1, items: L.trails() })], { type: "application/json" });
          var u = URL.createObjectURL(blob), a2 = document.createElement("a"); a2.href = u; a2.download = "calrank-trails.json";
          document.body.appendChild(a2); a2.click(); document.body.removeChild(a2); setTimeout(function () { URL.revokeObjectURL(u); }, 1000);
        } catch (e) {}
      });
      bar.appendChild(sv); mine.appendChild(bar);
      mine.appendChild(el("p", "tp-small", "이 목록은 이 기기의 브라우저에만 있어요. 칼랭크 서버로 보내지 않아요. 브라우저 데이터를 지우거나 다른 기기로 옮기면 사라지니, 백업 파일을 저장해 두세요."));
    };
    draw();
    var imp = document.getElementById("trImport");
    if (imp) imp.addEventListener("change", function () {
      var f = imp.files && imp.files[0]; if (!f) return;
      var r = new FileReader();
      r.onload = function () {
        try {
          var o = JSON.parse(String(r.result)), n = 0;
          (o.items || []).forEach(function (x) {
            if (x && /^(course|mountain)-[\w.-]+\.html$/.test(x.href) && (x.state === "want" || x.state === "done")) { L.setTrail(x.href, x.name, x.state); n++; }
          });
          mine.setAttribute("data-open", "1"); draw();
          var m = document.getElementById("trImportMsg"); if (m) m.textContent = n + "곳을 불러왔어요.";
        } catch (e) { var m2 = document.getElementById("trImportMsg"); if (m2) m2.textContent = "읽을 수 없는 파일이에요."; }
        imp.value = "";
      };
      r.readAsText(f);
    });
  }
})();
