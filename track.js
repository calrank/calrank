/* 방문 수 세기: 날짜·페이지별 숫자만 보낸다. 이름, 주소(IP), 쿠키는 쓰지 않는다.
   "오늘 이미 왔음" 표시(날짜 한 줄)만 이 기기의 localStorage 에 남긴다. */
(function () {
  // 홈 화면 설치·오프라인 보기를 위한 서비스 워커. 방문 집계와 무관하게 등록한다.
  try {
    if ("serviceWorker" in navigator && window.isSecureContext) {
      window.addEventListener("load", function () { navigator.serviceWorker.register("/sw.js").catch(function () {}); });
    }
  } catch (e) {}
  try {
    if (location.hostname !== "calrank.kr") return;
    // 운영자 본인 방문은 세지 않는다. 주소 끝에 ?cr_me=1 을 붙여 한 번 열면 이 기기에서 제외되고, ?cr_me=0 으로 풀린다.
    try {
      var me = new URLSearchParams(location.search).get("cr_me");
      if (me === "1") localStorage.setItem("cr_me", "1");
      if (me === "0") localStorage.removeItem("cr_me");
      if (localStorage.getItem("cr_me") === "1") return;
    } catch (e) {}
    if (navigator.webdriver || navigator.doNotTrack === "1") return;
    if (/bot|crawl|spider|headless|lighthouse|preview/i.test(navigator.userAgent)) return;
    var day = new Date(Date.now() + 9 * 36e5).toISOString().slice(0, 10), fresh = false;
    try {
      if (localStorage.getItem("cr_seen") !== day) { localStorage.setItem("cr_seen", day); fresh = true; }
    } catch (e) {}
    var path = location.pathname === "/" ? "/index.html" : location.pathname;
    var K = "sb_publishable_byKae86vGA0M5NjoZC0ELw_NMkm8ObR";
    // 화면에 실제로 보일 때만 센다. 링크 미리보기·미리 읽기(prerender)·백그라운드 탭은 hidden 이라 걸러진다.
    function whenVisible(fn) {
      if (document.visibilityState !== "hidden") { fn(); return; }
      var done = false;
      document.addEventListener("visibilitychange", function () {
        if (!done && document.visibilityState === "visible") { done = true; fn(); }
      });
    }
    whenVisible(function () {
      fetch("https://mlbzsqeoqlyvnyzeegeu.supabase.co/rest/v1/rpc/track_view", {
        method: "POST", keepalive: true,
        headers: { apikey: K, Authorization: "Bearer " + K, "Content-Type": "application/json" },
        body: JSON.stringify({ p_path: path, p_new: fresh })
      }).catch(function () {});
    });
    // 행동 측정: 어느 페이지에서 어느 곳으로 이어졌는지만 센다(날짜·페이지·종류·대상 숫자). 개인 식별 정보와 검색어, 주소의 ? 뒷부분은 보내지 않는다.
    function evt(kind, target) {
      try {
        fetch("https://mlbzsqeoqlyvnyzeegeu.supabase.co/rest/v1/rpc/track_evt", {
          method: "POST", keepalive: true,
          headers: { apikey: K, Authorization: "Bearer " + K, "Content-Type": "application/json" },
          body: JSON.stringify({ p_path: path, p_kind: kind, p_target: String(target || "").slice(0, 80) })
        }).catch(function () {});
      } catch (e) {}
    }
    // 같은 세션에서 두 번째 페이지에 도달했는지: 처음 들어온 페이지(path)에 "next"를 한 번 센다.
    try {
      var land = sessionStorage.getItem("cr_land");
      if (!land) sessionStorage.setItem("cr_land", path);
      else if (land !== path && !sessionStorage.getItem("cr_next")) {
        sessionStorage.setItem("cr_next", "1");
        var lp = path; path = land; evt("next", lp); path = lp;
      }
    } catch (e) {}
    // 클릭: 사이트 안 링크는 도착 페이지, 사이트 밖 링크는 "ext", 버튼은 id 만 센다.
    document.addEventListener("click", function (ev) {
      try {
        var el = ev.target && ev.target.closest ? ev.target.closest("a[href],button[id],[role=button][id]") : null;
        if (!el) return;
        if (el.id === "acctBtn") { evt("click", "btn:acctBtn"); return; }
        if (el.tagName === "A") {
          var u = new URL(el.getAttribute("href"), location.href);
          if (u.hostname !== location.hostname) { evt("click", "ext"); return; }
          var t = (u.pathname === "/" ? "/index.html" : u.pathname) + (u.hash && /^#[A-Za-z0-9_-]{1,20}$/.test(u.hash) ? u.hash : "");
          if (t === path) return;
          evt("click", t);
        } else {
          evt("click", "btn:" + el.id);
        }
      } catch (e) {}
    }, true);
    // 들어온 경로: 세션당 한 번만, 종류만 보낸다(주소 전체는 보내지 않는다).
    try {
      if (!sessionStorage.getItem("cr_ref")) {
        sessionStorage.setItem("cr_ref", "1");
        var src = "direct", host = "";
        try { host = new URL(document.referrer).hostname.toLowerCase(); } catch (e) {}
        var utm = (new URLSearchParams(location.search).get("utm_source") || "").toLowerCase();
        var h = utm || host;
        if (host === location.hostname) src = "";
        else if (utm === "share") src = "share";  // 칼랭크의 공유 버튼으로 만든 링크
        else if (h) {
          src = /naver\.com|naver$|^naver/.test(h) ? (/cafe\.naver|^cafe/.test(h) ? "cafe" : /blog\.naver|^blog/.test(h) ? "blog" : "naver")
            : /google|^google/.test(h) ? "google" : /daum|^daum/.test(h) ? "daum"
            : /kakao|^kakao/.test(h) ? "kakao" : /instagram|^instagram/.test(h) ? "instagram"
            : /facebook|^facebook|fb\.com/.test(h) ? "facebook" : /youtube|youtu\.be|^youtube/.test(h) ? "youtube"
            : /^x$|twitter|t\.co$/.test(h) ? "x" : /threads/.test(h) ? "threads" : /band\.us|^band$/.test(h) ? "band" : "other";
        }
        // 어느 페이지로 들어왔는지(주소의 ? 뒷부분 제외)도 함께 보낸다. 출처×페이지 숫자만 쌓인다.
        if (src) whenVisible(function () {
          fetch("https://mlbzsqeoqlyvnyzeegeu.supabase.co/rest/v1/rpc/track_ref", {
            method: "POST", keepalive: true,
            headers: { apikey: K, Authorization: "Bearer " + K, "Content-Type": "application/json" },
            body: JSON.stringify({ p_src: src, p_path: path })
          }).catch(function () {});
        });
      }
    } catch (e) {}
  } catch (e) {}
})();
