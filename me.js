// 내 활동 — 내가 확인한 시설 지점과 닉네임. 로그인한 본인 것만 서버에서 돌려준다(my_poi_checks).
(function () {
  "use strict";
  var body = document.getElementById("meBody");
  var KIND = { TOILET: "화장실", BENCH: "벤치", DRINK: "식수대", SPRING: "약수터·샘터", SHELTER: "대피소", VIEW: "전망" };
  function el(t, c, x) { var e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; }
  function card() { var c = el("div", "me-card"); body.appendChild(c); return c; }
  function km(m) { return m >= 1000 ? (m / 1000).toFixed(1) + "km" : m + "m"; }
  function ago(iso) { var d = Math.floor((Date.now() - new Date(iso)) / 864e5); return d <= 0 ? "오늘" : d + "일 전"; }
  function out() {
    body.innerHTML = ""; var c = card();
    c.appendChild(el("h2", "", "로그인이 필요합니다"));
    c.appendChild(el("p", "me-note", "로그인하면 내가 확인한 지점과 닉네임이 여기에 모입니다. 로그인 없이 누른 확인은 이 기기에만 남아 여기에 보이지 않습니다."));
    var b = el("button", "me-btn", "로그인·가입하기"); b.type = "button"; b.style.marginTop = "14px"; b.onclick = function () { CalrankAuth.openSheet(); }; c.appendChild(b);
  }
  function pageOf(id) { return /^mt-/.test(id) ? "/mountain-" + id.slice(3) + ".html" : "/course-" + id + ".html"; }
  function titles(ids, done) {
    var out = {}, list = ids.slice(0, 15), n = list.length; if (!n) return done(out);
    list.forEach(function (id) {
      fetch(pageOf(id)).then(function (r) { return r.ok ? r.text() : ""; }).then(function (h) {
        var m = /<h1[^>]*>([\s\S]*?)<\/h1>/.exec(h); if (m) out[id] = m[1].replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim().split(" 난이도")[0];
      }).catch(function () {}).then(function () { if (--n === 0) done(out); });
    });
  }
  function show() {
    var u = CalrankAuth.user(); if (!u) return out();
    body.innerHTML = "";
    Promise.all([CalrankAuth.nick(), CalrankAuth.rpc("my_poi_checks"), CalrankAuth.rpc("my_impact")]).then(function (v) {
      var nick = v[0], rows = v[1] && !v[1].error && Array.isArray(v[1].data) ? v[1].data : [], imp = v[2] && !v[2].error && Array.isArray(v[2].data) ? v[2].data : [];
      body.innerHTML = "";
      var a = card(); a.appendChild(el("p", "me-note", "닉네임"));
      a.appendChild(el("p", "me-nick", nick || "정하지 않음 (익명으로 남습니다)"));
      var nb = el("button", "me-btn", nick ? "닉네임 바꾸기" : "닉네임 정하기"); nb.type = "button"; nb.style.marginTop = "12px"; nb.onclick = function () { CalrankAuth.openSheet(); }; a.appendChild(nb);
      var s = card(); s.appendChild(el("p", "me-note", "내가 확인한 지점")); s.appendChild(el("p", "me-num", rows.length + "곳"));
      s.appendChild(el("p", "me-note", rows.length ? "다른 사람이 코스·산 지도에서 이 확인을 볼 수 있습니다." : "코스·산 페이지에서 지도의 내 위치(GPS)를 켜고 시설 근처를 지나면 \"있어요/없어요\"를 한 번 눌러 확인을 남길 수 있습니다."));
      if (!rows.length) return;
      var total = 0; imp.forEach(function (x) { total += +x.visitors || 0; });
      var ic = card(); ic.appendChild(el("p", "me-note", "내 확인이 닿은 사람")); ic.appendChild(el("p", "me-num", total > 0 ? total + "명" : "아직 없음"));
      ic.appendChild(el("p", "me-note", total > 0 ? "내가 처음 확인한 날 이후, 그 코스·산 페이지를 방문한 사람 수의 합입니다. 지도에서 이 지점을 직접 본 사람 수는 아닙니다." : "그 페이지를 연 사람이 생기면 여기에 나타납니다. 집계는 하루 단위로 쌓입니다."));
      var ids = {}; rows.forEach(function (r) { ids[r.route_id] = 1; });
      var l = card(); l.appendChild(el("h2", "", "최근 확인")); var ul = el("ul", "me-list"); l.appendChild(ul);
      titles(Object.keys(ids), function (T) {
        rows.slice(0, 100).forEach(function (r) {
          var li = el("li"), m = /^([A-Z]+):(\d+)$/.exec(r.poi_key), mk = /^([A-Z]+):\d+-\d+$/.exec(r.poi_key);
          li.appendChild(el("span", "me-tag" + (r.answer === "no" ? " no" : ""), r.answer === "yes" ? "있어요" : "없어요"));
          var a2 = el("a", "", (T[r.route_id] || r.route_id) + " · " + (m ? (KIND[m[1]] || "시설") + " " + km(+m[2]) + " 지점" : mk ? (KIND[mk[1]] || "시설") + " 지점" : "시설")); a2.href = pageOf(r.route_id).slice(1); li.appendChild(a2);
          li.appendChild(el("span", "me-date", ago(r.checked_at))); ul.appendChild(li);
        });
      });
    });
  }
  var t = 0, w = setInterval(function () { if (window.CalrankAuth || ++t > 50) { clearInterval(w); if (window.CalrankAuth) show(); else body.textContent = "불러오지 못했습니다. 새로고침해 주세요."; } }, 100);
  window.addEventListener("calrank:nick", show); window.addEventListener("calrank:auth", function () { setTimeout(show, 100); });
})();
