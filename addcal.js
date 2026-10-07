// 대회 하나를 사용자의 캘린더에 넣어 주는 조각.
//
// 왜 전체 구독(feed.ics)만으로 부족한가:
// 구글 캘린더는 "To subscribe to a new calendar, you must use a computer web
// browser" 라고 못박고 있다(구글 캘린더 고객센터). 즉 안드로이드 사용자는
// 폰에서 URL 구독을 아예 할 수 없다. calrank 방문자의 39%가 안드로이드다.
// 그래서 구독과 별개로, 대회 한 건을 그 자리에서 넣는 길을 둔다.
// 이 경로는 안드로이드·아이폰·PC 어디서나 동작한다.
//
// 두 가지를 준다:
//  1) 구글 캘린더 템플릿 링크 — 한 번에 열리지만 알림은 넣을 수 없다(URL 규격 한계).
//  2) .ics 파일 — VALARM 을 품고 있어 접수 마감과 대회 당일 알림이 함께 들어간다.
//     파일은 브라우저 안에서 만들어지며 서버로 아무것도 보내지 않는다.

(function (global) {
  "use strict";

  var PLACEHOLDER = /^(장소|시간|거리|종목|주최|접수)?\s*(미확인|미정|확인\s*중|추후\s*공지|별도\s*공지)$/;

  function meaningful(v) {
    if (v === null || v === undefined) return false;
    var s = String(v).trim();
    return !!s && !PLACEHOLDER.test(s);
  }

  function pad(n) { return n < 10 ? "0" + n : String(n); }

  function compact(iso) { return String(iso || "").replace(/-/g, ""); }

  // 종일 일정의 DTEND 는 '다음 날'이다 (끝나는 날은 포함되지 않는다)
  function nextDay(iso) {
    var d = new Date(iso + "T12:00:00Z");
    d.setUTCDate(d.getUTCDate() + 1);
    return d.getUTCFullYear() + pad(d.getUTCMonth() + 1) + pad(d.getUTCDate());
  }

  function todayIso() {
    var d = new Date();
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
  }

  function icsEscape(t) {
    return String(t === null || t === undefined ? "" : t)
      .replace(/\\/g, "\\\\").replace(/,/g, "\\,")
      .replace(/;/g, "\\;").replace(/\n/g, "\\n");
  }

  // RFC 5545: 한 줄 75옥텟. 한글은 UTF-8 에서 3바이트라 바이트로 자르면 글자가
  // 깨져 캘린더 앱이 파일을 통째로 거부한다. 글자 단위로 바이트를 센다.
  var ENC = typeof TextEncoder !== "undefined" ? new TextEncoder() : null;
  function utf8len(ch) {
    if (ENC) return ENC.encode(ch).length;
    return encodeURIComponent(ch).replace(/%[0-9A-F]{2}/g, "x").length;
  }

  function fold(line) {
    var out = [], cur = "", used = 0, first = true;
    for (var i = 0; i < line.length; i++) {
      var ch = line[i];
      var n = utf8len(ch);
      var limit = first ? 75 : 74;
      if (used + n > limit) {
        out.push(cur);
        cur = ch; used = n; first = false;
      } else {
        cur += ch; used += n;
      }
    }
    out.push(cur);
    return out.join("\r\n ");
  }

  function describe(ev) {
    var parts = [];
    var dists = (ev.distances || []).filter(meaningful);
    if (dists.length) parts.push("종목: " + dists.join(", "));
    [["time", "시간"], ["location", "장소"], ["regDeadline", "접수 마감"],
     ["organizer", "주최"], ["applyUrl", "신청"]].forEach(function (p) {
      if (meaningful(ev[p[0]])) parts.push(p[1] + ": " + ev[p[0]]);
    });
    parts.push("https://calrank.vercel.app/e/" + encodeURIComponent(ev.id) + ".html");
    return parts.join("\n");
  }

  function alarm(trigger, text) {
    return ["BEGIN:VALARM", "ACTION:DISPLAY", "TRIGGER:" + trigger,
            "DESCRIPTION:" + icsEscape(text), "END:VALARM"];
  }

  function buildIcs(ev) {
    var now = new Date().toISOString().replace(/[-:]/g, "").split(".")[0] + "Z";
    var url = "https://calrank.vercel.app/e/" + encodeURIComponent(ev.id) + ".html";
    var desc = icsEscape(describe(ev));
    var name = ev.name || "대회";

    var lines = [
      "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//calrank//KO",
      "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
      "X-WR-CALNAME:" + icsEscape(name), "X-WR-TIMEZONE:Asia/Seoul",
      "BEGIN:VEVENT",
      "UID:" + ev.id + "@calrank.vercel.app",
      "DTSTAMP:" + now,
      "DTSTART;VALUE=DATE:" + compact(ev.date),
      "DTEND;VALUE=DATE:" + nextDay(ev.date),
      "SUMMARY:" + icsEscape(name),
      "LOCATION:" + icsEscape(meaningful(ev.location) ? ev.location : ""),
      "DESCRIPTION:" + desc,
      "URL:" + url,
      "TRANSP:TRANSPARENT",
    ];
    lines = lines.concat(alarm("-P7D", name + " D-7 — 준비물과 교통편을 확인하세요"));
    lines = lines.concat(alarm("-P1D", name + " 내일입니다 — 배번과 출발 시간을 확인하세요"));
    lines.push("END:VEVENT");

    // 접수 마감이 아직 안 지났고 대회일보다 앞설 때만 따로 넣는다
    var dl = ev.regDeadline;
    if (meaningful(dl) && String(dl).length === 10 && dl >= todayIso() && dl < ev.date) {
      lines = lines.concat([
        "BEGIN:VEVENT",
        "UID:" + ev.id + "-deadline@calrank.vercel.app",
        "DTSTAMP:" + now,
        "DTSTART;VALUE=DATE:" + compact(dl),
        "DTEND;VALUE=DATE:" + nextDay(dl),
        "SUMMARY:" + icsEscape("[접수 마감] " + name),
        "DESCRIPTION:" + desc,
        "URL:" + url,
        "TRANSP:TRANSPARENT",
      ]);
      lines = lines.concat(alarm("-P3D", name + " 접수 마감 3일 전입니다"));
      lines = lines.concat(alarm("-P1D", name + " 접수가 내일 마감됩니다"));
      lines.push("END:VEVENT");
    }
    lines.push("END:VCALENDAR");

    return lines.map(fold).join("\r\n") + "\r\n";
  }

  // 구글 캘린더 템플릿 링크. 알림은 URL 로 지정할 수 없다(구글 규격).
  function googleUrl(ev) {
    var p = new URLSearchParams();
    p.set("action", "TEMPLATE");
    p.set("text", ev.name || "대회");
    p.set("dates", compact(ev.date) + "/" + nextDay(ev.date));
    p.set("details", describe(ev));
    if (meaningful(ev.location)) p.set("location", ev.location);
    return "https://calendar.google.com/calendar/render?" + p.toString();
  }

  function download(ev) {
    var blob = new Blob([buildIcs(ev)], { type: "text/calendar;charset=utf-8" });
    var href = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = href;
    a.download = (ev.name || "대회").replace(/[\\/:*?"<>|]/g, "") + ".ics";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(href); }, 1000);
  }

  function mount(container, ev) {
    if (!container || !ev || !ev.date) return;
    container.innerHTML = "";

    var box = document.createElement("div");
    box.className = "ac-box";

    var h = document.createElement("b");
    h.className = "ac-h";
    h.textContent = "📅 내 캘린더에 추가";
    box.appendChild(h);

    var row = document.createElement("div");
    row.className = "ac-row";

    var g = document.createElement("a");
    g.className = "ac-btn pri";
    g.href = googleUrl(ev);
    g.target = "_blank";
    g.rel = "noopener";
    g.textContent = "구글 캘린더";
    row.appendChild(g);

    var d = document.createElement("button");
    d.type = "button";
    d.className = "ac-btn";
    d.textContent = "알림 포함 (.ics)";
    d.addEventListener("click", function () { download(ev); });
    row.appendChild(d);

    box.appendChild(row);

    var note = document.createElement("span");
    note.className = "ac-note";
    var hasDl = meaningful(ev.regDeadline) && ev.regDeadline >= todayIso() && ev.regDeadline < ev.date;
    note.textContent = hasDl
      ? ".ics 를 받으면 접수 마감 3일 전·하루 전, 대회 7일 전·하루 전에 알림이 울립니다."
      : ".ics 를 받으면 대회 7일 전과 하루 전에 알림이 울립니다.";
    box.appendChild(note);

    container.appendChild(box);
  }

  global.CalrankAddCal = {
    mount: mount, buildIcs: buildIcs, googleUrl: googleUrl, download: download,
  };
})(typeof window !== "undefined" ? window : globalThis);
