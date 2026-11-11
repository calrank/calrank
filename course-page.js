// 저장된 코스 한 곳의 체력 부하를 보여 준다. 단면 자료는 #cpData(JSON)에 들어 있고,
// 계산은 course.js(Minetti 2002)가 한다. 필요한 스크립트: course.js
(function () {
  "use strict";
  var C = window.CalrankCourse, $ = function (id) { return document.getElementById(id); };
  var el = $("cpData"); if (!C || !el) return;
  var data; try { data = JSON.parse(el.textContent); } catch (e) { return; }
  var segs = C.fromProfile(data.profile);
  var prof = data.profile.map(function (p) { return { x: p[0], y: p[1] }; });
  function render() {
    var pace = C.parsePace($("cpPace").value);
    if (!pace) { $("cpMsg").textContent = "평지 페이스를 6:30 처럼 적어 주세요."; return; }
    $("cpMsg").textContent = "";
    var r = C.analyze(segs, { flatPaceSecPerKm: pace, downhillBenefit: $("cpDown").checked });
    var km = r.distM / 1000;
    $("cpIndex").textContent = r.index.toFixed(2);
    $("cpBand").textContent = C.band(r.index);
    $("cpTable").innerHTML = [
      ["평지로 환산한 거리", (r.equivM / 1000).toFixed(1) + " km"],
      ["1km당 상승", (r.gainM / km).toFixed(0) + " m"],
      ["100m 구간 최대 경사", (r.maxGrade * 100).toFixed(0) + " %"],
      ["이 페이스로 걸리는 시간", C.fmtTime(r.timeSec)]
    ].map(function (x) { return "<tr><th>" + x[0] + "</th><td>" + x[1] + "</td></tr>"; }).join("");
    if ($("cpChart")) $("cpChart").innerHTML = C.drawProfile(prof);
  }
  document.addEventListener("DOMContentLoaded", function () {
    $("cpPace").addEventListener("change", render);
    $("cpDown").addEventListener("change", render);
    render();
  });
})();
