// 대회 현장 확인 — 다녀온 사람이 급수·화장실 등을 "좋았어요/아쉬웠어요"로 남기고, 처음 확인한 닉네임이 보인다.
// 로그인·닉네임이 있어야 남길 수 있고, 대회일이 지난 뒤에만 버튼이 열린다. 서버가 같은 규칙으로 다시 검사한다.
(function () {
  "use strict";
  var ASP = [["water", "급수"], ["toilet", "화장실"], ["access", "교통·주차"], ["start", "출발 혼잡"], ["marks", "코스 표시"], ["bag", "짐 보관"]];
  var MSG = { login: "로그인한 뒤 남길 수 있습니다.", nick: "닉네임을 먼저 정해 주세요(내 활동 페이지).", bad: "내용을 확인하지 못했습니다. 잠시 뒤 다시 시도해 주세요.", slow: "잠시 뒤 다시 시도해 주세요." };
  var box = document.getElementById("aspectBox"), ev = null, rows = {};
  function el(t, c, x) { var e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; }
  function ago(iso) { var d = Math.floor((Date.now() - new Date(iso)) / 864e5); return d <= 0 ? "오늘" : d + "일 전"; }
  function over() { return ev && new Date(ev.date + "T23:59:59+09:00") < new Date(); }
  function load() {
    if (!box || !ev || !window.CalrankAuth) return;
    CalrankAuth.rpc("event_aspect_summary", { p_event: ev.id }).then(function (r) {
      rows = {}; (r && !r.error && Array.isArray(r.data) ? r.data : []).forEach(function (x) { rows[x.aspect] = x; });
      paint();
    });
  }
  function send(a, ans, msgEl) {
    var u = CalrankAuth.user(); if (!u) { CalrankAuth.openSheet(); return; }
    CalrankAuth.rpc("submit_event_aspect", { p_event: ev.id, p_aspect: a, p_answer: ans, p_note: null }).then(function (r) {
      var v = r && !r.error ? r.data : "err";
      if (v === "ok") { msgEl.textContent = ""; load(); } else msgEl.textContent = MSG[v] || "저장하지 못했습니다. 잠시 뒤 다시 시도해 주세요.";
    });
  }
  function paint() {
    box.innerHTML = "";
    var ul = el("ul", "asp-list"); box.appendChild(ul);
    var msg = el("p", "asp-msg"); msg.setAttribute("role", "status");
    ASP.forEach(function (a) {
      var r = rows[a[0]] || {}, li = el("li");
      var head = el("div", "asp-head"); head.appendChild(el("b", "", a[1]));
      head.appendChild(el("span", "asp-n", r.good_n || r.bad_n ? "좋았어요 " + (r.good_n || 0) + " · 아쉬웠어요 " + (r.bad_n || 0) : "아직 확인한 사람이 없습니다"));
      li.appendChild(head);
      if (r.first_name) li.appendChild(el("p", "asp-by", "처음 확인: " + r.first_name + " · 마지막 확인 " + ago(r.last_at)));
      if (over()) {
        var b = el("div", "asp-btns");
        [["good", "좋았어요"], ["bad", "아쉬웠어요"]].forEach(function (o) {
          var x = el("button", "asp-btn" + (r.mine === o[0] ? " on" : ""), o[1]); x.type = "button"; x.setAttribute("aria-pressed", r.mine === o[0] ? "true" : "false");
          x.onclick = function () { send(a[0], o[0], msg); }; b.appendChild(x);
        });
        li.appendChild(b);
      }
      ul.appendChild(li);
    });
    box.appendChild(msg);
    box.appendChild(el("p", "asp-note", over() ? "다녀오신 분만 남겨 주세요. 남긴 확인은 닉네임과 함께 공개되고, 내 활동에서 지울 수 있습니다." : "대회가 끝난 뒤 다녀온 분이 남길 수 있습니다."));
  }
  function start() { ev = window.__calrankEvAsp || null; if (ev) load(); }
  window.addEventListener("calrank:event", start);
  window.addEventListener("calrank:auth", function () { setTimeout(load, 100); });
  var t = 0, w = setInterval(function () { if ((window.CalrankAuth && window.__calrankEvAsp) || ++t > 60) { clearInterval(w); start(); } }, 100);
})();
