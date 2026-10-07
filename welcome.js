// welcome.html — 접수 마감이 임박한 대회를 바로 보여 준다.
//
// 이 페이지는 index.html 이 referrer 없는 첫 방문자를 보내는 곳이다.
// 카카오톡·오픈채팅·카페 앱에서 누른 링크는 referrer 가 비어 오기 때문에,
// 커뮤니티로 들어온 사람은 대부분 여기에 먼저 떨어진다.
// 간판만 보여 주면 그대로 나가므로, 지금 당장 쓸모 있는 정보를 바로 건넨다.

(function () {
  "use strict";

  var LIST = document.getElementById("wcDeadlines");
  if (!LIST) return;

  var SPORT_EMOJI = {
    marathon: "🏃", trail: "⛰️", cycling: "🚴", triathlon: "🏊", inline: "⛸️",
  };

  function todayIso() {
    var d = new Date();
    var p = function (n) { return n < 10 ? "0" + n : String(n); };
    return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate());
  }

  // 날짜 문자열끼리 뺀다. 시간대 때문에 하루가 밀리지 않도록 UTC 정오로 맞춘다.
  function daysBetween(fromIso, toIso) {
    var a = new Date(fromIso + "T12:00:00Z").getTime();
    var b = new Date(toIso + "T12:00:00Z").getTime();
    return Math.round((b - a) / 86400000);
  }

  function isPlaceholder(v) {
    return !v || /^(장소|시간|거리|종목)?\s*(미확인|미정|확인\s*중|추후\s*공지)$/.test(String(v).trim());
  }

  function render(items, today) {
    LIST.innerHTML = "";
    items.forEach(function (ev) {
      var left = daysBetween(today, ev.regDeadline);
      var a = document.createElement("a");
      a.className = "wc-row";
      a.href = "e/" + encodeURIComponent(ev.id) + ".html";

      var dday = document.createElement("span");
      dday.className = "wc-dday" + (left <= 3 ? " urgent" : "");
      dday.textContent = left === 0 ? "오늘 마감" : "D-" + left;

      var body = document.createElement("span");
      body.className = "wc-body";

      var name = document.createElement("b");
      name.textContent = (SPORT_EMOJI[ev.sport] || "🏁") + " " + (ev.name || "대회");

      var meta = document.createElement("span");
      var bits = [];
      if (!isPlaceholder(ev.region)) bits.push(ev.region);
      var dists = (ev.distances || []).filter(function (d) { return !isPlaceholder(d); });
      if (dists.length) bits.push(dists.slice(0, 3).join(" · "));
      bits.push("대회일 " + ev.date);
      meta.textContent = bits.join("  ·  ");

      body.appendChild(name);
      body.appendChild(meta);
      a.appendChild(dday);
      a.appendChild(body);
      LIST.appendChild(a);
    });
  }

  fetch("events.json")
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(function (data) {
      var all = Array.isArray(data) ? data : (data && data.events) || [];
      var today = todayIso();

      var soon = all.filter(function (ev) {
        return ev && typeof ev.regDeadline === "string" &&
               ev.regDeadline.length === 10 &&
               ev.regDeadline >= today &&
               typeof ev.date === "string" && ev.date >= today;
      });

      soon.sort(function (a, b) {
        if (a.regDeadline !== b.regDeadline) return a.regDeadline < b.regDeadline ? -1 : 1;
        return (a.date || "") < (b.date || "") ? -1 : 1;
      });

      if (!soon.length) {
        // 마감일 데이터가 하나도 없을 때까지 빈 상자를 보여 주진 않는다
        var sec = document.getElementById("wcDeadlineSec");
        if (sec) sec.style.display = "none";
        return;
      }
      render(soon.slice(0, 4), today);
    })
    .catch(function () {
      var sec = document.getElementById("wcDeadlineSec");
      if (sec) sec.style.display = "none";
    });
})();
