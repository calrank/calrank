// 대회 현장 확인 — 다녀온 사람이 급수·화장실 등을 "좋았어요/아쉬웠어요"로 남기고, 처음 확인한 닉네임이 보인다.
// 로그인·닉네임이 있어야 남길 수 있고, 대회일이 지난 뒤에만 버튼이 열린다. 서버가 같은 규칙으로 다시 검사한다.
// 남긴 직후에는 고마움·내 닉네임으로 남았다는 확인을 보여 주고, 로그인·닉네임이 막혀 있을 때 고른 답은 이 페이지 안(메모리)에만 두었다가 끝나면 자동으로 남긴다.
(function () {
  "use strict";
  var ASP = [["water", "급수"], ["toilet", "화장실"], ["access", "교통·주차"], ["start", "출발 혼잡"], ["marks", "코스 표시"], ["bag", "짐 보관"]];
  var MSG = { login: "로그인한 뒤 남길 수 있습니다.", nick: "닉네임을 먼저 정해 주세요(내 활동 페이지).", bad: "내용을 확인하지 못했습니다. 잠시 뒤 다시 시도해 주세요.", slow: "잠시 뒤 다시 시도해 주세요." };
  var box = document.getElementById("aspectBox"), ev = null, rows = {}, pending = null, thanks = null, busy = false;
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
  function mark(s) { try { if (typeof window.calrankEvt === "function") window.calrankEvt("step", s); } catch (e) { /* 무시 */ } }
  function say(x) { var p = box.querySelector(".asp-msg"); if (p) p.textContent = x; }
  function name(a) { for (var i = 0; i < ASP.length; i++) if (ASP[i][0] === a) return ASP[i][1]; return a; }
  function send(a, ans) {
    if (busy) return;
    if (!CalrankAuth.user()) { pending = [a, ans]; say("로그인하면 방금 고른 답이 바로 남겨집니다."); mark("ea-login"); CalrankAuth.openSheet(); return; }
    busy = true; say("남기는 중…");
    CalrankAuth.rpc("submit_event_aspect", { p_event: ev.id, p_aspect: a, p_answer: ans, p_note: null }).then(function (r) {
      busy = false; var v = r && !r.error ? r.data : "err";
      if (v === "ok") {
        pending = null; mark("ea-submit");
        CalrankAuth.nick().then(function (nm) { thanks = { a: a, ans: ans, nick: nm || "" }; load(); });
      } else if (v === "login") { pending = [a, ans]; say("로그인하면 방금 고른 답이 바로 남겨집니다."); CalrankAuth.openSheet(); }
      else if (v === "nick") { pending = [a, ans]; say("닉네임을 정하면 방금 고른 답이 바로 남겨집니다. 열린 창에서 정해 주세요."); mark("ea-nick"); CalrankAuth.openSheet(); }
      else say(MSG[v] || "저장하지 못했습니다. 잠시 뒤 다시 시도해 주세요.");
    });
  }
  function resume() { if (pending && CalrankAuth.user()) { var p = pending; pending = null; send(p[0], p[1]); } else load(); }
  function paint() {
    box.innerHTML = "";
    var total = 0; ASP.forEach(function (a) { var r = rows[a[0]] || {}; total += (r.good_n || 0) + (r.bad_n || 0); });
    box.appendChild(el("p", "asp-why", over() ? (total ? "다녀온 분 " + total + "건의 확인이 모였습니다. 다음에 이 대회에 나가는 분께 보입니다." : "아직 확인이 없습니다. 첫 확인을 남기면 닉네임이 '처음 확인'으로 표시되어 다음 참가자에게 도움이 됩니다.") : "대회가 끝나면, 다녀온 분의 현장 확인이 이곳에 모입니다."));
    if (thanks) {
      var ok = el("div", "asp-thanks"); ok.setAttribute("role", "status");
      ok.appendChild(el("p", "asp-thanks-t", "고맙습니다. " + (thanks.nick ? thanks.nick + " 님의 " : "") + name(thanks.a) + " 확인이 남았습니다."));
      ok.appendChild(el("p", "asp-by", "바꾸려면 다른 버튼을 누르세요. 지우는 것은 내 활동에서 할 수 있습니다. 다른 항목도 남겨 주시면 더 도움이 됩니다."));
      box.appendChild(ok);
    }
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
          x.onclick = function () { thanks = null; send(a[0], o[0]); }; b.appendChild(x);
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
  window.addEventListener("calrank:auth", function () { setTimeout(function () { if (window.CalrankAuth) resume(); }, 100); });
  window.addEventListener("calrank:nick", function () { setTimeout(function () { if (window.CalrankAuth) resume(); }, 300); });
  var t = 0, w = setInterval(function () { if ((window.CalrankAuth && window.__calrankEvAsp) || ++t > 60) { clearInterval(w); start(); } }, 100);
})();
