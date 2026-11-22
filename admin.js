// 운영 검토 — 운영자 계정만 쓸 수 있다. 권한은 서버(is_admin)가 정하고, 이 화면은 보여 주기만 한다.
(function () {
  "use strict";
  var body = document.getElementById("adBody");
  var PK = { toilet: "화장실", water: "식수·샘터", shelter: "쉼터", view: "조망", danger: "위험 구간" };
  var ST = { live: "표시 중", hidden: "자동 가림", removed: "제거됨" };
  var filter = "";
  function el(t, c, x) { var e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; }
  function card() { var c = el("div", "me-card"); body.appendChild(c); return c; }
  function ago(iso) { var d = Math.floor((Date.now() - new Date(iso)) / 864e5); return d <= 0 ? "오늘" : d + "일 전"; }
  function pageOf(id) { return /^mt-/.test(id) ? "mountain-" + id.slice(3) + ".html" : "course-" + id + ".html"; }
  function note(msg) { body.innerHTML = ""; var c = card(); c.appendChild(el("p", "me-note", msg)); return c; }
  function rows(r) { return r && !r.error && Array.isArray(r.data) ? r.data : null; }

  function list() {
    Promise.all([CalrankAuth.rpc("admin_poi_list", { p_status: filter || null }), CalrankAuth.rpc("admin_nick_reports")]).then(function (v) {
      var pois = rows(v[0]), reps = rows(v[1]);
      if (!pois) return note("목록을 불러오지 못했습니다. 잠시 뒤 다시 열어 주세요.");
      body.innerHTML = "";
      var f = card(), bar = el("div"); bar.style.cssText = "display:flex;flex-wrap:wrap;gap:8px";
      [["", "전체"], ["live", "표시 중"], ["hidden", "자동 가림"], ["removed", "제거됨"]].forEach(function (o) {
        var b = el("button", "me-btn", o[1]); b.type = "button"; if (filter !== o[0]) { b.style.background = "transparent"; b.style.border = "1px solid currentColor"; b.style.color = "inherit"; }
        b.onclick = function () { filter = o[0]; list(); }; bar.appendChild(b);
      });
      f.appendChild(el("p", "me-note", "장소 제보 " + pois.length + "건" + (pois.length === 200 ? " (최근 200건)" : ""))); f.appendChild(bar);
      var c = card(), ul = el("ul", "me-list"); c.appendChild(ul);
      if (!pois.length) c.appendChild(el("p", "me-note", "해당하는 제보가 없습니다."));
      pois.forEach(function (r) {
        var li = el("li");
        li.appendChild(el("span", "me-tag" + (r.status === "live" ? "" : " no"), ST[r.status] || r.status));
        var a = el("a", "", (PK[r.kind] || r.kind) + " · " + r.route_id + (r.note ? " · " + r.note : "")); a.href = pageOf(r.route_id); a.target = "_blank"; a.rel = "noopener"; li.appendChild(a);
        li.appendChild(el("span", "me-note", (r.nick || "닉네임 없음") + " · 있어요 " + r.yes_u + " / 없어요 " + r.no_u + " · " + ago(r.created_at)));
        var mp = el("a", "", "지도"); mp.href = "https://www.openstreetmap.org/?mlat=" + r.lat + "&mlon=" + r.lon + "#map=18/" + r.lat + "/" + r.lon; mp.target = "_blank"; mp.rel = "noopener"; li.appendChild(mp);
        var nx = r.status === "removed" ? "live" : "removed", b = el("button", "me-btn", nx === "live" ? "복구" : "제거"); b.type = "button"; b.style.marginLeft = "auto";
        b.onclick = function () { b.disabled = true; CalrankAuth.rpc("admin_poi_set", { p_id: r.id, p_status: nx }).then(function (x) { if (x && !x.error && x.data === "ok") list(); else { b.disabled = false; b.textContent = "실패, 다시 시도"; } }); };
        li.appendChild(b); ul.appendChild(li);
      });
      var n = card(); n.appendChild(el("p", "me-note", "닉네임 신고 (서로 다른 신고자 3명 이상이면 지점에서 닉네임이 가려집니다)"));
      var nl = el("ul", "me-list"); n.appendChild(nl);
      if (!reps || !reps.length) n.appendChild(el("p", "me-note", "신고가 없습니다."));
      (reps || []).forEach(function (r) { var li = el("li"); li.appendChild(el("span", "me-tag" + (r.reporters >= 3 ? " no" : ""), r.reporters + "명")); li.appendChild(el("span", "", r.nick || "닉네임 없음")); li.appendChild(el("span", "me-date", ago(r.last_at))); nl.appendChild(li); });
    });
  }

  function start() {
    var u = CalrankAuth.user();
    if (!u) { var c = note("로그인한 운영자 계정으로 열어 주세요."); var b = el("button", "me-btn", "로그인"); b.type = "button"; b.style.marginTop = "14px"; b.onclick = function () { CalrankAuth.openSheet(); }; c.appendChild(b); return; }
    CalrankAuth.rpc("is_admin").then(function (r) { if (r && !r.error && r.data === true) list(); else note("운영자 권한이 없는 계정입니다."); });
  }
  var t = 0, w = setInterval(function () { if (window.CalrankAuth || ++t > 50) { clearInterval(w); if (window.CalrankAuth) start(); else body.textContent = "불러오지 못했습니다. 새로고침해 주세요."; } }, 100);
  window.addEventListener("calrank:auth", function () { setTimeout(start, 100); });
})();
