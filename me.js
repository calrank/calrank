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
    Promise.all([CalrankAuth.nick(), CalrankAuth.rpc("my_poi_checks"), CalrankAuth.rpc("my_impact"), CalrankAuth.rpc("my_poi_users"), CalrankAuth.rpc("my_event_aspects"), CalrankAuth.rpc("my_gear_uses")]).then(function (v) {
      var nick = v[0], rows = v[1] && !v[1].error && Array.isArray(v[1].data) ? v[1].data : [], imp = v[2] && !v[2].error && Array.isArray(v[2].data) ? v[2].data : [], mine = v[3] && !v[3].error && Array.isArray(v[3].data) ? v[3].data : [], ea = v[4] && !v[4].error && Array.isArray(v[4].data) ? v[4].data : [], gu = v[5] && !v[5].error && Array.isArray(v[5].data) ? v[5].data : [];
      body.innerHTML = "";
      var a = card(); a.appendChild(el("p", "me-note", "닉네임"));
      a.appendChild(el("p", "me-nick", nick || "정하지 않음 (익명으로 남습니다)"));
      var nb = el("button", "me-btn", nick ? "닉네임 바꾸기" : "닉네임 정하기"); nb.type = "button"; nb.style.marginTop = "12px"; nb.onclick = function () { CalrankAuth.openSheet(); }; a.appendChild(nb);
      var s = card(); s.appendChild(el("p", "me-note", "내가 확인한 지점")); s.appendChild(el("p", "me-num", rows.length + "곳"));
      s.appendChild(el("p", "me-note", rows.length ? "다른 사람이 코스·산 지도에서 이 확인을 볼 수 있습니다." : "코스·산 페이지에서 지도의 내 위치(GPS)를 켜고 시설 근처를 지나면 \"있어요/없어요\"를 한 번 눌러 확인을 남길 수 있습니다."));
      var pc = card(); pc.appendChild(el("p", "me-note", "내가 제보한 장소")); pc.appendChild(el("p", "me-num", mine.length + "곳"));
      pc.appendChild(el("p", "me-note", mine.length ? "제보한 닉네임이 장소에 남습니다. 필요 없으면 삭제할 수 있습니다." : "코스·산 지도에서 내 위치(GPS)를 켜고 ‘장소 제보’를 누르면, 지도에 없는 화장실·식수·쉼터·조망·위험 구간을 직접 올릴 수 있습니다."));
      if (mine.length) {
        var pul = el("ul", "me-list"); pc.appendChild(pul);
        var PK = { toilet: "화장실", water: "식수·샘터", shelter: "쉼터", view: "조망", danger: "위험 구간" };
        titles(Object.keys(mine.reduce(function (o, r) { o[r.route_id] = 1; return o; }, {})), function (T2) {
          mine.forEach(function (r) {
            var li = el("li"); li.appendChild(el("span", "me-tag" + (r.status === "hidden" ? " no" : ""), r.status === "hidden" ? "가려짐" : "표시 중"));
            var a3 = el("a", "", (T2[r.route_id] || r.route_id) + " · " + (PK[r.kind] || "장소") + (r.note ? " · " + r.note : "")); a3.href = pageOf(r.route_id).slice(1); li.appendChild(a3);
            li.appendChild(el("span", "me-date", ago(r.created_at)));
            var db = el("button", "me-btn", "삭제"); db.type = "button"; db.style.marginLeft = "8px"; db.setAttribute("aria-label", "이 제보 삭제");
            db.onclick = function () { db.disabled = true; CalrankAuth.rpc("delete_poi_user", { p_id: r.id }).then(function (x) { if (x && !x.error && x.data === "ok") li.remove(); else db.disabled = false; }, function () { db.disabled = false; }); };
            li.appendChild(db); pul.appendChild(li);
          });
        });
      }
      if (ea.length) {
        var ec = card(); ec.appendChild(el("p", "me-note", "내가 남긴 대회 현장 확인")); ec.appendChild(el("p", "me-num", ea.length + "건"));
        ec.appendChild(el("p", "me-note", "대회 페이지에 닉네임과 함께 보입니다. 필요 없으면 삭제할 수 있습니다."));
        var EA = { water: "급수", toilet: "화장실", access: "교통·주차", start: "출발 혼잡", marks: "코스 표시", bag: "짐 보관" }, eul = el("ul", "me-list"); ec.appendChild(eul);
        ea.forEach(function (r) {
          var li = el("li"); li.appendChild(el("span", "me-tag" + (r.answer === "bad" ? " no" : ""), r.answer === "good" ? "좋았어요" : "아쉬웠어요"));
          var nm = r.event_id.replace(/^[a-z]+-/, "").replace(/-\d{4}-\d{2}-\d{2}$/, "").replace(/-/g, " ");
          var ea3 = el("a", "", nm + " · " + (EA[r.aspect] || "항목")); ea3.href = "event.html?id=" + encodeURIComponent(r.event_id); li.appendChild(ea3);
          li.appendChild(el("span", "me-date", ago(r.updated_at)));
          var eb = el("button", "me-btn", "삭제"); eb.type = "button"; eb.style.marginLeft = "8px"; eb.setAttribute("aria-label", "이 현장 확인 삭제");
          eb.onclick = function () { eb.disabled = true; CalrankAuth.rpc("delete_event_aspect", { p_event: r.event_id, p_aspect: r.aspect }).then(function (x) { if (x && !x.error && x.data === "ok") li.remove(); else eb.disabled = false; }); };
          li.appendChild(eb); eul.appendChild(li);
        });
      }
      if (gu.length) {
        var gc = card(); gc.appendChild(el("p", "me-note", "내가 써 본 장비 확인")); gc.appendChild(el("p", "me-num", gu.length + "건"));
        gc.appendChild(el("p", "me-note", "기어 판정 페이지에 닉네임과 함께 보입니다. 필요 없으면 삭제할 수 있습니다."));
        var gul = el("ul", "me-list"); gc.appendChild(gul);
        gu.forEach(function (r) {
          var li = el("li"); li.appendChild(el("span", "me-tag" + (r.answer === "bad" ? " no" : ""), r.answer === "good" ? "효과 있었어요" : "별로였어요"));
          var ga = el("a", "", r.gear_id.replace(/^gear-/, "").replace(/-/g, " ")); ga.href = r.gear_id + ".html"; li.appendChild(ga);
          li.appendChild(el("span", "me-date", ago(r.updated_at)));
          var gb = el("button", "me-btn", "삭제"); gb.type = "button"; gb.style.marginLeft = "8px"; gb.setAttribute("aria-label", "이 장비 확인 삭제");
          gb.onclick = function () { gb.disabled = true; CalrankAuth.rpc("delete_gear_use", { p_gear: r.gear_id }).then(function (x) { if (x && !x.error && x.data === "ok") li.remove(); else gb.disabled = false; }); };
          li.appendChild(gb); gul.appendChild(li);
        });
      }
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
