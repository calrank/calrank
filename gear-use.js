// 기어 "써 봤어요" — 장비를 써 본 사람이 효과를 확인하고, 처음 남긴 닉네임이 보인다.
// 로그인·닉네임이 필요하고, 페이지마다 한 사람이 한 번(바꿀 수 있음) 남긴다. 서버가 같은 규칙으로 다시 검사한다.
// 남긴 직후에는 고마움·내 닉네임으로 남았다는 확인·바꾸는 방법·다음 행동을 바로 보여 준다.
// 로그인·닉네임이 막혀 있을 때 고른 답은 이 페이지 안(메모리)에만 기억해 두었다가, 끝나면 자동으로 남긴다.
(function () {
  "use strict";
  var m = /\/(gear-[a-z0-9-]+)\.html$/.exec(location.pathname); if (!m) return;
  var id = m[1], main = document.querySelector("main"); if (!main) return;
  var MSG = { bad: "저장하지 못했습니다. 잠시 뒤 다시 시도해 주세요.", slow: "잠시 뒤 다시 시도해 주세요." };
  var PER = [[1, "한 달 미만"], [2, "1~6개월"], [3, "6개월 이상"]];
  var period = null, pending = null, done = null, busy = false, last = null;
  var sec = document.createElement("section"); sec.className = "gu-sec"; sec.setAttribute("aria-live", "polite"); main.appendChild(sec);
  function el(t, c, x) { var e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; }
  function ago(iso) { var d = Math.floor((Date.now() - new Date(iso)) / 864e5); return d <= 0 ? "오늘" : d + "일 전"; }
  function mark(s) { try { if (typeof window.calrankEvt === "function") window.calrankEvt("step", s); } catch (e) { /* 무시 */ } }
  function load() { CalrankAuth.rpc("gear_use_summary", { p_gear: id }).then(function (r) { var d = r && !r.error && Array.isArray(r.data) ? r.data[0] : null; last = d || { good_n: 0, bad_n: 0, long_n: 0 }; paint(last); }); }
  function say(t) { var p = sec.querySelector(".gu-msg"); if (p) p.textContent = t; }
  function send(ans) {
    if (busy) return;
    if (!CalrankAuth.user()) { pending = ans; say("로그인하면 방금 고른 답이 바로 남겨집니다."); mark("gu-login"); CalrankAuth.openSheet(); return; }
    busy = true; say("남기는 중…");
    CalrankAuth.rpc("submit_gear_use", { p_gear: id, p_answer: ans, p_period: period }).then(function (r) {
      busy = false; var v = r && !r.error ? r.data : "err";
      if (v === "ok") {
        pending = null; mark("gu-submit");
        CalrankAuth.nick().then(function (nm) { done = { ans: ans, nick: nm || "" }; load(); });
      } else if (v === "login") { pending = ans; say("로그인하면 방금 고른 답이 바로 남겨집니다."); CalrankAuth.openSheet(); }
      else if (v === "nick") { pending = ans; say("닉네임을 정하면 방금 고른 답이 바로 남겨집니다. 열린 창에서 정해 주세요."); mark("gu-nick"); CalrankAuth.openSheet(); }
      else say(MSG[v] || MSG.bad);
    });
  }
  function resume() { if (pending && CalrankAuth.user()) { var a = pending; pending = null; send(a); } else if (window.CalrankAuth) load(); }
  function bar(d) {
    var n = (d.good_n || 0) + (d.bad_n || 0), w = el("div", "gu-stat");
    var b = el("div", "gu-bar"); b.setAttribute("role", "img"); b.setAttribute("aria-label", "효과 있었어요 " + d.good_n + "명, 별로였어요 " + d.bad_n + "명");
    var g = el("span", "gu-bar-g"); g.style.flexGrow = String(d.good_n || 0); var x = el("span", "gu-bar-b"); x.style.flexGrow = String(d.bad_n || 0);
    b.appendChild(g); b.appendChild(x); w.appendChild(b);
    var pct = n >= 5 ? " (" + Math.round((d.good_n / n) * 100) + "%)" : "";
    w.appendChild(el("p", "gu-n", "써 본 사람 " + n + "명 · 효과 있었어요 " + d.good_n + pct + " · 별로였어요 " + d.bad_n + (d.long_n ? " · 6개월 이상 쓴 사람 " + d.long_n + "명" : "")));
    if (n < 5) w.appendChild(el("p", "gu-small", "5명 이상 모이면 비율을 함께 보여 드립니다."));
    return w;
  }
  function paint(d) {
    sec.innerHTML = ""; var n = (d.good_n || 0) + (d.bad_n || 0);
    sec.appendChild(el("h2", "gu-h", "써 본 분의 확인"));
    sec.appendChild(el("p", "gu-why", "판정은 연구 근거로 정하고, 이 칸에는 실제로 써 본 분의 경험을 모읍니다. 다음에 이 장비를 고르는 분께 보입니다."));
    if (done) {
      var ok = el("div", "gu-done"); ok.setAttribute("role", "status");
      ok.appendChild(el("p", "gu-done-t", "고맙습니다. " + (done.nick ? done.nick + " 님의 " : "") + "확인이 남았습니다."));
      var first = done.nick && d.first_name === done.nick;
      ok.appendChild(el("p", "gu-small", first ? "이 장비의 첫 확인으로 닉네임이 '처음 남긴 사람'에 표시됩니다." : "남긴 확인은 아래 숫자에 합쳐지고, 이 페이지를 보는 분께 보입니다."));
      ok.appendChild(el("p", "gu-small", "바꾸려면 다른 버튼을 누르세요. 지우는 것은 내 활동에서 할 수 있습니다."));
      var nx = el("a", "gu-next", "다른 장비도 써 보셨나요? 기어 판정 전체 보기 →"); nx.href = "gear.html"; ok.appendChild(nx);
      sec.appendChild(ok);
    } else if (d.mine) {
      sec.appendChild(el("p", "gu-mine", "내 확인: " + (d.mine === "good" ? "효과 있었어요" : "별로였어요") + " · 바꾸려면 아래 다른 버튼을 누르세요."));
    }
    if (n) sec.appendChild(bar(d));
    else sec.appendChild(el("p", "gu-n", "아직 써 본 분의 확인이 없습니다. 첫 확인을 남기면 닉네임이 '처음 남긴 사람'으로 이 자리에 표시됩니다."));
    if (d.first_name && n) sec.appendChild(el("p", "gu-by", "처음 남긴 사람: " + d.first_name + " · 마지막 확인 " + ago(d.last_at)));
    sec.appendChild(el("p", "gu-q", "이 장비를 써 보셨나요? 써 본 기간(선택)"));
    var pr = el("div", "gu-per"); if (d.my_period && period == null) period = d.my_period;
    PER.forEach(function (o) { var b = el("button", "gu-chip" + (period === o[0] ? " on" : ""), o[1]); b.type = "button"; b.setAttribute("aria-pressed", period === o[0] ? "true" : "false"); b.onclick = function () { period = period === o[0] ? null : o[0]; Array.prototype.forEach.call(pr.children, function (c, i) { var on = PER[i][0] === period; c.classList.toggle("on", on); c.setAttribute("aria-pressed", on ? "true" : "false"); }); }; pr.appendChild(b); });
    sec.appendChild(pr);
    var bt = el("div", "gu-btns");
    [["good", "효과 있었어요"], ["bad", "별로였어요"]].forEach(function (o) { var b = el("button", "gu-btn" + (d.mine === o[0] ? " on" : ""), o[1]); b.type = "button"; b.setAttribute("aria-pressed", d.mine === o[0] ? "true" : "false"); b.onclick = function () { done = null; send(o[0]); }; bt.appendChild(b); });
    sec.appendChild(bt);
    var msg = el("p", "gu-msg"); msg.setAttribute("role", "status"); sec.appendChild(msg);
    sec.appendChild(el("p", "gu-note", "써 본 분만 남겨 주세요. 닉네임과 함께 공개되고, 내 활동에서 지울 수 있습니다. 개인의 경험이며 위 판정 근거를 대신하지 않습니다."));
  }
  var t = 0, w = setInterval(function () { if (window.CalrankAuth || ++t > 60) { clearInterval(w); if (window.CalrankAuth) load(); } }, 100);
  // 로그인·닉네임이 정해지면, 기다리던 답이 있으면 바로 남기고 없으면 다시 읽는다.
  window.addEventListener("calrank:auth", function () { setTimeout(function () { if (window.CalrankAuth) resume(); }, 100); });
  window.addEventListener("calrank:nick", function () { setTimeout(function () { if (window.CalrankAuth) resume(); }, 300); });
})();
