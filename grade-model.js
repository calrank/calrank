// calrank 등급 모델 — level.js(계산기), 등급표, 기록증 페이지가 같은 기준을 쓰도록
// 상수와 계산을 한 곳에 모아 둔다. 값이 갈라지면 같은 기록에 다른 등급이 나오므로,
// scripts/generate_grade_pages.py가 매 실행마다 level.js와 이 파일을 함께 대조한다.
//
// 근거 구분(중요):
//  - 거리 환산은 Riegel 공식(Pete Riegel, 1981), 지수 1.06 — 공개된 경험식.
//  - 나이·성별 보정 계수와 등급 구간은 calrank 자체 기준이며 공인 통계가 아니다.
(function (global) {
  "use strict";

  var AGE_ANCHORS = [
    [20, 0.90], [30, 0.93], [40, 0.96], [50, 1.00], [60, 1.10], [70, 1.25], [80, 1.45],
  ];
  var GENDER_FACTOR = { male: 1.00, female: 1.11 };
  var RIEGEL = 1.06;

  // 오름차순(빠른 순): bound = 해당 등급의 '느린 쪽' 경계 (초/km, 10km 환산 기준)
  var TIER_BOUNDS = [
    [240, "상당한 러너"],
    [270, "러닝 상급자"],
    [300, "매우 좋은 편"],
    [348, "상당히 좋은 편"],
    [390, "평균 이상"],
    [450, "보통"],
    [540, "초보/기초체력"],
  ];

  function ageFactor(age) {
    if (age <= AGE_ANCHORS[0][0]) return AGE_ANCHORS[0][1];
    if (age >= AGE_ANCHORS[AGE_ANCHORS.length - 1][0]) return AGE_ANCHORS[AGE_ANCHORS.length - 1][1];
    for (var i = 0; i < AGE_ANCHORS.length - 1; i++) {
      var a0 = AGE_ANCHORS[i][0], f0 = AGE_ANCHORS[i][1];
      var a1 = AGE_ANCHORS[i + 1][0], f1 = AGE_ANCHORS[i + 1][1];
      if (age >= a0 && age <= a1) return f0 + (f1 - f0) * ((age - a0) / (a1 - a0));
    }
    return 1.0;
  }

  // level.js analyze()와 연산 순서까지 같게 맞춘다 (1초 차이로 등급이 갈리지 않도록)
  function normalizedPace(finishSec, distanceKm, age, gender) {
    var equiv10kTime = finishSec * Math.pow(10 / distanceKm, RIEGEL);
    return equiv10kTime / 10 / ageFactor(age) / GENDER_FACTOR[gender];
  }

  function tierOf(finishSec, distanceKm, age, gender) {
    var p = normalizedPace(finishSec, distanceKm, age, gender);
    for (var i = 0; i < TIER_BOUNDS.length; i++) {
      if (p <= TIER_BOUNDS[i][0]) return TIER_BOUNDS[i][1];
    }
    return TIER_BOUNDS[TIER_BOUNDS.length - 1][1];
  }

  // 그 등급을 받기 위한 가장 느린 기록(초). 부동소수점 때문에 경계가 한 칸
  // 어긋날 수 있어 실제 판정 함수로 양쪽을 조여 준다.
  function boundarySeconds(bound, distanceKm, age, gender) {
    var s = Math.floor(bound * ageFactor(age) * GENDER_FACTOR[gender] * 10 *
                       Math.pow(distanceKm / 10, RIEGEL));
    while (s > 0 && normalizedPace(s, distanceKm, age, gender) > bound) s--;
    while (normalizedPace(s + 1, distanceKm, age, gender) <= bound) s++;
    return s;
  }

  // "이 기록은 N세의 '평균 이상' 기준과 같다" — 나이보다 한참 젊게 나올 때만
  // 보여줄 값이라 호출하는 쪽에서 판단한다. 빠른 기록은 20세에서 포화된다.
  function runningAge(finishSec, distanceKm, gender) {
    var lo = 20, hi = 80;
    if (normalizedPace(finishSec, distanceKm, 20, gender) <= 390) return 20;
    if (normalizedPace(finishSec, distanceKm, 80, gender) > 390) return 80;
    for (var i = 0; i < 60; i++) {
      var mid = (lo + hi) / 2;
      if (normalizedPace(finishSec, distanceKm, mid, gender) > 390) lo = mid;
      else hi = mid;
    }
    return Math.round((lo + hi) / 2);
  }

  // 다음 이정표(라운드 넘버)까지 남은 시간. 전 구간 사용자에게 작동한다.
  function nextMilestone(finishSec, distanceKm) {
    var step;
    if (distanceKm <= 7) step = 300;            // 5분
    else if (distanceKm <= 15) step = 300;
    else if (distanceKm <= 30) step = 600;      // 10분
    else step = 900;                            // 15분
    var target = Math.floor((finishSec - 1) / step) * step;
    if (target <= 0) return null;
    return { targetSeconds: target, gapSeconds: finishSec - target,
             perKmSeconds: (finishSec - target) / distanceKm };
  }

  function formatTime(sec) {
    sec = Math.max(0, Math.round(sec));
    var h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
    var pad = function (n) { return n < 10 ? "0" + n : String(n); };
    return h ? h + ":" + pad(m) + ":" + pad(s) : m + ":" + pad(s);
  }

  function parseTime(text) {
    var parts = String(text).trim().split(":").map(Number);
    if (parts.some(isNaN)) return null;
    if (parts.length === 2) return parts[0] * 60 + parts[1];
    if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
    return null;
  }

  global.CalrankGrade = {
    AGE_ANCHORS: AGE_ANCHORS,
    GENDER_FACTOR: GENDER_FACTOR,
    RIEGEL: RIEGEL,
    TIER_BOUNDS: TIER_BOUNDS,
    ageFactor: ageFactor,
    normalizedPace: normalizedPace,
    tierOf: tierOf,
    boundarySeconds: boundarySeconds,
    runningAge: runningAge,
    nextMilestone: nextMilestone,
    formatTime: formatTime,
    parseTime: parseTime,
  };
})(typeof window !== "undefined" ? window : globalThis);
