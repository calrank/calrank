// calrank 규정 판정 모델 — 두 번째 축.
//
// gear-model.js 가 "효과가 있는가"를 연구로 따진다면, 이쪽은 "세계 최고 대회에서
// 쓸 수 있는가"를 연맹 규정으로 따진다. 둘을 한 파일에 섞지 않은 이유는 성격이
// 다르기 때문이다. 효과는 구간과 신뢰도가 있는 추정이고, 규정은 통과 아니면
// 위반인 이분법이다. 추정에 쓰는 말투로 규정을 적으면 규정이 무르게 읽히고,
// 규정에 쓰는 말투로 효과를 적으면 추정이 단정으로 읽힌다.
//
// 지키는 것 셋.
//  1. 숫자는 규정 원문 그대로다. 환산하거나 반올림해서 보여 주지 않는다.
//  2. 애매하면 "확인 필요"다. 통과로 밀지 않는다. 장비 검사에서 걸리는 쪽의
//     손해가 훨씬 크다.
//  3. 규정은 거의 매년 바뀐다. 그래서 결과에 언제 기준인지와 원문 링크를
//     반드시 함께 낸다.
(function (global) {
  "use strict";

  function isNum(v) { return typeof v === "number" && isFinite(v); }

  function findRule(data, id) {
    if (!data || !data.rules) return null;
    for (var i = 0; i < data.rules.length; i++) {
      if (data.rules[i].id === id) return data.rules[i];
    }
    return null;
  }

  function rulesBySport(data, sportId) {
    if (!data || !data.rules) return [];
    return data.rules.filter(function (r) { return r.sport === sportId; });
  }

  function bodyOf(data, rule) {
    if (!data || !data.bodies || !rule) return null;
    var b = data.bodies[rule.body];
    return b ? b : null;
  }

  // 사용자 수치를 규정 한 줄에 대 본다.
  //   → { verdict: "pass" | "fail" | "unknown", … }
  // 여유(margin)를 함께 낸다. 통과여도 0.2mm 남았다면 그건 알아야 하는 정보다.
  function checkLimit(value, limit, compare) {
    if (!isNum(value)) return { verdict: "unknown" };
    if (compare === "max") {
      if (!isNum(limit.max)) return { verdict: "pass", unlimited: true };
      return {
        verdict: value <= limit.max ? "pass" : "fail",
        limit: limit.max, margin: limit.max - value, compare: "max"
      };
    }
    if (compare === "min") {
      if (!isNum(limit.min)) return { verdict: "unknown" };
      return {
        verdict: value >= limit.min ? "pass" : "fail",
        limit: limit.min, margin: value - limit.min, compare: "min"
      };
    }
    return { verdict: "unknown" };
  }

  // 수온 기준은 통과·위반이 아니라 세 상태다. 금지 / 선택 / 의무.
  function checkTempBand(temp, option) {
    if (!isNum(temp) || !option) return { verdict: "unknown" };
    var forb = option.forbidden_at, mand = option.mandatory_at;
    if (isNum(forb) && temp >= forb) {
      return { verdict: "forbidden", forbiddenAt: forb, mandatoryAt: mand, temp: temp };
    }
    if (isNum(mand) && temp <= mand) {
      return { verdict: "mandatory", forbiddenAt: forb, mandatoryAt: mand, temp: temp };
    }
    return { verdict: "optional", forbiddenAt: forb, mandatoryAt: mand, temp: temp };
  }

  // input: { rule, value, choice }  choice 는 extra 옵션의 value
  function judge(input) {
    input = input || {};
    var rule = input.rule;
    if (!rule || !rule.check) return null;

    var chk = rule.check;
    var out = { rule: rule, value: input.value, compare: chk.compare, unit: chk.unit };

    // 종목·구분을 고르는 규정은 고른 쪽의 숫자를 쓴다.
    var extra = (chk.extra && chk.extra[0]) || null;
    var option = null;
    if (extra && extra.options) {
      for (var i = 0; i < extra.options.length; i++) {
        if (extra.options[i].value === input.choice) { option = extra.options[i]; break; }
      }
      if (!option) option = extra.options[0];
      out.option = option;
      out.extraLabel = extra.label;
    }

    if (chk.compare === "temp_band") {
      out.band = checkTempBand(input.value, option);
      out.verdict = out.band.verdict;
      return out;
    }

    // 고른 옵션에 숫자가 있으면 그것 하나만 본다. 없으면 규정의 모든 줄을 본다.
    if (option && (isNum(option.max) || isNum(option.min))) {
      out.results = [{
        scope: option.label,
        result: checkLimit(input.value, option, chk.compare),
        note: option.note
      }];
    } else {
      out.results = (rule.limits || []).filter(function (l) {
        return isNum(l.max) || isNum(l.min) || l.max === null;
      }).map(function (l) {
        return { scope: l.scope, result: checkLimit(input.value, l, chk.compare), note: l.note };
      });
    }

    var fails = out.results.filter(function (r) { return r.result.verdict === "fail"; });
    var passes = out.results.filter(function (r) { return r.result.verdict === "pass"; });
    out.verdict = !isNum(input.value) ? "unknown"
                : fails.length === 0 ? "pass"
                : passes.length === 0 ? "fail"
                : "partial";   // 어떤 종목은 통과, 어떤 종목은 위반
    out.failCount = fails.length;
    out.passCount = passes.length;
    return out;
  }

  // 종목별로 두 축이 각각 몇 칸 차 있는지. 카테고리 지도가 이걸로 그려진다.
  function coverage(claimsData, rulesData) {
    var sports = (claimsData && claimsData.sports) || [];
    return sports.map(function (s) {
      var claims = (claimsData.claims || []).filter(function (c) { return c.sport === s.id; });
      var rules = rulesBySport(rulesData, s.id);
      var bodies = {};
      rules.forEach(function (r) { bodies[r.body] = true; });
      return {
        id: s.id, label: s.label,
        claims: claims, rules: rules,
        claimCount: claims.length,
        ruleCount: rules.length,
        checkableCount: rules.filter(function (r) { return r.checkable; }).length,
        bodies: Object.keys(bodies)
      };
    });
  }

  global.calrankRules = {
    judge: judge,
    checkLimit: checkLimit,
    checkTempBand: checkTempBand,
    findRule: findRule,
    rulesBySport: rulesBySport,
    bodyOf: bodyOf,
    coverage: coverage
  };
})(typeof window !== "undefined" ? window : globalThis);
