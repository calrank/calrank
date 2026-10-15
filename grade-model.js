// calrank 등급 모델 — 계산기(level.js), 등급표, 기록증 페이지가 같은 기준을 쓰도록
// 상수와 계산을 한 곳에 모아 둔다. 값이 갈라지면 같은 기록에 다른 등급이 나오므로,
// scripts/generate_grade_pages.py가 매 실행마다 이 파일과 level.js를 함께 대조한다.
//
// 기준축은 WMA(세계마스터즈육상연맹) 2025 도로 연령 기준표다.
// 연령등급 % = 그 나이·성별의 기준기록 ÷ 내 기록 × 100. 100%가 세계기록 수준이고,
// 어느 age-grading 계산기에 넣어도 같은 값이 나온다. 표와 출처는 wma-standards.js에.
//
// 이 파일은 wma-standards.js가 먼저 실려 있어야 동작한다.
(function (global) {
  "use strict";

  // 내림차순(빠른 순). 값은 그 등급을 받기 위한 연령등급 % 하한.
  var TIER_BOUNDS = [
    [72, "상당한 러너"],
    [65, "러닝 상급자"],
    [59, "매우 좋은 편"],
    [51, "상당히 좋은 편"],
    [45, "꾸준한 러너"],
    [39, "보통"],
    [0,  "이제 시작"],
  ];

  // WMA가 보간 없이 직접 산출하는 네 거리.
  var DIST_KEY = [[5, "5km"], [10, "10km"], [21.0975, "half"], [42.195, "full"]];

  function distKey(km) {
    for (var i = 0; i < DIST_KEY.length; i++) {
      if (Math.abs(km - DIST_KEY[i][0]) < 0.05) return DIST_KEY[i][1];
    }
    return null;
  }

  function standard(gender, km, age) {
    var key = distKey(km);
    if (!key || typeof global.wmaStandard !== "function") return null;
    return global.wmaStandard(gender, key, age);
  }

  // 연령등급 %. 이 숫자 하나가 등급을 정한다.
  function ageGradePct(finishSec, distanceKm, age, gender) {
    var std = standard(gender, distanceKm, age);
    return std ? std / finishSec * 100 : null;
  }

  function tierOf(finishSec, distanceKm, age, gender) {
    var pct = ageGradePct(finishSec, distanceKm, age, gender);
    if (pct === null) return null;
    for (var i = 0; i < TIER_BOUNDS.length; i++) {
      if (pct >= TIER_BOUNDS[i][0]) return TIER_BOUNDS[i][1];
    }
    return TIER_BOUNDS[TIER_BOUNDS.length - 1][1];
  }

  // 그 등급을 받을 수 있는 가장 느린 기록(초).
  // 연령등급은 기록에 반비례하니 나눗셈 한 번이면 된다.
  function boundarySeconds(boundPct, distanceKm, age, gender) {
    var std = standard(gender, distanceKm, age);
    if (!std) return null;
    if (boundPct <= 0) return Infinity;
    return Math.floor(std / (boundPct / 100));
  }

  // "이 기록은 N세 기준으로 보면 꾸준한 러너입니다" — 같은 기록이 '꾸준한 러너'
  // 경계에 딱 걸리는 나이를 찾는다. 나이가 많을수록 경계가 느슨해지므로
  // 경계 시간은 나이에 대해 단조증가한다. 20세에서 이미 느슨하면 20을,
  // 100세에서도 모자라면 100을 돌려준다.
  function runningAge(finishSec, distanceKm, gender) {
    var REF = 45;  // '꾸준한 러너' 경계
    if (!distKey(distanceKm) || typeof global.wmaStandard !== "function") return null;
    if (boundarySeconds(REF, distanceKm, 20, gender) >= finishSec) return 20;
    if (boundarySeconds(REF, distanceKm, 100, gender) < finishSec) return 100;
    for (var age = 20; age <= 100; age++) {
      if (boundarySeconds(REF, distanceKm, age, gender) >= finishSec) return age;
    }
    return 100;
  }

  // 다음 이정표(라운드 넘버)까지 남은 시간. 전 구간 사용자에게 작동한다.
  function nextMilestone(finishSec, distanceKm) {
    var step;
    if (distanceKm <= 15) step = 300;           // 5분
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
    TIER_BOUNDS: TIER_BOUNDS,
    distKey: distKey,
    ageGradePct: ageGradePct,
    tierOf: tierOf,
    boundarySeconds: boundarySeconds,
    runningAge: runningAge,
    nextMilestone: nextMilestone,
    formatTime: formatTime,
    parseTime: parseTime,
  };
})(typeof window !== "undefined" ? window : globalThis);
