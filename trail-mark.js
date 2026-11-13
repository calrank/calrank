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
    box.appendChild(row); box.appendChild(msg); var paint0 = paint; paint = function () { paint0(); if (typeof drawProgs === "function") drawProgs(); }; paint();

    // 오프라인 저장: 연결이 약한 산에 들어가기 전에 이 페이지와 쓰는 파일을 서비스 워커 저장소에 미리 받아 둔다.
    // 지도 타일 같은 외부 이미지는 저장되지 않고, 글·숫자·경사 단면도는 저장된다.
    if ("caches" in window && "serviceWorker" in navigator) {
      var ob = el("button", "tp-btn ghost", "오프라인으로 저장"); ob.type = "button";
      var om = el("p", "tp-small"); om.setAttribute("role", "status"); om.setAttribute("aria-live", "polite");
      var PAGES = "cr-v1-pages", ASSETS = "cr-v1-assets";
      caches.open(PAGES).then(function (c) { return c.match(location.pathname); }).then(function (hit) {
        if (hit) { ob.textContent = "오프라인 저장됨 · 다시 저장"; om.textContent = "연결이 없어도 이 페이지를 열 수 있어요."; }
      }).catch(function () {});
      ob.addEventListener("click", function () {
        ob.disabled = true; om.textContent = "저장하는 중…";
        var urls = [].slice.call(document.querySelectorAll('link[rel="stylesheet"][href], script[src], img[src]'))
          .map(function (n) { return n.href || n.src; }).filter(function (u) { return u.indexOf(location.origin) === 0; });
        Promise.all([caches.open(PAGES), caches.open(ASSETS)]).then(function (cs) {
          return fetch(location.pathname, { cache: "reload" }).then(function (r) {
            if (!r.ok) throw new Error("page");
            return cs[0].put(location.pathname, r);
          }).then(function () {
            return Promise.all(urls.map(function (u) { return cs[1].add(u).catch(function () {}); }));
          });
        }).then(function () {
          ob.disabled = false; ob.textContent = "오프라인 저장됨 · 다시 저장"; om.textContent = "저장했어요. 연결이 없어도 이 페이지를 열 수 있어요. (지도 타일은 저장되지 않아요)";
        }).catch(function () { ob.disabled = false; om.textContent = "저장하지 못했어요. 연결을 확인하고 다시 눌러 주세요."; });
      });
      var orow = el("p"); orow.appendChild(ob); box.appendChild(orow); box.appendChild(om);
    }
  }

  // 카드 한 장을 공유하거나 저장한다. 공유창이 없는 기기에서는 파일로 내려받는다.
  function shareCard(data, fname, btn) {
    btn.disabled = true;
    var ready = window.CalrankTrailCard ? Promise.resolve() : new Promise(function (ok, no) {
      var sc = document.createElement("script"); sc.src = "trail-card.js"; sc.onload = ok; sc.onerror = no; document.head.appendChild(sc);
    });
    ready.then(function () { return window.CalrankTrailCard.build(data); }).then(function (blob) {
      var f = new File([blob], fname, { type: "image/png" });
      if (navigator.canShare && navigator.canShare({ files: [f] })) return navigator.share({ files: [f] }).catch(function () {});
      var u = URL.createObjectURL(blob), a3 = document.createElement("a"); a3.href = u; a3.download = fname;
      document.body.appendChild(a3); a3.click(); document.body.removeChild(a3); setTimeout(function () { URL.revokeObjectURL(u); }, 1000);
    }).catch(function () {}).then(function () { btn.disabled = false; });
  }

  // 길 하나를 얼마나 걸었는지. 칸 수는 페이지가 적어 두고, 채우는 건 이 기기 안의 '다녀왔어요' 표시다.
  var progs = [].slice.call(document.querySelectorAll(".tr-prog"));
  var drawProgs = function () {
    var done = {}; L.trails().forEach(function (x) { if (x.state === "done") done[x.href] = 1; });
    progs.forEach(function (sec) {
      var hs = (sec.getAttribute("data-hrefs") || "").split(",").filter(Boolean);
      var kms = (sec.getAttribute("data-km") || "").split(",").map(parseFloat);
      var n = hs.length; if (!n) return;
      var d = 0, dk = 0, tk = 0;
      hs.forEach(function (h, i) { var k = kms[i] || 0; tk += k; if (done[h]) { d++; dk += k; } });
      var name = sec.getAttribute("data-name"), link = sec.getAttribute("data-link");
      var box = sec.querySelector(".tr-prog-b"); if (!box) return;
      box.textContent = "";
      var pct = Math.round(d / n * 100);
      var big = el("p", "tr-prog-n"); big.appendChild(el("b", "", d + " / " + n)); big.appendChild(document.createTextNode(" 코스 다녀왔어요"));
      box.appendChild(big);
      var bar = el("div", "tr-prog-bar"); bar.setAttribute("role", "progressbar"); bar.setAttribute("aria-valuemin", "0"); bar.setAttribute("aria-valuemax", String(n)); bar.setAttribute("aria-valuenow", String(d)); bar.setAttribute("aria-label", name + " 완주 진행");
      var fill = el("i"); fill.style.width = pct + "%"; bar.appendChild(fill); box.appendChild(bar);
      var msg = d === n ? name + "을(를) 모두 다녀왔어요. 완주를 축하드려요."
        : d === 0 ? "코스 페이지에서 '다녀왔어요'를 누르면 이곳이 채워져요."
        : "걸은 거리 " + dk.toFixed(1) + "km · 남은 코스 " + (n - d) + "개 (" + (tk - dk).toFixed(1) + "km)";
      box.appendChild(el("p", "tp-small", msg));
      if (d > 0) {
        var gains = (sec.getAttribute("data-gain") || "").split(",").map(parseFloat);
        var names = (sec.getAttribute("data-names") || "").split("|");
        var dg = 0, dn2 = [];
        hs.forEach(function (h, i) { if (done[h]) { dg += gains[i] || 0; dn2.push(names[i]); } });
        var cbtn = el("button", "tp-btn ghost", "완주판 카드 저장"); cbtn.type = "button";
        cbtn.addEventListener("click", function () {
          shareCard({ title: name + " 완주판", n: d, total: n, km: dk, gain: dg, date: L.today(), names: dn2.reverse() }, "calrank-" + name + ".png", cbtn);
        });
        var cp = el("p"); cp.appendChild(cbtn); box.appendChild(cp);
      }
      if (link && location.pathname.split("/").pop() !== link) { var a = el("a", "", name + " 코스 모음 보기"); a.href = link; var pp = el("p", "tp-small"); pp.appendChild(a); box.appendChild(pp); }
    });
  };
  if (progs.length) drawProgs();

  var mine = document.getElementById("trMine");
  if (mine) {
    var draw = function () {
      var list = L.trails();
      while (mine.children.length > 1) mine.removeChild(mine.lastChild);   // 제목만 남기고 다시 그린다
      mine.hidden = !list.length && !mine.getAttribute("data-open");
      if (!list.length) return;
      var done = list.filter(function (x) { return x.state === "done"; });
      var wk = 0, wg = 0; done.forEach(function (x) { wk += x.km || 0; wg += x.gain || 0; });
      mine.appendChild(el("p", "mn-lead", done.length ? "걸어온 길이 차곡차곡 쌓이고 있어요." : "가 보고 싶은 곳을 모아 두었어요. 다녀오면 이곳으로 옮겨 주세요."));
      if (done.length) {
        var st = el("div", "mn-stats");
        [[String(done.length), "다녀온 곳"], [wk > 0 ? wk.toFixed(1) : "–", "km (코스)"], [wg > 0 ? Math.round(wg).toLocaleString("ko-KR") : "–", "m 오르막"]].forEach(function (t) {
          var c = el("div", "mn-stat"); c.appendChild(el("b", "", t[0])); c.appendChild(el("span", "", t[1])); st.appendChild(c);
        });
        mine.appendChild(st);
      }
      [["done", "다녀온 곳", "emoji/footprints.svg"], ["want", "가 보고 싶은 곳", "emoji/round-pushpin.svg"]].forEach(function (d) {
        var items = list.filter(function (x) { return x.state === d[0]; }).reverse();
        if (!items.length) return;
        var h = el("h3", "mn-h"); var im = el("img"); im.src = d[2]; im.alt = ""; im.width = 22; im.height = 22; h.appendChild(im);
        h.appendChild(document.createTextNode(d[1])); h.appendChild(el("span", "mn-n", String(items.length))); mine.appendChild(h);
        var ul = el("ul", "mn-list");
        items.forEach(function (x) {
          var li = el("li", "mn-item"), a = el("a", "mn-name", x.name); a.href = x.href; li.appendChild(a);
          var meta = [];
          if (x.km > 0) meta.push(x.km.toFixed(1) + "km");
          if (x.gain > 0) meta.push("오르막 " + Math.round(x.gain).toLocaleString("ko-KR") + "m");
          if (meta.length) li.appendChild(el("span", "mn-meta", meta.join(" · ")));
          var acts = el("div", "mn-acts");
          var mv = el("button", "mn-act", d[0] === "want" ? "다녀왔어요" : "다시 가고 싶어요"); mv.type = "button";
          mv.addEventListener("click", function () { L.setTrail(x.href, x.name, d[0] === "want" ? "done" : "want", x.km, x.gain); draw(); });
          var rm = el("button", "mn-act mn-del", "지우기"); rm.type = "button"; rm.setAttribute("aria-label", x.name + " 지우기");
          rm.addEventListener("click", function () { L.setTrail(x.href, x.name, ""); draw(); });
          acts.appendChild(mv); acts.appendChild(rm); li.appendChild(acts); ul.appendChild(li);
        });
        mine.appendChild(ul);
      });
      var bar = el("div", "mn-tools"), sv = el("button", "tp-btn ghost", "백업 파일 저장"); sv.type = "button";
      sv.addEventListener("click", function () {
        try {
          var blob = new Blob([JSON.stringify({ calrankTrails: 1, items: L.trails() })], { type: "application/json" });
          var u = URL.createObjectURL(blob), a2 = document.createElement("a"); a2.href = u; a2.download = "calrank-trails.json";
          document.body.appendChild(a2); a2.click(); document.body.removeChild(a2); setTimeout(function () { URL.revokeObjectURL(u); }, 1000);
        } catch (e) {}
      });
      var dn = done;
      if (dn.length) {
        var cb = el("button", "tp-btn", "다녀온 곳 카드 저장"); cb.type = "button";
        cb.addEventListener("click", function () {
          cb.disabled = true;
          var go = function () {
            var km = 0, gn = 0; dn.forEach(function (x) { km += x.km || 0; gn += x.gain || 0; });
            return window.CalrankTrailCard.build({ n: dn.length, km: km, gain: gn, date: L.today(), names: dn.slice().reverse().map(function (x) { return x.name; }) });
          };
          var ready = window.CalrankTrailCard ? Promise.resolve() : new Promise(function (ok, no) {
            var sc = document.createElement("script"); sc.src = "trail-card.js"; sc.onload = ok; sc.onerror = no; document.head.appendChild(sc);
          });
          ready.then(go).then(function (blob) {
            var f = new File([blob], "calrank-trails.png", { type: "image/png" });
            if (navigator.canShare && navigator.canShare({ files: [f] })) return navigator.share({ files: [f] }).catch(function () {});
            var u = URL.createObjectURL(blob), a3 = document.createElement("a"); a3.href = u; a3.download = "calrank-trails.png";
            document.body.appendChild(a3); a3.click(); document.body.removeChild(a3); setTimeout(function () { URL.revokeObjectURL(u); }, 1000);
          }).catch(function () {}).then(function () { cb.disabled = false; });
        });
        bar.appendChild(cb);
      }
      bar.appendChild(sv);
      mine.appendChild(bar);
      mine.appendChild(el("p", "mn-foot", "이 목록은 이 기기의 브라우저에만 있고, 칼랭크 서버로 보내지 않아요. 브라우저 데이터를 지우거나 기기를 바꾸면 사라지니 백업 파일을 한 번 저장해 두세요."));
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
