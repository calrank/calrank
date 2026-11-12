/* 방문 수 세기: 날짜·페이지별 숫자만 보낸다. 이름, 주소(IP), 쿠키는 쓰지 않는다.
   "오늘 이미 왔음" 표시(날짜 한 줄)만 이 기기의 localStorage 에 남긴다. */
(function () {
  try {
    if (location.hostname !== "calrank.vercel.app") return;
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
  } catch (e) {}
})();
