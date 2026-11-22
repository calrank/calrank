/* 제휴 블록: 상품 카드 표시 + 반응 측정(어느 페이지인지만, 사람은 식별하지 않는다).
   1) 매주 갱신되는 인기 상품(affiliate_cards)이 있으면 쿠팡 배너 자리에 상품 카드를 그린다. 없으면 쿠팡 배너가 그대로 보인다.
   2) 배너·카드가 화면에 처음 보이면 aff-view, 카드·글자 링크를 누르면 aff-click 을 센다(쿠팡 배너 안의 클릭은 쿠팡 파트너스 리포트에서 본다).
   funnel.js 의 calrankMark 가 조회로 기록한다. */
(function () {
  var URL_ = "https://mlbzsqeoqlyvnyzeegeu.supabase.co/rest/v1/rpc/affiliate_cards";
  var K = "sb_publishable_byKae86vGA0M5NjoZC0ELw_NMkm8ObR";
  function mark(s) { try { if (window.calrankMark) window.calrankMark(s); } catch (x) { /* 무시 */ } }
  function won(n) { return n ? n.toLocaleString("ko-KR") + "원" : ""; }
  function el(t, c, x) { var e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; }
  var box = document.querySelector(".aff-box"), ban = box && box.querySelector(".aff-ban");
  document.addEventListener("click", function (e) {
    var a = e.target && e.target.closest ? e.target.closest("a[data-aff]") : null;
    if (a) mark("aff-click");
  });
  function watch(node) {
    if (!node || !("IntersectionObserver" in window)) return;
    var io = new IntersectionObserver(function (es) { if (es.some(function (e) { return e.isIntersecting; })) { io.disconnect(); mark("aff-view"); } }, { threshold: 0.5 });
    io.observe(node);
  }
  function cards(rows, page) {
    var ul = el("ul", "aff-cards");
    rows.forEach(function (r) {
      if (!/^https:\/\/link\.coupang\.com\//.test(r.url) || !/^https:\/\//.test(r.image)) return;
      var li = el("li"), a = el("a"); a.href = r.url; a.rel = "sponsored nofollow noopener"; a.target = "_blank"; a.setAttribute("data-aff", page);
      var im = el("img"); im.src = r.image; im.alt = ""; im.loading = "lazy"; im.width = 120; im.height = 120; a.appendChild(im);
      a.appendChild(el("span", "aff-nm", r.name));
      if (r.price) a.appendChild(el("span", "aff-pr", won(r.price)));
      li.appendChild(a); ul.appendChild(li);
    });
    return ul;
  }
  if (box && ban && box.getAttribute("data-bk") && window.fetch) {
    var page = location.pathname.replace(/^\//, "");
    fetch(URL_, { method: "POST", headers: { apikey: K, Authorization: "Bearer " + K, "Content-Type": "application/json" }, body: JSON.stringify({ p_banner: box.getAttribute("data-bk") }) })
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (rows) {
        if (!Array.isArray(rows) || rows.length < 3) return;
        var ul = cards(rows, page); if (ul.children.length < 3) return;
        ban.replaceWith(ul); watch(ul);
      }).catch(function () { /* 쿠팡 배너가 그대로 남는다 */ });
  }
  watch(ban);
})();
