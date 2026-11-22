/* 계정 버튼: 헤더의 사람 모양 버튼 하나로 로그인·가입·비밀번호 찾기·로그아웃을 한다.
   서버 라이브러리(supabase-js)는 로그인 창에서 무언가를 누르기 전에는 받지 않는다.
   로그인 여부 표시는 이 기기에 저장된 세션 기록만 읽는다. 버튼은 링크(내 랭크)라서 이 스크립트가 없어도 로그인 화면으로 간다. */
(function () {
  "use strict";
  var btn = document.getElementById("acctBtn");
  if (!btn) return;
  var URL_ = "https://mlbzsqeoqlyvnyzeegeu.supabase.co";
  var KEY = "sb_publishable_byKae86vGA0M5NjoZC0ELw_NMkm8ObR";
  var LIB = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.119.0/dist/umd/supabase.min.js";
  var STORE = "sb-mlbzsqeoqlyvnyzeegeu-auth-token";
  // 소셜 로그인: Supabase 대시보드에서 해당 제공자를 켠 뒤 여기에 이름을 넣으면 버튼이 나타난다. 예: ["kakao","google"]
  var SOCIAL = [];
  var SOCIAL_LABEL = { kakao: "카카오로 계속하기", google: "구글로 계속하기" };
  var IDLE_DAYS = 30, LAST = "calrank_last_seen", ONLY = "calrank_session_only", LIVE = "calrank_live";
  var sheet = null, scrim = null, mode = "login", lastFocus = null;

  // ── 이 기기의 로그인 기록 ────────────────────────────────────────
  function savedUser() {
    try {
      var o = JSON.parse(localStorage.getItem(STORE) || "null");
      var u = o && (o.user || (o.currentSession && o.currentSession.user));
      return u && u.email ? u : null;
    } catch (e) { return null; }
  }
  function maskEmail(m) {
    var p = String(m).split("@");
    if (p.length !== 2) return m;
    return p[0].slice(0, 2) + "***@" + p[1];
  }
  function paint() {
    var u = savedUser();
    btn.classList.toggle("is-in", !!u);
    btn.setAttribute("aria-label", u ? "내 계정 (로그인됨)" : "로그인·내 계정");
    btn.title = u ? "내 계정" : "로그인";
  }
  paint();
  // 서비스 워커가 예전 style.css 를 먼저 내줄 때(재방문 첫 1회) 버튼 모양이 깨지지 않도록 최소 규칙을 보충한다.
  try {
    if (getComputedStyle(btn).borderRadius.indexOf("50%") < 0) {
      var fb = document.createElement("style");
      fb.textContent = ".acct-btn{order:2;position:relative;display:inline-flex;align-items:center;justify-content:center;flex:none;width:40px;height:40px;margin-left:16px;border:1.5px solid #bbb;border-radius:50%}" +
        ".acct-btn img{width:22px;height:22px;margin:0}.acct-btn.is-in::after{content:'';position:absolute;right:-1px;top:-1px;width:11px;height:11px;border-radius:50%;background:#2A7A50;border:2px solid #fff}" +
        ".nav-menu{order:1}@media(max-width:1020px){.acct-btn{order:0;width:44px;height:44px;margin:0 8px 0 0}.nav-toggle{order:1}}";
      document.head.appendChild(fb);
    }
  } catch (e) { /* 무시 */ }
  // 오래 안 들어오면 로그아웃: 마지막 방문 후 30일이 지났거나, "로그인 유지"를 끄고 브라우저를 닫았다 다시 연 경우.
  (function () {
    try {
      var now = Date.now(), last = +localStorage.getItem(LAST) || 0, u = savedUser();
      var expired = u && ((last && now - last > IDLE_DAYS * 864e5) ||
        (localStorage.getItem(ONLY) === "1" && !sessionStorage.getItem(LIVE)));
      localStorage.setItem(LAST, String(now)); sessionStorage.setItem(LIVE, "1");
      if (expired) {
        getClient(function (e, c) {
          if (e) return;
          c.auth.signOut().then(function () { localStorage.removeItem(ONLY); paint(); window.dispatchEvent(new CustomEvent("calrank:auth")); });
        });
      }
    } catch (e) { /* 저장소를 못 쓰는 환경에서는 건너뛴다 */ }
  })();
  window.addEventListener("storage", function (e) { if (e.key === STORE) { paint(); if (sheet && !sheet.hidden) render(savedUser() ? "in" : (mode === "in" ? "login" : mode)); } });

  // ── 서버 연결은 필요할 때만 ──────────────────────────────────────
  function getClient(cb) {
    try { if (typeof sb !== "undefined" && sb && sb.auth) return cb(null, sb); } catch (e) { /* 이 페이지에는 없다 */ }
    if (window.__acctSb) return cb(null, window.__acctSb);
    function make() {
      try { window.__acctSb = window.supabase.createClient(URL_, KEY); cb(null, window.__acctSb); } catch (e) { cb(e); }
    }
    if (window.supabase && window.supabase.createClient) return make();
    var s = document.createElement("script");
    s.src = LIB; s.onload = make; s.onerror = function () { cb(new Error("load")); };
    document.head.appendChild(s);
  }
  function friendly(err) {
    var m = String((err && err.message) || ""), st = err && err.status, code = String((err && err.code) || ""), mc = m + " " + code;
    if (/over_email_send_rate_limit|email rate limit/i.test(mc)) return "메일을 보내는 횟수가 잠시 한도에 닿았습니다. 몇 분 뒤에 다시 눌러 주세요.";
    if (/over_request_rate_limit|only request this after/i.test(mc)) { var sec = /(\d+)\s*seconds?/i.exec(m); return "너무 자주 눌렀습니다. " + (sec ? sec[1] + "초" : "잠시") + " 뒤에 다시 눌러 주세요."; }
    if (st === 429 || /rate limit|too many/i.test(mc)) return "요청이 한꺼번에 많았습니다. 잠시 뒤에 다시 눌러 주세요.";
    if (/invalid login credentials/i.test(m)) return "이메일 또는 비밀번호가 맞지 않습니다.";
    if (/email not confirmed/i.test(m)) return "이메일 인증을 먼저 마쳐 주세요. 가입할 때 보낸 메일을 확인해 주세요.";
    if (/weak_password|pwned|known to be weak|easy to guess/i.test(mc)) return "너무 흔하거나 유출된 적 있는 비밀번호입니다. 다른 비밀번호로 정해 주세요.";
    if (/password/i.test(m) && /(longer|too long|72)/i.test(m)) return "비밀번호는 72자 이하로 정해 주세요.";
    if (/password/i.test(m) && /(least|short|characters)/i.test(m)) return "비밀번호는 8자 이상으로 정해 주세요.";
    if (/email_address_invalid|invalid.*email|email.*invalid|unable to validate email/i.test(mc)) return "이메일 주소를 확인해 주세요. 쓸 수 없는 주소입니다.";
    if (/error sending|sending (confirmation|recovery|magic)|smtp|email_provider|unexpected_failure/i.test(mc) || st === 500) return "인증 메일을 보내지 못했습니다. 잠시 뒤에 다시 시도해 주세요.";
    if (/user_banned|banned/i.test(mc)) return "이용이 제한된 계정입니다.";
    if (/signup_disabled|signups? not allowed|signups? .*disabled/i.test(mc)) return "지금은 새 가입을 받지 않습니다.";
    if (/failed to fetch|networkerror|network request failed|load failed|fetch/i.test(m) || st === 0) return "인터넷 연결을 확인하고 다시 눌러 주세요.";
    return "처리하지 못했습니다. 잠시 뒤에 다시 시도해 주세요.";
  }

  // ── 창 ───────────────────────────────────────────────────────────
  var CSS = ".acct-scrim{position:fixed;inset:0;z-index:60;background:rgba(0,0,0,.45);display:flex;align-items:flex-end;justify-content:center}" +
    ".acct-scrim[hidden]{display:none}" +
    ".acct-sheet{box-sizing:border-box;width:100%;max-width:420px;max-height:92vh;max-height:92dvh;overflow-y:auto;background:var(--bg);color:var(--ink);" +
    "border:1px solid var(--line);border-radius:18px 18px 0 0;padding:20px 20px calc(22px + env(safe-area-inset-bottom,0px));font-family:var(--font-body,inherit)}" +
    "@media (min-width:600px){.acct-scrim{align-items:center}.acct-sheet{border-radius:18px;padding-bottom:24px}}" +
    ".acct-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0 0 12px}" +
    ".acct-title{margin:0;font-size:19px;font-weight:800;line-height:1.3}" +
    ".acct-x{flex:none;width:44px;height:44px;margin:-8px -10px -8px 0;border:0;background:none;color:var(--ink-soft);font-size:26px;line-height:1;cursor:pointer;border-radius:50%}" +
    ".acct-tabs{display:flex;gap:6px;margin:0 0 14px}" +
    ".acct-tab{flex:1;min-height:44px;border:1.5px solid var(--border);background:var(--bg);color:var(--ink-soft);font:700 15px/1 var(--font-body,inherit);border-radius:999px;cursor:pointer}" +
    ".acct-tab[aria-selected=true]{border-color:var(--ink);background:var(--ink);color:var(--bg)}" +
    ".acct-form{display:flex;flex-direction:column;gap:6px}" +
    ".acct-form label{font-size:13px;font-weight:700;color:var(--ink-soft);margin-top:6px}" +
    ".acct-form input[type=email],.acct-form input[type=password],.acct-pwrow input[type=text]{box-sizing:border-box;width:100%;min-height:46px;padding:0 14px;font:500 16px/1 var(--font-body,inherit);" +
    "color:var(--ink);background:var(--surface);border:1.5px solid var(--border);border-radius:12px}" +
    ".acct-form input:focus-visible,.acct-sheet button:focus-visible,.acct-sheet a:focus-visible{outline:2px solid var(--accent-ink);outline-offset:2px}" +
    ".acct-pwrow{position:relative;display:flex}.acct-pwrow input{padding-right:64px!important}" +
    ".acct-eye{position:absolute;right:4px;top:0;bottom:0;min-width:56px;border:0;background:none;color:var(--ink-soft);font:700 14px/1 var(--font-body,inherit);cursor:pointer;border-radius:10px}" +
    ".acct-hint{margin:2px 0 0;font-size:12.5px;line-height:1.55;color:var(--ink-faint)}" +
    ".acct-agree{display:flex;align-items:flex-start;gap:10px;margin-top:10px;font-size:13px;line-height:1.55;color:var(--ink-soft)}" +
    ".acct-agree a{color:var(--ink);text-decoration:underline}" +
    ".acct-agree input{flex:none;width:20px;height:20px;margin:1px 0 0}" +
    ".acct-go{min-height:48px;margin-top:12px;border:0;border-radius:999px;background:var(--accent-fill);color:var(--on-accent);font:800 16px/1 var(--font-body,inherit);cursor:pointer}" +
    ".acct-go[disabled]{opacity:.6;cursor:default}" +
    ".acct-msg{min-height:1.4em;margin:8px 0 0;font-size:13.5px;line-height:1.5;color:var(--ink-soft)}" +
    ".acct-acts{display:flex;flex-direction:column;gap:6px;margin-top:10px;font-weight:600}.acct-acts .acct-link{margin:0;align-self:flex-start}.acct-msg.err{color:var(--accent-ink)}" +
    ".acct-msg.ok{white-space:pre-line;padding:12px 14px;border-radius:12px;background:var(--surface);border:1.5px solid var(--ink);color:var(--ink);font-weight:700}" +
    ".acct-note{margin:12px 0 0;font-size:13px;line-height:1.6;color:var(--ink-faint)}" +
    ".acct-link{display:inline-block;margin-top:10px;padding:0;border:0;background:none;color:var(--ink-soft);font:600 14px/1.4 var(--font-body,inherit);text-decoration:underline;cursor:pointer}" +
    ".acct-row{display:flex;flex-direction:column;gap:8px;margin-top:6px}" +
    ".acct-btn2{display:flex;align-items:center;justify-content:center;min-height:48px;border:1.5px solid var(--ink);border-radius:999px;background:var(--bg);color:var(--ink);font:800 16px/1 var(--font-body,inherit);text-decoration:none;cursor:pointer}" +
    ".acct-who{margin:0 0 14px;font-size:15px;color:var(--ink-soft);word-break:break-all}";

  var carry = "";
  function emailField(auto) {
    return '<label for="acctEmail">이메일</label><input type="email" id="acctEmail" name="email" autocomplete="' + auto +
      '" inputmode="email" autocapitalize="none" autocorrect="off" spellcheck="false" required placeholder="you@example.com">';
  }
  function pwField(id, auto, ph, describe) {
    return '<div class="acct-pwrow"><input type="password" id="' + id + '" name="' + id + '" autocomplete="' + auto + '" required placeholder="' + ph + '"' +
      (describe ? ' aria-describedby="acctHint"' : "") + ' autocapitalize="none" autocorrect="off" spellcheck="false">' +
      '<button type="button" class="acct-eye" data-act="eye" aria-label="비밀번호 보기" aria-pressed="false">보기</button></div>';
  }
  var HINT = '<p class="acct-hint" id="acctHint">8자 이상. 외우기 쉬운 문장을 길게 만들면 안전합니다. 비밀번호 관리 앱에서 붙여넣어도 됩니다.</p>';
  function el(html) { var d = document.createElement("div"); d.innerHTML = html; return d.firstElementChild; }

  function build() {
    var st = document.createElement("style"); st.textContent = CSS; document.head.appendChild(st);
    scrim = el('<div class="acct-scrim" hidden></div>');
    sheet = el('<div class="acct-sheet" role="dialog" aria-modal="true" aria-labelledby="acctTitle"></div>');
    scrim.appendChild(sheet); document.body.appendChild(scrim);
    scrim.addEventListener("mousedown", function (e) { if (e.target === scrim) close(); });
    sheet.addEventListener("click", onClick);
    sheet.addEventListener("submit", onSubmit);
    document.addEventListener("keydown", onKey);
  }

  function head(title) {
    return '<div class="acct-head"><h2 class="acct-title" id="acctTitle">' + title + '</h2>' +
      '<button type="button" class="acct-x" data-act="close" aria-label="닫기">×</button></div>';
  }
  var AGREE = '<label class="acct-agree"><input type="checkbox" id="acctAgree"><span>만 14세 이상이며, <a href="terms.html" target="_blank" rel="noopener">이용약관</a>과 ' +
    '<a href="privacy.html" target="_blank" rel="noopener">개인정보처리방침</a>에 동의합니다.</span></label>';

  function social() {
    if (!SOCIAL.length) return "";
    return '<div class="acct-row" style="margin-top:14px">' + SOCIAL.map(function (k) {
      return '<button type="button" class="acct-btn2" data-act="oauth" data-p="' + k + '">' + (SOCIAL_LABEL[k] || k) + '</button>';
    }).join("") + '</div>';
  }
  function render(which) {
    mode = which;
    var h;
    if (which === "in") {
      var u = savedUser();
      h = head("내 계정") + '<p class="acct-who" id="acctWho"></p><div class="acct-row">' +
        '<a class="acct-btn2" href="myrank.html">내 랭크로 가기</a>' +
        '<button type="button" class="acct-btn2" data-act="chpw">비밀번호 변경</button>' +
        '<button type="button" class="acct-btn2" data-act="out">로그아웃</button></div><p class="acct-msg" id="acctMsg" role="status"></p>';
      sheet.innerHTML = h;
      sheet.querySelector("#acctWho").textContent = u ? maskEmail(u.email) : "";
    } else if (which === "chpw") {
      h = head("비밀번호 변경") + '<form class="acct-form" id="acctForm" data-kind="chpw" novalidate>' +
        '<label for="acctPw">새 비밀번호</label>' + pwField("acctPw", "new-password", "8자 이상", true) + HINT +
        '<label for="acctPw2">새 비밀번호 확인</label>' + pwField("acctPw2", "new-password", "한 번 더 입력", false) +
        '<button type="submit" class="acct-go">비밀번호 변경</button><p class="acct-msg" id="acctMsg" role="status"></p></form>' +
        '<button type="button" class="acct-link" data-act="in">← 돌아가기</button>';
      sheet.innerHTML = h;
    } else if (which === "reset") {
      h = head("비밀번호 찾기") + '<form class="acct-form" id="acctForm" data-kind="reset" novalidate>' +
        '<p class="acct-note" style="margin:0 0 6px">가입한 이메일을 넣으면 비밀번호를 새로 정할 수 있는 링크를 보내 드립니다.</p>' +
        '' + emailField("email") +
        '<button type="submit" class="acct-go">재설정 링크 받기</button><p class="acct-msg" id="acctMsg" role="status"></p></form>' +
        '<button type="button" class="acct-link" data-act="login">← 로그인으로 돌아가기</button>';
      sheet.innerHTML = h;
    } else {
      var up = which === "signup";
      h = head(up ? "회원가입" : "로그인") +
        '<div class="acct-tabs" role="tablist"><button type="button" class="acct-tab" role="tab" data-act="login" aria-selected="' + (!up) + '">로그인</button>' +
        '<button type="button" class="acct-tab" role="tab" data-act="signup" aria-selected="' + up + '">회원가입</button></div>' +
        '<form class="acct-form" id="acctForm" data-kind="' + (up ? "signup" : "login") + '" novalidate>' +
        '' + emailField(up ? "email" : "username") +
        '<label for="acctPw">비밀번호</label>' + pwField("acctPw", up ? "new-password" : "current-password", up ? "8자 이상" : "비밀번호", up) + (up ? HINT : "") +
        (up ? AGREE : '<label class="acct-agree"><input type="checkbox" id="acctKeep" checked><span>이 기기에서 로그인 유지 (30일 이상 접속하지 않으면 자동 로그아웃)</span></label>') +
        '<button type="submit" class="acct-go">' + (up ? "회원가입" : "로그인") + '</button><p class="acct-msg" id="acctMsg" role="status"></p></form>' +
        social() + (up ? '<p class="acct-note">가입에는 이메일과 비밀번호만 필요합니다. 실명과 전화번호는 받지 않습니다.</p>'
            : '<button type="button" class="acct-link" data-act="reset">비밀번호를 잊으셨나요?</button>' +
              '<p class="acct-note">로그인 없이도 대회 일정과 등급 확인은 그대로 쓸 수 있습니다.</p>');
      sheet.innerHTML = h;
    }
    var ce = sheet.querySelector("#acctEmail");
    if (ce && carry) ce.value = carry;
    carry = "";
    var f = sheet.querySelector("input");
    if (f) f.focus(); else { var b = sheet.querySelector("a,button:not(.acct-x)"); if (b) b.focus(); }
  }

  function open() {
    if (!sheet) build();
    lastFocus = document.activeElement;
    render(savedUser() ? "in" : "login");
    scrim.hidden = false;
    document.documentElement.style.overflow = "hidden";
    btn.setAttribute("aria-expanded", "true");
  }
  function close() {
    if (!sheet || scrim.hidden) return;
    scrim.hidden = true;
    document.documentElement.style.overflow = "";
    btn.setAttribute("aria-expanded", "false");
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }
  function onKey(e) {
    if (!sheet || scrim.hidden) return;
    if (e.key === "Escape") { e.preventDefault(); close(); return; }
    if (e.key !== "Tab") return;
    var f = sheet.querySelectorAll("a[href],button:not([disabled]),input:not([disabled])");
    if (!f.length) return;
    var first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }

  var TYPO = { "gmial.com": "gmail.com", "gamil.com": "gmail.com", "gmail.co": "gmail.com", "gmail.con": "gmail.com", "naver.con": "naver.com", "naver.co": "naver.com",
    "nave.com": "naver.com", "daum.com": "daum.net", "hanmial.net": "hanmail.net", "hanmail.com": "hanmail.net", "kakao.net": "kakao.com" };
  function typoOf(e) { var d = e.split("@")[1]; return d && TYPO[d.toLowerCase()] ? e.split("@")[0] + "@" + TYPO[d.toLowerCase()] : ""; }
  function msg(t, err, ok, acts) {
    var m = sheet.querySelector("#acctMsg"); if (!m) return;
    m.textContent = t; m.className = "acct-msg" + (err ? " err" : ok ? " ok" : "");
    if (acts && acts.length) {
      var row = document.createElement("span"); row.className = "acct-acts";
      acts.forEach(function (a, i) { var b = document.createElement("button"); b.type = "button"; b.setAttribute("data-act", a[0]); b.className = i ? "acct-link" : "acct-btn2"; b.textContent = a[1]; row.appendChild(b); });
      m.appendChild(row);
    }
    if (ok) { try { m.scrollIntoView({ block: "nearest" }); } catch (e) {} }
  }
  function busy(on) { var g = sheet.querySelector(".acct-go"); if (g) g.disabled = on; }

  function onClick(e) {
    var t = e.target.closest ? e.target.closest("[data-act]") : null;
    if (!t) return;
    var a = t.getAttribute("data-act");
    var ei = sheet.querySelector("#acctEmail"); if (ei && ei.value && (a === "login" || a === "signup" || a === "reset")) carry = ei.value.trim();
    if (a === "close") close();
    else if (a === "login" || a === "signup" || a === "reset" || a === "chpw") render(a);
    else if (a === "in") render("in");
    else if (a === "oauth") oauth(t.getAttribute("data-p"));
    else if (a === "out") signOut();
    else if (a === "eye") {
      var inp = t.parentNode.querySelector("input"), show = inp.type === "password";
      inp.type = show ? "text" : "password";
      t.textContent = show ? "숨기기" : "보기";
      t.setAttribute("aria-pressed", String(show));
      t.setAttribute("aria-label", show ? "비밀번호 숨기기" : "비밀번호 보기");
    }
  }

  function oauth(p) {
    if (SOCIAL.indexOf(p) < 0) return;
    msg("연결하는 중…");
    getClient(function (err, c) {
      if (err) return msg("연결하지 못했습니다. 잠시 후 다시 시도해 주세요.", true);
      try { localStorage.removeItem(ONLY); } catch (x) { /* 무시 */ }
      c.auth.signInWithOAuth({ provider: p, options: { redirectTo: location.href.split("#")[0] } })
        .then(function (r) { if (r.error) msg(friendly(r.error), true); });
    });
  }
  function signOut() {
    msg("로그아웃하는 중…");
    getClient(function (err, c) {
      if (err) return msg("연결하지 못했습니다. 잠시 후 다시 시도해 주세요.", true);
      c.auth.signOut().then(function () {
        try { localStorage.removeItem("calrank_guest_mode"); } catch (x) { /* 저장소를 못 쓰는 환경 */ }
        paint(); close();
        window.dispatchEvent(new CustomEvent("calrank:auth"));
      }, function () { msg("로그아웃하지 못했습니다. 잠시 후 다시 시도해 주세요.", true); });
    });
  }

  function onSubmit(e) {
    e.preventDefault();
    var kind = e.target.getAttribute("data-kind");
    var emEl = sheet.querySelector("#acctEmail");
    var email = emEl ? (emEl.value || "").trim() : "";
    var pwEl = sheet.querySelector("#acctPw"), pw = pwEl ? pwEl.value : "";
    if (kind === "chpw") {
      var pw2 = sheet.querySelector("#acctPw2").value;
      if (pw.length < 8) return msg("비밀번호는 8자 이상이어야 합니다. 지금 " + pw.length + "자입니다.", true);
      if (pw.length > 72) return msg("비밀번호는 72자 이하로 정해 주세요.", true);
      if (pw !== pw2) return msg("두 비밀번호가 서로 다릅니다.", true);
      busy(true); msg("처리하는 중…");
      return getClient(function (err, c) {
        if (err) { busy(false); return msg("연결하지 못했습니다. 잠시 후 다시 시도해 주세요.", true); }
        c.auth.updateUser({ password: pw }).then(function (r) {
          busy(false);
          msg(r.error ? (/same|different/i.test(r.error.message || "") ? "이전과 다른 비밀번호를 입력해 주세요." : friendly(r.error)) : "비밀번호를 바꿨습니다.", !!r.error);
        }, function (x) { busy(false); msg(friendly(x), true); });
      });
    }
    function bad(t, el) { msg(t, true); if (el && el.focus) el.focus(); return; }
    if (!email) return bad("이메일을 입력해 주세요.", emEl);
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return bad("이메일 주소 형식이 맞지 않습니다. 예: name@example.com", emEl);
    if (kind === "signup" && !pw) return bad("비밀번호를 입력해 주세요. 8자 이상이면 됩니다.", pwEl);
    if (kind === "signup" && pw.length < 8) return bad("비밀번호는 8자 이상이어야 합니다. 지금 " + pw.length + "자입니다.", pwEl);
    if (kind === "signup" && pw.length > 72) return bad("비밀번호는 72자 이하로 정해 주세요.", pwEl);
    if (kind === "login" && !pw) return bad("비밀번호를 입력해 주세요.", pwEl);
    if (kind === "signup" && !sheet.querySelector("#acctAgree").checked) return bad("가입하려면 약관과 개인정보처리방침에 동의해 주세요.", sheet.querySelector("#acctAgree"));
    if (kind !== "chpw" && typoOf(email) && sheet.getAttribute("data-typo") !== email) {
      var fix = typoOf(email);
      sheet.setAttribute("data-typo", email);
      emEl.value = fix;
      return msg("이메일을 " + fix + " 로 고쳤습니다. 맞는지 확인하고 다시 눌러 주세요. 다른 주소라면 직접 고쳐 주세요.", true);
    }
    busy(true); msg("처리하는 중…");
    getClient(function (err, c) {
      if (err) { busy(false); return msg("연결하지 못했습니다. 잠시 후 다시 시도해 주세요.", true); }
      var p = kind === "login" ? c.auth.signInWithPassword({ email: email, password: pw })
        : kind === "signup" ? c.auth.signUp({ email: email, password: pw })
        : c.auth.resetPasswordForEmail(email, { redirectTo: location.origin + "/reset.html" });
      p.then(function (r) {
        busy(false);
        if (r.error) {
          var em = String(r.error.message || "");
          if (kind === "login" && /invalid login credentials/i.test(em)) return msg("이메일 또는 비밀번호가 맞지 않습니다. 가입하지 않은 이메일일 수도 있습니다.", true, false, [["reset", "비밀번호 재설정"], ["signup", "아직 가입 전이에요 · 회원가입"]]);
          if (kind === "login" && /email not confirmed/i.test(em)) return msg("이메일 인증이 아직 끝나지 않았습니다. 가입 때 받은 메일의 링크를 눌러 주세요. 메일이 없다면 회원가입을 다시 눌러 새 인증 메일을 받을 수 있습니다.", true, false, [["signup", "인증 메일 다시 받기"]]);
          if (kind === "signup" && /already|registered|exists/i.test(em)) return msg("이미 가입한 이메일입니다. 로그인해 주세요.", false, true, [["login", "로그인하기"], ["reset", "비밀번호가 기억나지 않아요"]]);
          return msg(friendly(r.error), true);
        }
        if (kind === "reset") return msg(email + " 로 재설정 링크를 보냈습니다. 받은 편지함과 스팸함을 확인해 주세요. 메일이 없다면 가입하지 않은 이메일일 수 있습니다.", false, true, [["signup", "회원가입하기"]]);
        if (kind === "signup" && !(r.data && r.data.session)) {
          // 가입된 이메일인지 여부는 일부러 알려 주지 않는다.
          return msg("가입 요청을 받았습니다.\n① 메일함(스팸함 포함)에서 인증 링크를 눌러 주세요.\n② 메일이 없다면 이미 가입한 이메일입니다. 로그인해 주세요.", false, true, [["login", "로그인하기"], ["reset", "비밀번호가 기억나지 않아요"]]);
        }
        try {
          var kp = sheet.querySelector("#acctKeep");
          if (kind === "login" && kp && !kp.checked) localStorage.setItem(ONLY, "1"); else localStorage.removeItem(ONLY);
          localStorage.setItem(LAST, String(Date.now()));
        } catch (x) { /* 무시 */ }
        paint(); close();
        window.dispatchEvent(new CustomEvent("calrank:auth"));
      }, function (x) { busy(false); msg(friendly(x), true); });
    });
  }

  // 메일 인증 링크로 들어온 경우: 만료·재사용이면 다음 할 일을, 성공이면 로그인됐다는 안내를 보여 준다.
  (function landing() {
    var raw = (location.hash || "") + "&" + (location.search || "");
    if (/reset\.html/.test(location.pathname)) return;
    var errc = /error_code=([a-z_]+)/.exec(raw), ok = /type=signup/.test(raw) && /access_token=/.test(raw);
    if (!errc && !ok) return;
    function clean() { try { history.replaceState(null, "", location.pathname + (ok || errc ? "" : location.search)); } catch (e) { /* 무시 */ } }
    function show() {
      if (!sheet) build();
      lastFocus = document.activeElement; render("login");
      scrim.hidden = false; document.documentElement.style.overflow = "hidden"; btn.setAttribute("aria-expanded", "true");
    }
    if (errc) {
      clean();
      return show(), msg(errc[1] === "otp_expired" ? "인증 링크가 만료됐거나 이미 사용됐습니다. 이미 인증했다면 로그인해 주세요. 아직이라면 회원가입을 다시 눌러 새 인증 메일을 받을 수 있습니다." : "인증 링크를 확인하지 못했습니다. 로그인해 보시고, 안 되면 회원가입을 다시 눌러 새 메일을 받아 주세요.", true, false, [["signup", "인증 메일 다시 받기"]]);
    }
    getClient(function (err, c) {
      if (err) return;
      setTimeout(function () { clean(); paint(); show(); render(savedUser() ? "in" : "login"); msg(savedUser() ? "이메일 인증이 끝났습니다. 로그인된 상태입니다." : "이메일 인증이 끝났습니다. 로그인해 주세요.", false, true); }, 600);
    });
  })();

  btn.addEventListener("click", function (e) {
    // 새 탭·창으로 열기(휠 클릭, Ctrl·Cmd 클릭)는 원래 링크(내 랭크)대로 둔다.
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    open();
  });
})();
