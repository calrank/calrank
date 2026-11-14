/* 코스 페이지의 "일몰까지 남는 시간".
   코스 시작점 좌표와 날짜로 일몰을 계산하고, 출발 시각에 걷는 시간 가늠을 더한 하산 시각과 비교한다.
   일몰: NOAA Solar Calculator 식(scripts/sun_times.py 와 같은 식). 서버에 아무것도 보내지 않는다. */
(function () {
  var sec = document.getElementById("sunMargin");
  if (!sec) return;
  var lat = parseFloat(sec.dataset.lat), lon = parseFloat(sec.dataset.lon);
  var wmin = parseFloat(sec.dataset.min), wmax = parseFloat(sec.dataset.max);
  if (!isFinite(lat) || !isFinite(lon) || !isFinite(wmin) || !isFinite(wmax)) return;

  function rad(d) { return d * Math.PI / 180; }
  function deg(r) { return r * 180 / Math.PI; }
  function jday(y, m, d) { return Date.UTC(y, m - 1, d) / 86400000 + 2440587.5; }
  // 반환: [일출, 일몰] 한국 표준시 기준 분(0~1440). 극야·백야면 null
  function sunTimes(y, m, d) {
    var t = (jday(y, m, d) - 2451545.0) / 36525.0;
    var L0 = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360;
    var M = 357.52911 + t * (35999.05029 - 0.0001537 * t);
    var e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t);
    var Mr = rad(M);
    var C = Math.sin(Mr) * (1.914602 - t * (0.004817 + 0.000014 * t)) + Math.sin(2 * Mr) * (0.019993 - 0.000101 * t) + Math.sin(3 * Mr) * 0.000289;
    var trueLong = L0 + C, omega = 125.04 - 1934.136 * t;
    var appLong = trueLong - 0.00569 - 0.00478 * Math.sin(rad(omega));
    var eps0 = 23 + (26 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60) / 60;
    var eps = eps0 + 0.00256 * Math.cos(rad(omega));
    var decl = deg(Math.asin(Math.sin(rad(eps)) * Math.sin(rad(appLong))));
    var yy = Math.pow(Math.tan(rad(eps / 2)), 2), L0r = rad(L0);
    var eot = 4 * deg(yy * Math.sin(2 * L0r) - 2 * e * Math.sin(Mr) + 4 * e * yy * Math.sin(Mr) * Math.cos(2 * L0r) - 0.5 * yy * yy * Math.sin(4 * L0r) - 1.25 * e * e * Math.sin(2 * Mr));
    var latr = rad(lat), declr = rad(decl);
    var cosHa = Math.cos(rad(90.833)) / (Math.cos(latr) * Math.cos(declr)) - Math.tan(latr) * Math.tan(declr);
    if (cosHa > 1 || cosHa < -1) return null;
    var ha = deg(Math.acos(cosHa)), noon = 720 - 4 * lon - eot + 9 * 60;
    return [noon - 4 * ha, noon + 4 * ha];
  }
  function hm(min) {
    min = Math.round(min);
    var d = Math.floor(min / 1440); min -= d * 1440;
    return String(Math.floor(min / 60)).padStart(2, "0") + ":" + String(min % 60).padStart(2, "0") + (d ? " (다음 날)" : "");
  }
  function dur(min) {
    min = Math.round(Math.abs(min));
    var h = Math.floor(min / 60), m = min % 60;
    return h ? h + "시간" + (m ? " " + m + "분" : "") : m + "분";
  }

  var kst = new Date(Date.now() + 9 * 36e5);
  var today = kst.toISOString().slice(0, 10);
  var dateEl = document.getElementById("smDate"), timeEl = document.getElementById("smTime"), out = document.getElementById("smOut");
  dateEl.value = today;
  timeEl.value = "09:00";

  function render() {
    var p = (dateEl.value || "").split("-").map(Number), tp = (timeEl.value || "").split(":").map(Number);
    if (p.length !== 3 || tp.length < 2 || !isFinite(p[0]) || !isFinite(tp[0])) { out.textContent = ""; return; }
    var s = sunTimes(p[0], p[1], p[2]);
    if (!s) { out.textContent = "이 날짜는 일몰을 계산할 수 없습니다."; return; }
    var start = tp[0] * 60 + tp[1];
    var endMin = start + wmin, endMax = start + wmax, sunset = s[1];
    var gapMax = sunset - endMin, gapMin = sunset - endMax;   // 가장 빠르게 / 가장 느리게 걸을 때 남는 시간
    var verdict;
    if (gapMin >= 0) verdict = "걷는 시간 가늠의 범위 안에서는 모두 일몰 전에 내려옵니다. 남는 시간은 " + dur(gapMin) + " ~ " + dur(gapMax) + "입니다.";
    else if (gapMax >= 0) verdict = "천천히 걸으면 일몰 이후에 내려오게 됩니다. 일몰까지 가장 빠르게 걸으면 " + dur(gapMax) + " 남고, 가장 느리게 걸으면 " + dur(gapMin) + " 모자랍니다.";
    else verdict = "걷는 시간 가늠의 범위 모두 일몰 이후에 내려옵니다. 일몰 이후에는 조명이 필요합니다.";
    out.innerHTML = '<table class="cv-table"><tbody>' +
      "<tr><th>일출 · 일몰</th><td>" + hm(s[0]) + " · " + hm(sunset) + "</td></tr>" +
      "<tr><th>하산 예상 시각</th><td>" + hm(endMin) + " ~ " + hm(endMax) + "</td></tr></tbody></table>" +
      '<p class="tp-p">' + verdict + "</p>";
  }
  dateEl.addEventListener("input", render);
  timeEl.addEventListener("input", render);
  render();
})();
