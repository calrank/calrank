// 기어 "써 봤어요" — 장비를 써 본 사람이 효과를 확인하고, 처음 남긴 닉네임이 보인다.
// 로그인·닉네임이 필요하고, 페이지마다 한 사람이 한 번(바꿀 수 있음) 남긴다. 서버가 같은 규칙으로 다시 검사한다.
(function () {
  "use strict";
  var m = /\/(gear-[a-z0-9-]+)\.html$/.exec(location.pathname); if (!m) return;
  var id = m[1], main = document.querySelector("main"); if (!main) return;
  var MSG = { login: "로그인한 뒤 남길 수 있습니다.", nick: "닉네임을 먼저 정해 주세요(내 활동 페이지).", bad: "저장하지 못했습니다. 잠시 뒤 다시 시도해 주세요.", slow: "잠시 뒤 다시 시도해 주세요." };
  var PER = [[1, "한 달 미만"], [2, "1~6개월"], [3, "6개월 이상"]];
  var period = null, sec = document.createElement("section"); sec.className = "gu-sec"; sec.setAttribute("aria-live", "polite"); main.appendChild(sec);
  function el(t, c, x) { var e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; }
  function ago(iso) { var d = Math.floor((Date.now() - new Date(iso)) / 864e5); return d <= 0 ? "오늘" : d + "일 전"; }
  function load() { CalrankAuth.rpc("gear_use_summary", { p_gear: id }).then(function (r) { var d = r && !r.error && Array.isArray(r.data) ? r.data[0] : null; paint(d || { good_n: 0, bad_n: 0, long_n: 0 }); }); }
  function send(ans, msg) {
    if (!CalrankAuth.user()) { CalrankAuth.openSheet(); return; }
    CalrankAuth.rpc("submit_gear_use", { p_gear: id, p_answer: ans, p_period: period }).then(function (r) {
      var v = r && !r.error ? r.data : "err"; if (v === "ok") load(); else msg.textContent = MSG[v] || MSG.bad;
    });
  }
  function paint(d) {
    sec.innerHTML = ""; var n = (d.good_n || 0) + (d.bad_n || 0);
    sec.appendChild(el("h2", "gu-h", "써 본 분의 확인"));
    sec.appendChild(el("p", "gu-n", n ? "써 본 사람 " + n + "명 · 효과 있었어요 " + d.good_n + " · 별로였어요 " + d.bad_n + (d.long_n ? " · 6개월 이상 쓴 사람 " + d.long_n + "명" : "") : "아직 써 본 사람의 확인이 없습니다."));
    if (d.first_name) sec.appendChild(el("p", "gu-by", "처음 남긴 사람: " + d.first_name + " · 마지막 확인 " + ago(d.last_at)));
    sec.appendChild(el("p", "gu-q", "이 장비를 써 보셨나요? 써 본 기간(선택)"));
    var pr = el("div", "gu-per"); if (d.my_period) period = d.my_period;
    PER.forEach(function (o) { var b = el("button", "gu-chip" + (period === o[0] ? " on" : ""), o[1]); b.type = "button"; b.setAttribute("aria-pressed", period === o[0] ? "true" : "false"); b.onclick = function () { period = period === o[0] ? null : o[0]; Array.prototype.forEach.call(pr.children, function (c, i) { var on = PER[i][0] === period; c.classList.toggle("on", on); c.setAttribute("aria-pressed", on ? "true" : "false"); }); }; pr.appendChild(b); });
    sec.appendChild(pr);
    var msg = el("p", "gu-msg"); msg.setAttribute("role", "status");
    var bt = el("div", "gu-btns");
    [["good", "효과 있었어요"], ["bad", "별로였어요"]].forEach(function (o) { var b = el("button", "gu-btn" + (d.mine === o[0] ? " on" : ""), o[1]); b.type = "button"; b.setAttribute("aria-pressed", d.mine === o[0] ? "true" : "false"); b.onclick = function () { send(o[0], msg); }; bt.appendChild(b); });
    sec.appendChild(bt); sec.appendChild(msg);
    sec.appendChild(el("p", "gu-note", "써 본 분만 남겨 주세요. 닉네임과 함께 공개되고, 내 활동에서 지울 수 있습니다. 개인의 경험이며 위 판정 근거를 대신하지 않습니다."));
  }
  var t = 0, w = setInterval(function () { if (window.CalrankAuth || ++t > 60) { clearInterval(w); if (window.CalrankAuth) load(); } }, 100);
  window.addEventListener("calrank:auth", function () { setTimeout(function () { if (window.CalrankAuth) load(); }, 100); });
})();
