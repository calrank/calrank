// calrank 기어 판정 모델
//
// 하는 일은 하나다. 장비의 "효과 주장"을 받아 **그 사람 조건에서의 기대값**으로
// 바꾼다. 같은 신발이라도 4:16/km로 달리는 사람과 5:15/km로 달리는 사람에게
// 기대할 수 있는 것이 다르고, 그 둘을 가르는 근거의 단단함도 다르기 때문이다.
//
// 설계에서 지킨 네 가지.
//
//  1. 근거가 없는 구간은 비워 둔다. 옆 구간 값을 끌어다 쓰지 않는다.
//     모르면 "근거 없음"이 정답이다.
//  2. 근거 등급을 결과에서 떼지 않는다. 숫자만 보여 주면 2.88%와 0.90%가 같은
//     무게로 읽힌다. 하나는 메타분석이고 하나는 16명짜리 단일 연구다.
//  3. 유의하지 않은 근거는 아래끝을 0으로 둔다. "효과가 없을 수도 있다"가 그
//     연구가 말한 바이므로, 점추정만 보여 주면 과장이 된다.
//  4. 한 장비의 효과를 하나로 줄이지 않는다. 트레일 폴은 산소를 더 쓰면서
//     다리 충격을 줄인다. 좋은 쪽만 적으면 광고가 된다.
//
// 종목과 무관하게 돈다. 조건 변수가 러닝은 속도, 트레일은 경사, 사이클은 다시
// 속도인 것만 다르고 구조는 같다. 그래서 조건 이름을 claim 쪽에 적어 둔다.
//
// 등급 변화는 wma-standards.js 와 grade-model.js 가 실려 있을 때만 낸다.
(function (global) {
  "use strict";

  function isNum(v) { return typeof v === "number" && isFinite(v); }

  // 적용 범위 [아래끝, 위끝]. null 은 제한 없음. 아래끝 포함, 위끝 제외.
  function inRange(value, range) {
    if (!range) return false;
    var lo = range[0], hi = range[1];
    if (lo !== null && lo !== undefined && value < lo) return false;
    if (hi !== null && hi !== undefined && value >= hi) return false;
    return true;
  }

  function pickEvidence(effect, conditionKey, conditionValue) {
    if (!effect || !effect.evidence || !effect.evidence.length) return null;
    for (var i = 0; i < effect.evidence.length; i++) {
      var ev = effect.evidence[i];
      var r = ev.applies ? ev.applies[conditionKey] : null;
      // 조건을 안 따지는 근거(applies 가 [null,null])는 언제나 적용된다.
      if (r && r[0] === null && r[1] === null) return ev;
      if (!isNum(conditionValue)) continue;
      if (inRange(conditionValue, r)) return ev;
    }
    return null;
  }

  // 효과 구간. 유의하지 않으면 아래끝을 0으로 끌어내린다.
  //
  // no_data 는 다르다. "효과가 0"과 "모른다"는 같은 말이 아니고, 0으로 적으면
  // 화면에서 "영향 없음"으로 읽힌다. 연구가 0편인 칸은 숫자를 내지 않는다.
  function effectRange(ev) {
    if (!ev) return null;
    if (ev.no_data) return null;
    var point = ev.effect_pct, lo = point, hi = point;
    if (ev.ci && ev.ci.length === 2) { lo = ev.ci[0]; hi = ev.ci[1]; }
    if (ev.significant === false) lo = 0;
    return { point: point, lo: lo, hi: hi };
  }

  // 조건값을 뽑는다. 러닝은 기록에서 속도가 나오고, 나머지는 받아 쓴다.
  function conditionValue(claim, input) {
    var key = claim.condition;
    if (isNum(input[key])) return input[key];
    if (key === "speed_kmh" && isNum(input.finishSec) && isNum(input.distanceKm) &&
        input.finishSec > 0) {
      return input.distanceKm / (input.finishSec / 3600);
    }
    return null;
  }

  // input: { claim, finishSec, distanceKm, age, gender, priceKrw, [조건값] }
  function judge(input) {
    input = input || {};
    var claim = input.claim;
    if (!claim || !claim.effects || !claim.effects.length) return null;

    var cond = conditionValue(claim, input);
    var out = {
      claim: claim,
      conditionKey: claim.condition,
      conditionValue: cond,
      effects: [],
      hasAnyEvidence: false
    };
    if (isNum(input.finishSec) && isNum(input.distanceKm) && input.distanceKm > 0) {
      out.speedKmh = input.distanceKm / (input.finishSec / 3600);
      out.paceSecPerKm = input.finishSec / input.distanceKm;
    }

    var transfer = isNum(claim.transfer_to_time) ? claim.transfer_to_time : 1;

    for (var i = 0; i < claim.effects.length; i++) {
      var eff = claim.effects[i];
      var ev = pickEvidence(eff, claim.condition, cond);
      var row = {
        id: eff.id, label: eff.label, detail: eff.detail,
        direction: eff.direction || "better",
        evidence: ev, hasEvidence: !!ev
      };
      if (ev && ev.no_data) {
        // 적용 구간은 찾았지만 그 구간에 연구가 없다. 이것도 정보다 —
        // 오히려 가장 알고 싶은 구간이 비어 있다는 사실이 정보다.
        row.hasEvidence = false;
        row.noData = true;
        row.gap = { note: ev.note, source: ev.source };
      } else if (ev) {
        out.hasAnyEvidence = true;
        row.range = effectRange(ev);

        // 기록에 영향을 주는 효과만 시간으로 환산한다.
        if (eff.affects_time && isNum(input.finishSec) && input.finishSec > 0) {
          var sec = input.finishSec, sign = (eff.direction === "worse") ? -1 : 1;
          row.transfer = transfer;
          row.cutSec = {
            point: sign * sec * (row.range.point / 100) * transfer,
            lo:    sign * sec * (row.range.lo    / 100) * transfer,
            hi:    sign * sec * (row.range.hi    / 100) * transfer
          };
          row.adjustedSec = Math.max(1, Math.round(sec - row.cutSec.point));

          var gm = global.calrankGrade;
          if (gm && typeof gm.agePercent === "function" &&
              typeof gm.tierOf === "function" && isNum(input.age) && input.gender) {
            var p0 = gm.agePercent(input.gender, input.distanceKm, input.age, sec);
            var p1 = gm.agePercent(input.gender, input.distanceKm, input.age, row.adjustedSec);
            if (isNum(p0) && isNum(p1)) {
              var t0 = gm.tierOf(p0), t1 = gm.tierOf(p1);
              row.grade = { before: p0, after: p1, tierBefore: t0, tierAfter: t1,
                            moved: !!(t0 && t1 && t0 !== t1) };
            }
          }
          if (isNum(input.priceKrw) && input.priceKrw > 0 && row.cutSec.point > 0) {
            row.wonPerSecond = input.priceKrw / row.cutSec.point;
            row.priceKrw = input.priceKrw;
          }
        }
      }
      out.effects.push(row);
    }
    // 기록으로 환산되는 효과 하나를 머리말로 올려 둔다.
    out.primary = out.effects.filter(function (e) { return e.cutSec; })[0] || null;
    return out;
  }

  // 그 효과의 근거 지형 전체. 차트가 "내가 어느 구간에 있는지"를 그릴 때 쓴다.
  function evidenceMap(claim, effectId) {
    if (!claim || !claim.effects) return [];
    var eff = claim.effects.filter(function (e) { return e.id === effectId; })[0]
            || claim.effects[0];
    if (!eff || !eff.evidence) return [];
    var key = claim.condition;
    return eff.evidence.map(function (ev) {
      var r = (ev.applies && ev.applies[key]) || [null, null];
      return {
        lo: r[0], hi: r[1], grade: ev.grade, range: effectRange(ev),
        significant: ev.significant !== false,
        n: ev.n, studies: ev.studies, source: ev.source, url: ev.url, note: ev.note
      };
    });
  }

  function findClaim(data, id) {
    if (!data || !data.claims) return null;
    for (var i = 0; i < data.claims.length; i++) {
      if (data.claims[i].id === id) return data.claims[i];
    }
    return null;
  }

  function claimsBySport(data, sportId) {
    if (!data || !data.claims) return [];
    return data.claims.filter(function (c) { return c.sport === sportId; });
  }

  global.calrankGear = {
    judge: judge,
    pickEvidence: pickEvidence,
    effectRange: effectRange,
    evidenceMap: evidenceMap,
    findClaim: findClaim,
    claimsBySport: claimsBySport,
    inRange: inRange
  };
})(typeof window !== "undefined" ? window : globalThis);
