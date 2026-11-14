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
    fetch("https://mlbzsqeoqlyvnyzeegeu.supabase.co/rest/v1/rpc/track_view", {
      method: "POST", keepalive: true,
      headers: { apikey: K, Authorization: "Bearer " + K, "Content-Type": "application/json" },
      body: JSON.stringify({ p_path: path, p_new: fresh })
    }).catch(function () {});
    // 들어온 경로: 세션당 한 번만, 종류만 보낸다(주소 전체는 보내지 않는다).
    try {
      if (!sessionStorage.getItem("cr_ref")) {
        sessionStorage.setItem("cr_ref", "1");
        var src = "direct", host = "";
        try { host = new URL(document.referrer).hostname.toLowerCase(); } catch (e) {}
        var utm = (new URLSearchParams(location.search).get("utm_source") || "").toLowerCase();
        var h = utm || host;
        if (host === location.hostname) src = "";
        else if (h) {
          src = /naver\.com|naver$|^naver/.test(h) ? (/cafe\.naver|^cafe/.test(h) ? "cafe" : /blog\.naver|^blog/.test(h) ? "blog" : "naver")
            : /google|^google/.test(h) ? "google" : /daum|^daum/.test(h) ? "daum"
            : /kakao|^kakao/.test(h) ? "kakao" : /instagram|^instagram/.test(h) ? "instagram"
            : /facebook|^facebook|fb\.com/.test(h) ? "facebook" : /youtube|youtu\.be|^youtube/.test(h) ? "youtube"
            : /^x$|twitter|t\.co$/.test(h) ? "x" : /threads/.test(h) ? "threads" : /band\.us|^band$/.test(h) ? "band" : "other";
        }
        if (src) fetch("https://mlbzsqeoqlyvnyzeegeu.supabase.co/rest/v1/rpc/track_ref", {
          method: "POST", keepalive: true,
          headers: { apikey: K, Authorization: "Bearer " + K, "Content-Type": "application/json" },
          body: JSON.stringify({ p_src: src })
        }).catch(function () {});
      }
    } catch (e) {}
  } catch (e) {}
})();
