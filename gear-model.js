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
    if (key === "duration_min" && isNum(input.finishSec) && input.finishSec > 0) {
      return input.finishSec / 60;
    }
    return null;
  }

  // ── Martin 등(1998) 도로사이클 출력 모델 ──────────────────────────
  //
  // 다른 주장은 "연구가 N% 라고 보고했다"를 옮기지만, 공기저항만은 검증된
  // 식이 있어서 그대로 돌리면 된다. 식 자체는 실측 출력과 r=.97, 표준오차
  // 2.7W 로 맞았다 (J Appl Biomech 14(3):276–291).
  //
  //   P = [ ½ρ·CdA·v³ + Crr·m·g·v + (91 + 8.7v)×10⁻³·v ] / Ec
  //
  // 평지·무풍을 가정한다. 경사와 바람 항은 논문에 있지만 여기서는 쓰지
  // 않는다 — 사용자가 넣을 수 없는 값을 기본값으로 채우면 그 기본값이
  // 결과를 좌우하면서 출처는 논문으로 보이게 된다.
  var MARTIN = { rho: 1.225, crr: 0.004, mass: 80, ec: 0.977, g: 9.81 };

  // Object.assign 은 undefined 도 복사한다. 사용자가 안 넣은 값까지 덮어쓰면
  // 기본값이 사라지면서 계산이 NaN 이 되고, 화면에는 "근거 없음"으로 나온다.
  // 숫자가 들어온 것만 덮는다.
  function withOpts(base, opts) {
    var o = Object.assign({}, base);
    if (opts) {
      for (var k in opts) {
        if (Object.prototype.hasOwnProperty.call(opts, k) && isNum(opts[k])) o[k] = opts[k];
      }
    }
    return o;
  }

  // o.grade 는 경사(소수, 0.07 = 7%). 안 넣으면 평지다. 경사 항은 논문 식의
  // 중력 항 m·g·sinθ·v 이고, 구름저항은 노면에 수직인 힘(cosθ)에 걸린다.
  function martinPower(v, o) {
    o = o || MARTIN;
    if (!isNum(v) || v <= 0) return null;
    var th = isNum(o.grade) ? Math.atan(o.grade) : 0;
    var aero = 0.5 * o.rho * o.cda * v * v * v;
    var roll = o.crr * o.mass * o.g * Math.cos(th) * v;
    var grav = o.mass * o.g * Math.sin(th) * v;
    var bear = (91 + 8.7 * v) * 1e-3 * v;
    var sum = aero + roll + grav + bear;
    return { total: sum / o.ec, aero: aero, roll: roll, grav: grav, bear: bear,
             share: aero / sum, gravShare: grav / sum };
  }

  // 같은 출력에서 CdA 만 바뀌면 속도가 어디로 가는지. 이분법으로 푼다.
  function martinSpeed(watts, o) {
    if (!isNum(watts) || watts <= 0) return null;
    var lo = 0.1, hi = 30, mid;
    for (var i = 0; i < 60; i++) {
      mid = (lo + hi) / 2;
      var p = martinPower(mid, o);
      if (!p) return null;
      if (p.total < watts) lo = mid; else hi = mid;
    }
    return (lo + hi) / 2;
  }

  // 공기저항이 가져가는 몫 — 속도만 있으면 난다.
  function aeroShareAt(speedKmh, opts) {
    if (!isNum(speedKmh) || speedKmh <= 0) return null;
    var o = withOpts(MARTIN, opts);
    if (!isNum(o.cda)) o.cda = 0.264;   // 논문 참가자 6명 평균
    var p = martinPower(speedKmh / 3.6, o);
    return p ? { sharePct: p.share * 100, watts: p.total, cda: o.cda } : null;
  }

  // 저항 계수 하나를 퍼센트로 바꿨을 때 같은 힘으로 얼마나 빨라지나.
  // 공기저항(cda)과 구름저항(crr) 둘 다 같은 식으로 푼다 — 어느 쪽을
  // 건드리든 출력을 고정하고 속도를 다시 푸는 일은 똑같다.
  //
  // 여기서 재미있는 건 둘의 방향이 반대라는 점이다. 공기저항은 속도의
  // 세제곱으로 커지니 빠를수록 비중이 커지고, 구름저항은 속도에 비례하니
  // 느릴수록 비중이 커진다. 그래서 같은 퍼센트를 줄여도 빠른 사람은
  // 휠에서, 느린 사람은 타이어에서 더 많이 돌려받는다.
  function resistTimeGain(speedKmh, which, deltaPct, distanceKm, opts) {
    if (!isNum(speedKmh) || speedKmh <= 0) return null;
    if (!isNum(deltaPct) || deltaPct <= 0 || deltaPct >= 100) return null;
    if (which !== "cda" && which !== "crr") return null;
    var o = withOpts(MARTIN, opts);
    if (!isNum(o.cda)) o.cda = 0.264;
    if (!isNum(o[which])) return null;

    var v0 = speedKmh / 3.6;
    var p0 = martinPower(v0, o);
    if (!p0) return null;
    var o2 = Object.assign({}, o);
    o2[which] = o[which] * (1 - deltaPct / 100);
    var v1 = martinSpeed(p0.total, o2);
    if (!isNum(v1) || v1 <= 0) return null;

    var out = { which: which, deltaPct: deltaPct,
                watts: p0.total, sharePct: p0.share * 100,
                rollSharePct: (p0.roll / (p0.aero + p0.roll + p0.bear)) * 100,
                speedBefore: v0 * 3.6, speedAfter: v1 * 3.6,
                gainKmh: (v1 - v0) * 3.6, gainPct: (v1 / v0 - 1) * 100,
                before: o[which], after: o2[which] };
    if (isNum(distanceKm) && distanceKm > 0) {
      out.secBefore = distanceKm * 1000 / v0;
      out.secAfter  = distanceKm * 1000 / v1;
      out.cutSec    = out.secBefore - out.secAfter;
    }
    return out;
  }

  // CdA 가 deltaM2 만큼 줄면 같은 힘으로 얼마나 빨라지나.
  function cdaTimeGain(speedKmh, deltaM2, distanceKm, opts) {
    if (!isNum(speedKmh) || speedKmh <= 0) return null;
    if (!isNum(deltaM2) || deltaM2 <= 0) return null;
    var o = withOpts(MARTIN, opts);
    if (!isNum(o.cda)) o.cda = 0.264;
    if (deltaM2 >= o.cda) return null;

    var v0 = speedKmh / 3.6;
    var p0 = martinPower(v0, o);
    if (!p0) return null;
    var o2 = Object.assign({}, o, { cda: o.cda - deltaM2 });
    var v1 = martinSpeed(p0.total, o2);
    if (!isNum(v1) || v1 <= 0) return null;

    var out = { watts: p0.total, sharePct: p0.share * 100,
                speedBefore: v0 * 3.6, speedAfter: v1 * 3.6,
                gainKmh: (v1 - v0) * 3.6, gainPct: (v1 / v0 - 1) * 100,
                cdaBefore: o.cda, cdaAfter: o2.cda };
    if (isNum(distanceKm) && distanceKm > 0) {
      out.secBefore = distanceKm * 1000 / v0;
      out.secAfter  = distanceKm * 1000 / v1;
      out.cutSec    = out.secBefore - out.secAfter;
    }
    return out;
  }

  // 오르막에서 무게가 줄면 같은 힘으로 얼마나 빨라지나.
  //   gradientPct 경사(%), lengthKm 오르막 길이, powerW 내 출력(W),
  //   massKg 사람+자전거+짐 총중량, deltaKg 줄어드는 무게.
  // 평지 식과 같은 모델에 경사 항만 더했다. 출력을 고정하고 속도를 다시 푼다.
  function massTimeGain(gradientPct, lengthKm, powerW, massKg, deltaKg, opts) {
    if (!isNum(gradientPct) || gradientPct < 0 || gradientPct > 30) return null;
    if (!isNum(lengthKm) || lengthKm <= 0) return null;
    if (!isNum(powerW) || powerW <= 0) return null;
    if (!isNum(massKg) || massKg <= 0) return null;
    if (!isNum(deltaKg) || deltaKg <= 0 || deltaKg >= massKg) return null;
    var o = withOpts(MARTIN, opts);
    if (!isNum(o.cda)) o.cda = 0.35;
    o.grade = gradientPct / 100;
    o.mass = massKg;
    var v0 = martinSpeed(powerW, o);
    var o2 = Object.assign({}, o, { mass: massKg - deltaKg });
    var v1 = martinSpeed(powerW, o2);
    if (!isNum(v0) || !isNum(v1) || v0 <= 0 || v1 <= 0) return null;
    var p0 = martinPower(v0, o);
    var out = { gradientPct: gradientPct, powerW: powerW, massKg: massKg, deltaKg: deltaKg,
                speedBefore: v0 * 3.6, speedAfter: v1 * 3.6,
                gainPct: (v1 / v0 - 1) * 100,
                gravSharePct: p0 ? p0.gravShare * 100 : null,
                aeroSharePct: p0 ? p0.share * 100 : null };
    out.secBefore = lengthKm * 1000 / v0;
    out.secAfter = lengthKm * 1000 / v1;
    out.cutSec = out.secBefore - out.secAfter;
    out.cutSecPerKg = out.cutSec / deltaKg;
    out.wattsPerKg = powerW / massKg;
    return out;
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
        verb: eff.verb || null,
        evidence: ev, hasEvidence: !!ev
      };
      // 모델로 계산하는 효과. 보고된 숫자를 옮기는 대신 식을 돌린다.
      if (ev && eff.computed) {
        out.hasAnyEvidence = true;
        row.computed = eff.computed;
        var spd = isNum(cond) ? cond : null;
        if (eff.computed === "aero_share") {
          row.aero = aeroShareAt(spd, { cda: input.cda });
          row.hasEvidence = !!row.aero;
        } else if (eff.computed === "crr_time" || eff.computed === "cda_pct_time") {
          var which = eff.computed === "crr_time" ? "crr" : "cda";
          var dp = which === "crr" ? ev.crr_delta_pct : ev.cda_delta_pct;
          if (isNum(input.resistDeltaPct)) dp = input.resistDeltaPct;
          row.aero = resistTimeGain(spd, which, dp, input.distanceKm,
                                    { cda: input.cda, crr: input.crr });
          row.hasEvidence = !!row.aero;
          if (row.aero && isNum(row.aero.cutSec)) {
            var sgn = (eff.direction === "worse") ? -1 : 1;
            row.cutSec = { point: sgn * row.aero.cutSec,
                           lo: sgn * row.aero.cutSec, hi: sgn * row.aero.cutSec };
            row.adjustedSec = Math.max(1, Math.round(row.aero.secAfter));
            if (isNum(input.priceKrw) && input.priceKrw > 0 && row.cutSec.point > 0) {
              row.wonPerSecond = input.priceKrw / row.cutSec.point;
              row.priceKrw = input.priceKrw;
            }
          }
        } else if (eff.computed === "cda_time") {
          var delta = isNum(input.cdaDelta) ? input.cdaDelta : ev.cda_delta_m2;
          row.aero = cdaTimeGain(spd, delta, input.distanceKm, { cda: input.cda });
          row.hasEvidence = !!row.aero;
          if (row.aero && isNum(row.aero.cutSec)) {
            row.cutSec = { point: row.aero.cutSec, lo: row.aero.cutSec, hi: row.aero.cutSec };
            row.adjustedSec = Math.max(1, Math.round(row.aero.secAfter));
            if (isNum(input.priceKrw) && input.priceKrw > 0 && row.aero.cutSec > 0) {
              row.wonPerSecond = input.priceKrw / row.aero.cutSec;
              row.priceKrw = input.priceKrw;
            }
          }
        } else if (eff.computed === "mass_time") {
          var dk = isNum(input.deltaKg) ? input.deltaKg : ev.delta_kg;
          var pw = isNum(input.powerW) ? input.powerW : 200;
          var mk = isNum(input.massKg) ? input.massKg : 80;
          row.aero = massTimeGain(cond, input.distanceKm, pw, mk, dk, { cda: input.cda });
          row.hasEvidence = !!row.aero;
          if (row.aero) {
            row.cutSec = { point: row.aero.cutSec, lo: row.aero.cutSec, hi: row.aero.cutSec };
            row.adjustedSec = Math.max(1, Math.round(row.aero.secAfter));
            if (isNum(input.priceKrw) && input.priceKrw > 0 && row.aero.cutSec > 0) {
              row.wonPerSecond = input.priceKrw / row.aero.cutSec;
              row.priceKrw = input.priceKrw;
            }
          }
        }
        out.effects.push(row);
        continue;
      }
      if (ev && ev.no_data) {
        // 적용 구간은 찾았지만 그 구간에 연구가 없다. 이것도 정보다 —
        // 오히려 가장 알고 싶은 구간이 비어 있다는 사실이 정보다.
        row.hasEvidence = false;
        row.noData = true;
        row.gap = { note: ev.note, source: ev.source };
      } else if (ev && (ev.caveat || eff.kind === "caveat")) {
        // 효과가 아니라 주의사항이다. 퍼센트를 붙이면 "0% 좋아집니다"
        // 같은 말이 되는데, 하려던 말과 정반대로 읽힌다.
        out.hasAnyEvidence = true;
        row.hasEvidence = true;
        row.caveat = true;
        row.evidence = ev;
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
    martinPower: martinPower,
    martinSpeed: martinSpeed,
    aeroShareAt: aeroShareAt,
    cdaTimeGain: cdaTimeGain,
    massTimeGain: massTimeGain,
    resistTimeGain: resistTimeGain,
    pickEvidence: pickEvidence,
    effectRange: effectRange,
    evidenceMap: evidenceMap,
    findClaim: findClaim,
    claimsBySport: claimsBySport,
    inRange: inRange
  };
})(typeof window !== "undefined" ? window : globalThis);
