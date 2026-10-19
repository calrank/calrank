// calrank 내 체력 등급 확인 — 로그인 없이 바로 계산 (전부 브라우저에서 처리)

// 등급 기준축은 WMA(세계마스터즈육상연맹) 2025 도로 연령 기준표다.
// 연령등급 % = 그 나이·성별의 기준기록 ÷ 내 기록 × 100. 100%가 세계기록 수준이고,
// 어느 age-grading 계산기에 넣어도 같은 값이 나온다. 표와 출처는 wma-standards.js에.
//
// 내림차순(빠른 순). 값은 그 등급을 받기 위한 연령등급 % 하한.
const TIER_BOUNDS = [
  [72, "상당한 러너", "동호인 최상위권입니다. 이 페이스를 꾸준히 유지하는 것 자체가 훈련이 잘 되어 있다는 뜻이에요.", "동호인 최상위권입니다. 훈련이 잘 되어 있다는 뜻이에요."],
  [65, "러닝 상급자", "동호인 사이에서도 확실히 빠른 편입니다. 대회에서 상위권을 노려볼 만한 수준이에요.", "동호인 사이에서도 확실히 빠른 편입니다. 대회 상위권을 노려볼 만해요."],
  [59, "매우 좋은 편", "평균을 크게 웃도는 체력입니다. 꾸준한 훈련이 실제 기록으로 잘 전환되고 있어요.", "평균을 크게 웃도는 체력입니다. 훈련이 기록으로 잘 전환되고 있어요."],
  [51, "상당히 좋은 편", "일반적인 동호인 평균을 확실히 넘어선 수준입니다. 운동을 꽤 하는 편이라고 볼 수 있어요.", "동호인 평균을 확실히 넘어선 수준입니다. 운동을 꽤 하는 편이에요."],
  [45, "꾸준한 러너", "또래·동성 평균보다 좋은 편입니다. 꾸준히 달리고 계신 게 기록으로 드러나고 있어요.", "또래·동성 평균보다 좋은 편입니다. 꾸준히 달린 게 드러나고 있어요."],
  [39, "보통", "일반적인 체력 수준입니다. 지금의 페이스도 꾸준히 유지하면 좋은 기반이 됩니다.", "일반적인 체력 수준입니다. 지금 페이스를 유지하면 좋은 기반이 돼요."],
  [0, "이제 시작", "이제 막 시작하는 단계이거나 기초체력을 다지는 중이에요. 완주 자체가 의미 있는 시작입니다.", "기초체력을 다지는 단계입니다. 완주 자체가 의미 있는 시작이에요."],
];

// WMA가 보간 없이 직접 산출하는 네 거리.
const DIST_KEY = [[5, "5km"], [10, "10km"], [21.0975, "half"], [42.195, "full"]];

function distKey(km) {
  for (const [v, k] of DIST_KEY) if (Math.abs(km - v) < 0.05) return k;
  return null;
}

function wmaStd(gender, km, age) {
  const k = distKey(km);
  return k ? wmaStandard(gender, k, age) : null;
}

function getTier(pct) {
  const row = TIER_BOUNDS.find((r) => pct >= r[0]) || TIER_BOUNDS[TIER_BOUNDS.length - 1];
  return { bound: row[0], label: row[1], desc: row[2], cardDesc: row[3] };
}

// 거리별로 현실적인 기록 범위. 랭킹 화면과 같은 경계를 쓴다.
// 아래값은 세계기록보다 조금 느슨하게 잡아 정상 기록이 막히지 않게 한다.
const PLAUSIBLE_SECONDS = [
  [5, 720, 5400], [10, 1500, 9000], [21.0975, 3300, 18000], [42.195, 7000, 36000],
];
function plausibleRange(distanceKm) {
  const row = PLAUSIBLE_SECONDS.find(([km]) => Math.abs(km - distanceKm) < 0.05);
  return row ? [row[1], row[2]] : null;
}

function parseTimeToSeconds(text) {
  const parts = text.split(":").map(Number);
  if (parts.some(isNaN)) return null;
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  return null;
}

function formatPace(sec) {
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return `${m}:${String(s).padStart(2, "0")}/km`;
}

function analyze({ finishSec, distanceKm, age, gender }) {
  const actualPaceSec = finishSec / distanceKm;
  const speedKmh = distanceKm / (finishSec / 3600);

  // 연령등급 % 하나가 등급을 정한다. 거리마다 WMA 기준기록이 따로 있어서
  // 거리끼리 환산할 필요가 없다.
  const std = wmaStd(gender, distanceKm, age);
  const agePct = std ? (std / finishSec) * 100 : null;
  const tier = agePct === null ? null : getTier(agePct);

  return { actualPaceSec, speedKmh, agePct, tier };
}

function renderResult(result, inputs) {
  const el = document.getElementById("levelResult");
  const { actualPaceSec, speedKmh, tier } = result;
  const genderLabel = inputs.gender === "male" ? "남성" : "여성";

  el.innerHTML = `
    <div class="level-tier-badge">${tier.label}</div>
    <p class="level-tier-desc">${tier.desc}</p>
    <div class="level-stats">
      <div class="level-stat"><span class="level-stat-label">페이스</span><span class="level-stat-value">${formatPace(actualPaceSec)}</span></div>
      <div class="level-stat"><span class="level-stat-label">시속</span><span class="level-stat-value">${speedKmh.toFixed(1)}km/h</span></div>
      <div class="level-stat"><span class="level-stat-label">비교 기준</span><span class="level-stat-value">${inputs.age}세 ${genderLabel}</span></div>
    </div>
    ${(() => {
      // ── 연령등급 숫자와 다음 등급까지 ──────────────────────────
      // 이 페이지는 WMA 연령등급 위에 서 있는데, 정작 그 숫자가 화면에
      // 없었다. 등급 이름만 보여 주면 "왜 그 등급인지" 알 수가 없다.
      // 계산은 이미 하고 있었고 공유 카드에만 쓰이던 값이다.
      const { agePct } = result;
      if (agePct == null) return "";
      const gap = gapToNextTier({ agePct, finishSec: inputs.finishSec,
        distanceKm: inputs.distanceKm, age: inputs.age, gender: inputs.gender });
      const target = gap ? inputs.finishSec - gap.diff : null;
      return `
      <div class="lv-grade">
        <div class="lv-grade-num">
          <span class="lv-grade-pct">${agePct.toFixed(1)}<i>%</i></span>
          <span class="lv-grade-cap">연령등급 · 100%가 세계기록 수준</span>
        </div>
        ${gap ? `
        <div class="lv-grade-next">
          <span class="lv-next-l">다음 등급 <b>${gap.label}</b> 까지</span>
          <span class="lv-next-v">${fmtGap(gap.diff)} 단축</span>
          <span class="lv-next-t">목표 기록 ${fmtClock(target)}</span>
        </div>` : `
        <div class="lv-grade-next">
          <span class="lv-next-l">가장 높은 구간입니다</span>
        </div>`}
      </div>`;
    })()}

    ${(() => {
      // ── 얼마를 줄이면 어떻게 바뀌나 ───────────────────────────
      // "더 열심히"는 측정이 안 된다. 1분을 줄이면 몇 %가 되는지
      // 보여 주면 목표가 숫자가 된다. 전부 WMA 기준표에서 나오는 값이라
      // 따로 추정하거나 지어내는 부분이 없다.
      const { agePct } = result;
      if (agePct == null) return "";
      const rows = [60, 120, 180, 300].map((cut) => {
        const t = inputs.finishSec - cut;
        if (t < 300) return null;
        const std = wmaStd(inputs.gender, inputs.distanceKm, inputs.age);
        if (!std) return null;
        const pct = (std / t) * 100;
        const tr = getTier(pct);
        return { cut, t, pct, label: tr.label, up: tr.label !== result.tier.label };
      }).filter(Boolean);
      if (!rows.length) return "";
      return `
      <p class="level-tier-table-title">기록을 줄이면 어떻게 바뀔까</p>
      <div class="lv-what">
        <div class="lv-what-row lv-what-head">
          <span>단축</span><span>기록</span><span>연령등급</span><span>등급</span>
        </div>
        ${rows.map((r) => `
        <div class="lv-what-row${r.up ? " up" : ""}">
          <span>${r.cut / 60}분</span>
          <span>${fmtClock(r.t)}</span>
          <span>${r.pct.toFixed(1)}%</span>
          <span>${r.label}${r.up ? " ↑" : ""}</span>
        </div>`).join("")}
      </div>`;
    })()}

    ${(() => {
      // ── 다른 거리로 환산하면 ─────────────────────────────────
      // 같은 연령등급을 받는 다른 거리의 기록이다. 예측이 아니라
      // 같은 기준으로 환산한 값이라는 점을 문구로 분명히 해 둔다.
      const others = [5, 10, 21.0975, 42.195].filter(
        (k) => Math.abs(k - inputs.distanceKm) > 0.01);
      const rows = others.map((k) => {
        const t = equivTime(inputs.finishSec, inputs.distanceKm, k,
                            inputs.age, inputs.gender);
        return t ? { k, t } : null;
      }).filter(Boolean);
      if (!rows.length) return "";
      return `
      <p class="level-tier-table-title">같은 수준이라면 다른 거리에서는</p>
      <div class="lv-equiv">
        ${rows.map((r) => `
        <div class="lv-equiv-c">
          <span class="lv-equiv-d">${distLabel(r.k)}</span>
          <span class="lv-equiv-t">${fmtClock(r.t)}</span>
        </div>`).join("")}
      </div>
      <p class="lv-equiv-note">지금 기록과 같은 연령등급이 되는 기록입니다.
      앞으로 그 거리를 뛰면 이 시간이 나온다는 뜻은 아닙니다 — 거리마다
      필요한 훈련이 다릅니다.</p>`;
    })()}

    <p class="level-tier-table-title">체력 수준 구간 (${inputs.age}세 ${genderLabel} ${distLabel(inputs.distanceKm)} 기준)</p>
    <div class="level-tier-table">
      ${TIER_BOUNDS.slice().reverse().map(([bound, label], i) => {
        const isCurrent = label === tier.label;
        return `<div class="level-tier-row${isCurrent ? " current" : ""}">` +
               `<span class="level-tier-step">${i + 1}</span><span>${label}</span></div>`;
      }).join("")}
    </div>
    <button type="button" class="lv-share-btn" id="lvShareBtn">📷 공유 카드 만들기</button>
    <p class="lv-share-hint">카드를 먼저 보여드립니다. 확인하고 저장하거나 공유하세요. 가입하지 않아도 되고, 이미지는 기기 안에서 만들어져 서버로 올라가지 않습니다.</p>
  `;
  el.style.display = "block";
  const shareBtn = document.getElementById("lvShareBtn");
  if (shareBtn) {
    shareBtn.addEventListener("click", () => shareCard(result, inputs, shareBtn));
  }
  el.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// ──────────────────────────────────────────────────────────────
// 공유 카드
//
// 이 페이지가 사이트에서 방문자가 가장 많은 곳인데(지난주 26명, 1위),
// 결과를 가지고 나갈 방법이 없었다. 버튼이라고는 "저장하고 랭킹에서
// 비교하기"(= 가입) 하나뿐이고, 방문자의 67%가 모바일이다.
// 가입을 요구하는 순간 거기서 끊긴다.
//
// 넣지 않은 것: 구간별 페이스(1km·2km…)와 네거티브 스플릿.
// 이 계산기는 완주 시간 하나만 받으므로 구간 기록이 존재하지 않는다.
// 그 자리에는 실제로 계산되는 거리별 환산 기록을 넣었다.
// 모든 처리는 브라우저 안에서 끝난다 — 서버로 아무것도 보내지 않는다.
// ──────────────────────────────────────────────────────────────

const CARD_W = 1200, CARD_H = 1200;

// 늘 같은 주소를 가리키므로 QR 을 미리 만들어 둔다.
// 런타임에 QR 라이브러리를 불러오지 않으려는 것 — 이 페이지는 유입 1위라
// 외부 스크립트를 하나라도 덜 얹는 편이 낫다.
const QR_PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAUoAAAFKCAAAAABeQknZAAADeElEQVR42u3dYW7CMAyA0Wbi/lfOLoA6GztRM973k4kNnhJpFm24LkmSJEmSJEmSJJ3SePfgXPar55ufRh/Lv76x9b39WE1doUSJEqVQokSJUh29PhiGbstPE+P2scpks/e9WZU2OEqUQokSJUqhPGnaif6nP4LPvZ9i8nNP5ROinvdmVdrgKFEKJUqUQony9Gmnp+jcE506KjOOVWmDoxRKlCiFEiVK005fozDF5GemvXOPVYkSJUqhRIkSpVCeOe30zAv5z3Zm+rXsuOfHqrTBUaIUSpQohRLl6dPObP5z+fts1l2rNq1KGxylUKJEKZQoUX7dtLP3fpfoNWg9ZwkMq9IGRymUKFEKJUqU39Ef37eTvyrs/lfP5mfkp5ie92FV2uAoUQolSpRCifL0aecKzj2VkwbyE0bPd492/12r0gZHiVIoUaJEKZTPn3aiRSeWnntves5pcyWbDY5SKFGiFEqUKL+kV3SKqXxnZ3TuuYI/rUxF696vVWmDo0QplChRohTKRxX+qCN/9dho+Wn3ZBOdxvKvxaq0wVGiFEqUKFEK5UnTzo5r1fLnELhvxwYXSpQoUSJAiRKlVkw7lTOhe65ay5+JcAXnsg+IrEobHCVKoUSJUihRHjntrJuFKrNL990/lU90rEobHCVKoUSJUihRnjTtdN8N0zNRVT4r6jmvwKq0wVGiFEqUKIUS5bdMOztOkc5PJz0c+TuRrEobHCVKoUSJEqVQPqpX/ikz+NgIPmO0zFbd5xWER0Or0gZHiVIoUaIUSpSHTzvrvsWmZ1KKzimVe35MOzY4SpRCiRKlUKL8j9NOfrLJT0BX+qeVU65n4RmuZLPBUaIUSpQohRLl4xs7/kj+1Of7l1r5FqDKrHaZdmxwlCiFEiVKoUR5+LQzl/3qdd84ev/c/JVs+YHQqrTBUaIUSpQoUQrlo3p9MAyl55TK9BSdSSrzUeX9WpU2OEqUQokSpVCiPHPaiU4T675bp3KCwCzMW/mTEKxKGxwlSqFEiRKlUJ457fQUnWKu4BSTv0en5zQD9+3Y4ChRCiVKlEKJ0rSTmToqn+NE78yZza/ZqrTBUaIUSpQohRLl6dNO5Vq1ynkAlc9xeq6Mm1alDY5SKFGiRCmUKE9sy5lsPff8VM6drsw47tuxwVEKJUqUKIUSpSRJkiRJkiRJkrS0X7asr1pj/piBAAAAAElFTkSuQmCC";
// 배지 안 러너. 직접 그리지 않고 Google Material Symbols 의 directions_run
// (Apache License 2.0 — 상업적 이용·수정 허용, 출처 표기 의무 없음) 을
// 미리 그림으로 구워 둔다. 경로를 캔버스에 직접 그리려면 Path2D 가 필요한데
// 지원이 고르지 않고, QR 과 같은 방식이라 코드도 한 가지로 맞출 수 있다.
const RUNNER_PNG = "data:image/png;base64,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";

// 통계 줄과 배지에 쓰는 글리프. Material Symbols Rounded(Apache-2.0)를
// 실제로 그려지는 크기에 맞춰 PNG 로 구워 두었다. node-canvas 에는
// Path2D 가 없어서 SVG 패스를 그대로 쓸 수 없다.
const ICON_PNG = {
  clock: "data:image/png;base64,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",
  trend: "data:image/png;base64,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",
  person: "data:image/png;base64,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",
  star: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABwAAAAcCAYAAAByDd+UAAAE3UlEQVR42q2WXWgUZxSGnzP7m2TNmjSJSWO0tRsDqeiFClqEpBAhQcGrNdA/KC0qZYOhsYig3eSmaqkScSMYqdBSvNj0rqYECtZAaS+qtWALiabGakyM+WlizO/szOnFbGPU/KzSD4aZYb5z3jnfed/3+4QUh6qCCGNffMzf4yMRQ4WiQDC27MBJUEVEUsrjThWQlhYEuDE5HllXuuY0wM2Ou2RCTFtaUk4jqVUHIvB9zdu8UZzXsSyQXgLK2KNJfr3XI9uPt8zOWWoYKf1WfRRVxe+TymAwo8SwEhiWRTCYgcvyVaoq1EdTSpUiIIgIm1blNc5dFEXYvDqvUUSgnv8HUONhRBpoP/hWyOv3lJCwQAEFsSx8Pm/Jz5+8GxJpQOPhJQFdCwIBRKOU5+VSX1qOP5tPg7lZW5iecZolAqq4gun4bVs/31rVRl4ulJZzub2dhoVIo6rOwyId/3rfdnat36CZaV5IWLNcs1Ux3C7Gpmb48Wqn7Pryu8VltRBLy9YWsPWV/FAov4BVuZmhjStXRLJzgjuYnH6WiqqQ5mNocKT1t54HsTsDD7u67vfxy+37Xe03+p6t8Nx7laHt60ONRZnpO0CwVbFtRVXRZOU+vw9Mc2Heq4LHw/TUNKqKJOMMQzBEAOXu6Hjr5et3auXByZqO3BXZJUwnHArp3CYq2ApqpyBZBTHAEGeuzFG6DfjcPLg/3Ol+NG125dpagm2DZT8G/G+2pOoPDolIKE8kEbDFwLCViRmzy9U7MnxhY+GKzVkvLV/rEILHLBSef8ic+GQuSfNxq6e/9di3P+ycTXnr6L7GV4tW7GdqBmw7NZ9a0g8NSPPS1d13qvhIc60ji+RHEaH3RCSSkx087bEVLOvFQVXB5cI0hIHh0ZrCuljMZRgkbDvZYhFUo7xcF4vdvfeganzGBJ/XCXwRMJ+XCTNBT89AVWFdLKYaxbJtZK61iTRw5eweXjt8ru1q173ih6Pjnbhd2M8BaquC28XYw/HO6929VWuONLfp2T2INMzvpZv2NqPxMGUnLnTd7BuKAUkdpWjMybmd/YOxLce/adN4GNnbvIR555aiqpSuzKnE6+EpnSytRa+HdYX5zpb1T1YKu0V5PSKCrYRw7s+xpI4MLMsKiQjsKVgcMB4OIyI0VVeELNsuwUw4rJqPGPP01hDATGBaVklTdUVIpIF4OLwwYPijUgDe2bYulJmd6fjnHPXbmrS6NL9z2U+5CgKmyfKcIO9v2xACWFORtciSDrwOwMjETAiP+4mCUMXwuCGQRm//YGtv/2ArAT+4k32ei+t2MzQ1FQLYmFWxMKBRvZtoWRmWbVUyYyYLUMQQCKQxMTnNn3d6awoPNO0sPNC08/dbfTUT45OdZKQ566m2E2OamGaiMlpWhlG9e/5Tmybd5s6JveQHgupxGc5f+32Y45P0jz469dWVjtrDLZdmN2tV5VDlNva9ub6xYHlgvyfdD1MzIJCwlb6xEVlVd3Y297wsHZtw4fF5IZABHjeDwyOd1273FRcdPFN7uOUS8XDY2StViYfDHG37idUHz9Re6+4rHhwe7cTjhkAGbq+HsQlXavT+o/6DyND5Qxf/+mxv5PFhKk40Gp2fsPH47Hv3sX2RgfOHLl5v+DDygj6saHTpM6dGo7PnlsXGv+MyHchZ26X3AAAAAElFTkSuQmCC",
};

const BG = "#0A0A0A", PANEL = "#141414", PANEL_2 = "#101010";
const LINE = "rgba(255,255,255,.07)";
const ACCENT = "#FF3D1A", ACCENT_DIM = "#8A2412";
const INK = "#FFFFFF", INK_SOFT = "#C9C2BE", INK_FAINT = "#7E7874";

function fmtClock(sec) {
  const s = Math.max(0, Math.round(sec));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), r = s % 60;
  return h ? `${h}:${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`
           : `${m}:${String(r).padStart(2, "0")}`;
}

// "0:23 남음" 은 페이스처럼 읽힌다. 남은 시간은 말로 쓴다.
function fmtGap(sec) {
  const s = Math.max(0, Math.round(sec));
  if (s < 60) return `${s}초`;
  const m = Math.floor(s / 60), r = s % 60;
  if (m < 60) return r ? `${m}분 ${r}초` : `${m}분`;
  const h = Math.floor(m / 60), rm = m % 60;
  return rm ? `${h}시간 ${rm}분` : `${h}시간`;
}

function distLabel(km) {
  if (Math.abs(km - 21.0975) < 0.05) return "하프마라톤";
  if (Math.abs(km - 42.195) < 0.05) return "풀코스";
  return `${km}km`;
}

// 다음(더 빠른) 등급까지 얼마나 줄여야 하는지. 이 페이지의 모델을
// 그대로 거꾸로 푼 값이라 화면에 보이는 등급과 어긋나지 않는다.
function gapToNextTier({ agePct, finishSec, distanceKm, age, gender }) {
  let next = null;
  for (let i = TIER_BOUNDS.length - 1; i >= 0; i--) {
    if (TIER_BOUNDS[i][0] > agePct) { next = TIER_BOUNDS[i]; break; }
  }
  if (!next) return null;                       // 이미 최상위 구간
  const std = wmaStd(gender, distanceKm, age);
  if (!std) return null;
  const needFinish = std / (next[0] / 100);     // 그 등급을 받는 가장 느린 기록
  const diff = finishSec - needFinish;
  if (!(diff > 0)) return null;
  return { label: next[1], diff };
}

// ── 그리기 도우미 ────────────────────────────────────────────
function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function setFont(ctx, weight, px) {
  ctx.font = `${weight} ${px}px "Noto Sans KR", sans-serif`;
}

// 라틴 문자는 한글 폰트의 영문 글리프가 어색해 별도 스택을 쓴다.
function setLatin(ctx, weight, px) {
  ctx.font = `${weight} ${px}px "Helvetica Neue", Helvetica, Arial, sans-serif`;
}

// letterSpacing 을 준 글자를 가운데 맞출 때 쓴다.
// 마지막 글자 뒤에도 간격이 붙어 그대로 재면 왼쪽으로 치우친다.
function centerTracked(ctx, text, cx, y, track) {
  ctx.textAlign = "left";
  ctx.letterSpacing = `${track}px`;
  const w = ctx.measureText(text).width - track;
  ctx.fillText(text, cx - w / 2, y);
  ctx.letterSpacing = "0px";
}

function fitFont(ctx, text, weight, startPx, maxWidth, minPx) {
  let px = startPx;
  for (;;) {
    setFont(ctx, weight, px);
    if (ctx.measureText(text).width <= maxWidth || px <= (minPx || 24)) break;
    px -= 3;
  }
  return px;
}

// 월계수.
// 잎을 한 점에서 방사형으로 뻗으면 부채처럼 보인다. 줄기의 접선을 구해
// 그 방향을 기준으로 잎을 눕혀야 가지로 읽힌다.
function laurel(ctx, x, y, h, dir, opts) {
  const o = opts || {};
  const color = o.color || ACCENT;
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(dir, 1);
  ctx.globalAlpha = o.alpha === undefined ? 1 : o.alpha;

  // 줄기: 2차 베지에. 바깥쪽(-x)으로 휜다.
  const P0 = [0, -h / 2], P1 = [-h * 0.34, 0], P2 = [0, h / 2];
  const at = (t) => [
    (1 - t) * (1 - t) * P0[0] + 2 * (1 - t) * t * P1[0] + t * t * P2[0],
    (1 - t) * (1 - t) * P0[1] + 2 * (1 - t) * t * P1[1] + t * t * P2[1],
  ];
  const tangent = (t) => [
    2 * (1 - t) * (P1[0] - P0[0]) + 2 * t * (P2[0] - P1[0]),
    2 * (1 - t) * (P1[1] - P0[1]) + 2 * t * (P2[1] - P1[1]),
  ];

  ctx.strokeStyle = color;
  ctx.lineWidth = Math.max(1.5, h * 0.016);
  ctx.lineCap = "round";
  ctx.globalAlpha *= 0.75;
  ctx.beginPath();
  ctx.moveTo(P0[0], P0[1]);
  ctx.quadraticCurveTo(P1[0], P1[1], P2[0], P2[1]);
  ctx.stroke();
  ctx.globalAlpha = o.alpha === undefined ? 1 : o.alpha;

  ctx.fillStyle = color;
  const N = 7;
  for (let i = 0; i < N; i++) {
    const t = 0.08 + (i / (N - 1)) * 0.84;
    const [px, py] = at(t);
    const [tx, ty] = tangent(t);
    const ang = Math.atan2(ty, tx);
    const taper = 0.62 + 0.38 * Math.sin(t * Math.PI);
    const len = h * 0.21 * taper, wid = h * 0.058 * taper;
    [-1, 1].forEach((side) => {
      const f = side < 0 ? 1 : 0.6;
      ctx.save();
      ctx.translate(px, py);
      ctx.rotate(ang + Math.PI + side * 0.72);
      ctx.beginPath();
      ctx.ellipse(len * f * 0.5, 0, len * f * 0.5, wid * f, 0, 0, Math.PI * 2);
      // 잎끼리 겹쳐 덩어리로 보이지 않도록 배경색으로 가장자리를 끊는다
      ctx.fillStyle = color;
      ctx.fill();
      ctx.strokeStyle = o.sep || "#0E0E10";
      ctx.lineWidth = Math.max(1.4, h * 0.016);
      ctx.stroke();
      ctx.restore();
    });
  }
  ctx.restore();
}

// CalRank 마크. 상승하는 랭크 막대 + 러너를 감싸는 링.
// Path2D는 구형 사파리에서 stroke가 비는 일이 있어 경로를 직접 그린다.
function drawEmblem(ctx, x, y, size, color) {
  const u = size / 64;
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(u, u);
  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  // 바깥 링 — 오른쪽 위를 틔워 트랙처럼 보이게
  ctx.strokeStyle = color;
  ctx.globalAlpha = 0.9;
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.arc(32, 32, 29, -Math.PI * 0.26, Math.PI * 1.62);
  ctx.stroke();
  ctx.globalAlpha = 0.28;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(32, 32, 23, 0, Math.PI * 2);
  ctx.stroke();
  ctx.globalAlpha = 1;

  // 올라가는 막대 3개
  ctx.fillStyle = color;
  const bars = [[18, 40, 7, 10], [28.5, 33, 7, 17], [39, 25, 7, 25]];
  bars.forEach(([bx, by, bw, bh], i) => {
    ctx.globalAlpha = 0.45 + i * 0.275;
    roundRect(ctx, bx, by, bw, bh, 3);
    ctx.fill();
  });
  ctx.globalAlpha = 1;

  // 링 끝을 마무리하는 점
  ctx.beginPath();
  ctx.arc(32 + 29 * Math.cos(-Math.PI * 0.26), 32 + 29 * Math.sin(-Math.PI * 0.26), 4.2, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

// 달리는 사람. 배지 안에 넣는다.
function runner(ctx, cx, cy, size, img) {
  if (!img) return;                       // 그림을 못 받으면 배지만 나온다
  ctx.drawImage(img, cx - size / 2, cy - size / 2, size, size);
}

// 작은 별. 배지 장식. Material Symbols 의 star 를 구워 쓴다.
function star(ctx, cx, cy, r, alpha, img) {
  if (!img) return;
  ctx.save();
  ctx.globalAlpha = alpha === undefined ? 1 : alpha;
  ctx.drawImage(img, cx - r, cy - r, r * 2, r * 2);
  ctx.restore();
}

// 모서리가 둥근 육각형. flatTop 이면 위아래가 평평하고 좌우에 꼭짓점이 온다.
function hexagon(ctx, cx, cy, r, corner) {
  const rad = corner === undefined ? r * 0.14 : corner;
  // 정육각형은 가로로 납작하다. 세로를 늘려 정사각에 가깝게 만든다.
  const rx = r * 0.92, ry = r * 1.06;
  const pts = [];
  for (let i = 0; i < 6; i++) {
    const a = i * Math.PI / 3;
    pts.push([cx + rx * Math.cos(a), cy + ry * Math.sin(a)]);
  }
  const mid = (p, q) => [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2];
  ctx.beginPath();
  ctx.moveTo.apply(ctx, mid(pts[5], pts[0]));
  for (let i = 0; i < 6; i++) {
    const cur = pts[i], nxt = pts[(i + 1) % 6], m = mid(cur, nxt);
    ctx.arcTo(cur[0], cur[1], m[0], m[1], rad);
    ctx.lineTo(m[0], m[1]);
  }
  ctx.closePath();
}

function iconCircle(ctx, cx, cy, r, kind, icons) {
  ctx.save();
  // 가운데가 밝은 원. 납작한 원보다 깊이가 생긴다.
  const g = ctx.createRadialGradient(cx, cy - r * 0.3, r * 0.1, cx, cy, r);
  g.addColorStop(0, "rgba(255,61,26,.26)");
  g.addColorStop(1, "rgba(255,61,26,.04)");
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.fillStyle = g; ctx.fill();
  ctx.strokeStyle = "rgba(255,110,70,.55)"; ctx.lineWidth = 1.8; ctx.stroke();

  // 글리프마다 잉크가 차지하는 비율이 달라서, 눈에 보이는 무게를 맞춰 키운다.
  const img = icons && icons[kind];
  if (img) {
    const s = r * (kind === "trend" ? 1.42 : kind === "person" ? 1.14 : 1.24);
    ctx.drawImage(img, cx - s / 2, cy - s / 2, s, s);
  }
  ctx.restore();
}


// ── 카드 본체 ────────────────────────────────────────────────
function drawCard(ctx, d) {
  if (!d.icons) d.icons = {};   // 그림을 못 받아도 카드는 나온다
  ctx.fillStyle = BG;
  ctx.fillRect(0, 0, CARD_W, CARD_H);
  const M = 28;
  ctx.fillStyle = PANEL_2;
  roundRect(ctx, M, M, CARD_W - M * 2, CARD_H - M * 2, 28);
  ctx.fill();
  ctx.strokeStyle = LINE; ctx.lineWidth = 2; ctx.stroke();

  const L = 72, R = CARD_W - 72;

  // ── 머리: 등급 ──────────────────────────────────────────
  // 배지를 뺀 왼쪽 영역 한가운데를 기준으로 모든 줄을 맞춘다.
  const bx = R - 156, by = 186, br = 126;
  const colR = bx - br - 26;
  const cxL = (L + colR) / 2;

  ctx.fillStyle = INK_FAINT;
  setLatin(ctx, 700, 22);
  centerTracked(ctx, "RUNNING PERFORMANCE GRADE", cxL, 116, 5);

  const tierPx = fitFont(ctx, d.tier, 900, 84, 430, 46);
  const tierW = ctx.measureText(d.tier).width;
  ctx.fillStyle = INK;
  ctx.textAlign = "center";
  ctx.fillText(d.tier, cxL, 202);

  // 짧은 제목에 큰 월계수를 붙이면 글자가 눌린다. 제목 폭에 맞춰 키운다.
  const lauH = Math.max(80, Math.min(112, tierW * 0.4));
  laurel(ctx, cxL - tierW / 2 - lauH * 0.36, 178, lauH, 1);
  laurel(ctx, cxL + tierW / 2 + lauH * 0.36, 178, lauH, -1);

  ctx.fillStyle = INK_SOFT;
  setFont(ctx, 400, 25);
  d.desc.forEach((line, i) => ctx.fillText(line, cxL, 262 + i * 36));
  ctx.textAlign = "left";

  // ── 머리: 단계 배지 ─────────────────────────────────────

  // 뒤쪽 발광
  const glow = ctx.createRadialGradient(bx, by, br * 0.2, bx, by, br * 1.75);
  glow.addColorStop(0, "rgba(255,61,26,.22)");
  glow.addColorStop(1, "rgba(255,61,26,0)");
  ctx.fillStyle = glow;
  ctx.beginPath(); ctx.arc(bx, by, br * 1.75, 0, Math.PI * 2); ctx.fill();

  // 배지 뒤 월계관 (은은하게)
  laurel(ctx, bx - br * 0.88, by + 6, br * 1.34, 1, { color: "#C04C2B", alpha: 0.26, sep: "#141416" });
  laurel(ctx, bx + br * 0.88, by + 6, br * 1.34, -1, { color: "#C04C2B", alpha: 0.26, sep: "#141416" });

  // 바깥 육각 — 두꺼운 테두리
  const gOuter = ctx.createLinearGradient(bx, by - br, bx, by + br);
  gOuter.addColorStop(0, "rgba(255,96,60,.34)");
  gOuter.addColorStop(1, "rgba(110,28,12,.26)");
  hexagon(ctx, bx, by, br, br * 0.17); ctx.fillStyle = gOuter; ctx.fill();
  ctx.strokeStyle = "#E8502A"; ctx.lineWidth = 7; ctx.stroke();

  // 안쪽 면 — 깊은 적갈색
  const gInner = ctx.createLinearGradient(bx, by - br, bx, by + br);
  gInner.addColorStop(0, "rgba(74,20,11,.96)");
  gInner.addColorStop(1, "rgba(30,9,5,.96)");
  hexagon(ctx, bx, by, br - 17, (br - 17) * 0.17);
  ctx.fillStyle = gInner; ctx.fill();

  // 안쪽 가는 선
  hexagon(ctx, bx, by, br - 27, (br - 27) * 0.17);
  ctx.strokeStyle = "rgba(255,130,95,.5)"; ctx.lineWidth = 2; ctx.stroke();

  runner(ctx, bx, by - 68, 64, d.runnerImg);

  // 별 — 러너 아래 양옆으로 3개씩, 바깥으로 갈수록 작아진다
  [-1, 1].forEach((sgn) => {
    [[40, 7, 1], [56, 5.4, 0.78], [70, 4, 0.5]].forEach(([dx, rr, al]) => {
      star(ctx, bx + sgn * dx, by - 30, rr, al, d.icons.star);
    });
  });

  ctx.textAlign = "center";
  ctx.fillStyle = "#FFFFFF";
  setFont(ctx, 900, 30);
  ctx.letterSpacing = "3px";
  ctx.fillText("LEVEL", bx, by + 10);
  ctx.letterSpacing = "0px";

  // 큰 숫자 — 강조색. 축이 흔들리지 않게 바깥 글자 없이 가운데 하나만 둔다.
  // '7단계 중 몇 번째'는 아래 '체력 수준 구간' 목록이 그대로 보여준다.
  const baseY = by + 94;
  const gNum = ctx.createLinearGradient(0, baseY - 70, 0, baseY);
  gNum.addColorStop(0, "#FF8A62");
  gNum.addColorStop(1, "#EF3C16");
  ctx.fillStyle = gNum;
  setFont(ctx, 900, 92);
  ctx.textAlign = "center";
  ctx.fillText(String(d.step), bx, baseY);
  ctx.textAlign = "left";

  // ── 기록 줄 ────────────────────────────────────────────
  const barY = 330, barH = 128;
  ctx.fillStyle = PANEL;
  roundRect(ctx, L, barY, R - L, barH, 18); ctx.fill();
  ctx.strokeStyle = LINE; ctx.lineWidth = 1.5; ctx.stroke();

  const cells = [
    ["완주 기록", d.finish, d.distance, "clock"],
    ["페이스", d.pace, "/km", "trend"],
    ["비교 기준", `${d.age}세`, d.genderLabel, "person"],
  ];
  const cw = (R - L) / 3;
  cells.forEach(([label, value, unit, icon], i) => {
    const x0 = L + i * cw;
    if (i) {
      ctx.strokeStyle = LINE; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(x0, barY + 26); ctx.lineTo(x0, barY + barH - 26); ctx.stroke();
    }
    iconCircle(ctx, x0 + 58, barY + barH / 2, 30, icon, d.icons);
    ctx.textAlign = "left";
    ctx.fillStyle = INK_FAINT;
    setFont(ctx, 400, 23);
    ctx.fillText(label, x0 + 102, barY + 50);
    ctx.fillStyle = INK;
    const vPx = fitFont(ctx, value, 900, 44, cw - 190, 26);
    ctx.fillText(value, x0 + 102, barY + 101);
    const vw = ctx.measureText(value).width;
    ctx.fillStyle = INK_SOFT;
    setFont(ctx, 400, 22);
    ctx.fillText(unit, x0 + 108 + vw, barY + 101);
  });

  // ── 왼쪽: 거리별 환산 ───────────────────────────────────
  const pY = 492, pH = 520, pW = (R - L - 28) / 2;
  ctx.fillStyle = PANEL;
  roundRect(ctx, L, pY, pW, pH, 18); ctx.fill();
  ctx.strokeStyle = LINE; ctx.lineWidth = 1.5; ctx.stroke();

  ctx.textAlign = "left";
  ctx.fillStyle = INK;
  setFont(ctx, 900, 27);
  ctx.fillText("거리별 환산 기록", L + 30, pY + 50);
  ctx.fillStyle = INK_FAINT;
  setFont(ctx, 400, 20);
  ctx.fillText("같은 체력이라면 이 정도", L + 30, pY + 82);

  const rowY0 = pY + 118, rowH = 62;
  d.equivalents.forEach((e, i) => {
    const y = rowY0 + i * rowH;
    if (e.current) {
      ctx.fillStyle = "rgba(255,61,26,.12)";
      roundRect(ctx, L + 18, y - 22, pW - 36, rowH - 10, 10); ctx.fill();
      ctx.strokeStyle = "rgba(255,61,26,.5)"; ctx.lineWidth = 1.5; ctx.stroke();
    }
    ctx.fillStyle = e.current ? ACCENT : INK_SOFT;
    setFont(ctx, e.current ? 900 : 400, 25);
    ctx.fillText(e.label, L + 38, y + 10);
    ctx.textAlign = "right";
    ctx.fillStyle = e.current ? ACCENT : INK;
    setFont(ctx, 900, 30);
    ctx.fillText(e.time, L + pW - 38, y + 11);
    ctx.textAlign = "left";
  });

  const spY = rowY0 + d.equivalents.length * rowH + 18;
  ctx.fillStyle = "rgba(255,61,26,.08)";
  roundRect(ctx, L + 18, spY, pW - 36, 86, 12); ctx.fill();
  iconCircle(ctx, L + 64, spY + 43, 26, "trend", d.icons);
  ctx.fillStyle = INK_FAINT;
  setFont(ctx, 400, 21);
  ctx.fillText("평균 속도", L + 106, spY + 33);
  ctx.fillStyle = INK;
  setFont(ctx, 900, 36);
  ctx.fillText(d.speed, L + 106, spY + 75);
  const spw = ctx.measureText(d.speed).width;
  ctx.fillStyle = INK_SOFT;
  setFont(ctx, 400, 20);
  ctx.fillText("km/h", L + 112 + spw, spY + 75);

  ctx.fillStyle = INK_FAINT;
  setFont(ctx, 400, 18);
  ctx.fillText("WMA 연령 기준표로 환산 · 실제 기록과 다를 수 있습니다", L + 30, pY + pH - 26);

  // ── 오른쪽: 체력 수준 구간 ──────────────────────────────
  const qX = L + pW + 28;
  ctx.fillStyle = PANEL;
  roundRect(ctx, qX, pY, pW, pH, 18); ctx.fill();
  ctx.strokeStyle = LINE; ctx.lineWidth = 1.5; ctx.stroke();

  ctx.fillStyle = INK;
  setFont(ctx, 900, 27);
  ctx.fillText("체력 수준 구간", qX + 30, pY + 50);
  ctx.fillStyle = INK_FAINT;
  setFont(ctx, 400, 20);
  ctx.fillText(`${d.age}세 ${d.genderLabel} ${d.distance} 기준`, qX + 30, pY + 82);

  const tY0 = pY + 104, tH = 44;
  const chipX = qX + 30, chipW = 44;
  d.tiers.forEach((t, i) => {
    const y = tY0 + i * tH, h = tH - 7;
    ctx.fillStyle = t.current ? ACCENT : "rgba(255,255,255,.035)";
    roundRect(ctx, qX + 18, y, pW - 36, h, 8); ctx.fill();

    // 레벨 번호 — 배지의 숫자와 같은 축으로 읽히도록 왼쪽에 고정폭으로 둔다
    ctx.fillStyle = t.current ? "rgba(255,255,255,.22)" : "rgba(255,255,255,.05)";
    roundRect(ctx, chipX, y + 6, chipW, h - 12, 7); ctx.fill();
    ctx.textAlign = "center";
    ctx.fillStyle = t.current ? "#FFFFFF" : INK_FAINT;
    setFont(ctx, 900, 19);
    ctx.fillText(String(t.step), chipX + chipW / 2, y + 26);

    ctx.textAlign = "left";
    ctx.fillStyle = t.current ? "#FFFFFF" : INK_SOFT;
    setFont(ctx, t.current ? 900 : 400, 22);
    ctx.fillText(t.label, chipX + chipW + 14, y + 26);
  });

  if (d.next) {
    const nY = tY0 + d.tiers.length * tH + 16;
    ctx.fillStyle = "rgba(255,61,26,.10)";
    roundRect(ctx, qX + 18, nY, pW - 36, 64, 10); ctx.fill();
    ctx.fillStyle = INK_SOFT;
    setFont(ctx, 400, 20);
    ctx.fillText(`'${d.next.label}'까지`, qX + 38, nY + 26);
    ctx.fillStyle = ACCENT;
    setFont(ctx, 900, 28);
    ctx.textAlign = "right";
    ctx.fillText(`${fmtGap(d.next.diff)} 남음`, qX + pW - 38, nY + 46);
    ctx.textAlign = "left";
  } else {
    // 최상위 구간이면 '다음 구간' 상자가 비어 구멍이 생긴다. 그 자리를 채운다.
    const nY = pY + pH - 92;
    ctx.fillStyle = "rgba(255,61,26,.10)";
    roundRect(ctx, qX + 22, nY, pW - 44, 70, 14); ctx.fill();
    ctx.strokeStyle = "rgba(255,61,26,.3)"; ctx.lineWidth = 1.5; ctx.stroke();
    ctx.fillStyle = ACCENT;
    setFont(ctx, 900, 26);
    ctx.fillText("최고 구간", qX + 38, nY + 44);
    ctx.fillStyle = INK_SOFT;
    setFont(ctx, 400, 20);
    ctx.textAlign = "right";
    ctx.fillText("더 올라갈 구간이 없습니다", qX + pW - 38, nY + 44);
    ctx.textAlign = "left";
  }

  // ── 꼬리말 ────────────────────────────────────────────
  const fY = 1020;
  ctx.strokeStyle = LINE; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(L, fY); ctx.lineTo(R, fY); ctx.stroke();

  drawEmblem(ctx, L, fY + 26, 74, ACCENT);
  ctx.fillStyle = INK;
  setFont(ctx, 900, 38);
  ctx.letterSpacing = "5px";
  ctx.fillText("CALRANK", L + 92, fY + 70);
  ctx.letterSpacing = "0px";
  ctx.fillStyle = ACCENT;
  setFont(ctx, 700, 18);
  ctx.fillText("calrank.vercel.app", L + 92, fY + 98);

  ctx.fillStyle = INK_FAINT;
  setFont(ctx, 400, 17);
  ctx.textAlign = "right";
  [
    `연령등급 ${d.agePct}% · WMA 2025 연령 기준표`,
    "공인 기록이 아닌 참고용입니다.",
  ].forEach((line, i) => ctx.fillText(line, R - 150, fY + 52 + i * 24));

  ctx.fillStyle = INK_SOFT;
  setFont(ctx, 700, 19);
  ctx.fillText("내 기록도 확인하기", R - 150, fY + 102);
  ctx.textAlign = "left";

  // QR — 카카오톡에 올린 그림을 보고 바로 들어올 수 있게
  if (d.qr) {
    const qs = 96;
    ctx.fillStyle = "#FFFFFF";
    roundRect(ctx, R - qs - 6, fY + 22, qs + 12, qs + 12, 8);
    ctx.fill();
    ctx.drawImage(d.qr, R - qs, fY + 28, qs, qs);
  }
}

// ── 데이터 ──────────────────────────────────────────────────
// 같은 연령등급을 다른 거리에서 내려면 몇 분이 걸리는지.
// Riegel 환산식 대신 WMA 기준기록끼리의 비율을 쓴다. 네 거리 모두 WMA가
// 직접 산출한 값이라, 경험식으로 메우는 것보다 실제 기록 분포에 가깝다.
function equivTime(finishSec, fromKm, toKm, age, gender) {
  const a = wmaStd(gender, fromKm, age), b = wmaStd(gender, toKm, age);
  if (!a || !b) return finishSec * (toKm / fromKm);
  return finishSec * (b / a);
}

const EQUIV_DISTANCES = [[5, "5km"], [10, "10km"], [21.0975, "하프"], [42.195, "풀코스"]];

function cardData(result, inputs) {
  const { finishSec, distanceKm, age, gender } = inputs;
  const next = gapToNextTier({ agePct: result.agePct, finishSec, distanceKm, age, gender });

  // TIER_BOUNDS 는 빠른 순서다. 카드에는 느린 쪽부터 쌓아 올린다.
  const slowFirst = TIER_BOUNDS.slice().reverse();
  const idx = slowFirst.findIndex(([, label]) => label === result.tier.label);

  return {
    tier: result.tier.label,
    desc: clampLines(wrapKo(result.tier.cardDesc || result.tier.desc, 25), 2),
    step: idx + 1,
    agePct: result.agePct === null ? "–" : result.agePct.toFixed(1),
    steps: slowFirst.length,
    distance: distLabel(distanceKm),
    finish: fmtClock(finishSec),
    pace: formatPace(result.actualPaceSec).replace("/km", ""),
    speed: result.speedKmh.toFixed(1),
    age,
    genderLabel: gender === "male" ? "남성" : "여성",
    equivalents: EQUIV_DISTANCES.map(([km, label]) => ({
      label,
      time: fmtClock(Math.abs(km - distanceKm) < 0.05 ? finishSec
                                                      : equivTime(finishSec, distanceKm, km, age, gender)),
      current: Math.abs(km - distanceKm) < 0.05,
    })),
    tiers: slowFirst.map(([, label], i) => ({ label, step: i + 1, current: label === result.tier.label })),
    next,
  };
}

// 두 줄을 넘기면 문장이 "…볼" 처럼 어중간하게 끊긴다. 말줄임으로 끝맺는다.
function clampLines(lines, max) {
  if (lines.length <= max) return lines;
  const kept = lines.slice(0, max);
  kept[max - 1] = kept[max - 1].replace(/[\s.]+$/, "") + "…";
  return kept;
}

// 설명 문장을 카드 폭에 맞춰 두 줄로 나눈다 (한글은 단어 단위로 끊는다)
function wrapKo(text, perLine) {
  const words = String(text || "").split(" ");
  const lines = []; let cur = "";
  for (const w of words) {
    if ((cur + " " + w).trim().length > perLine && cur) { lines.push(cur.trim()); cur = w; }
    else cur = (cur + " " + w).trim();
  }
  if (cur) lines.push(cur);
  return lines;
}

// 약속이 끝나지 않으면 버튼이 "카드 만드는 중…" 에서 그대로 멈춘다.
// 단계마다 시간 제한을 두고, 지나면 포기하고 다음으로 넘어간다.
function withTimeout(p, ms, fallback) {
  return Promise.race([
    Promise.resolve(p).then((v) => v, () => fallback),
    new Promise((r) => setTimeout(() => r(fallback), ms)),
  ]);
}

function loadPng(src) {
  return withTimeout(new Promise((resolve) => {
    try {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => resolve(null);     // 그림이 없어도 카드는 나온다
      img.src = src;
    } catch (_) { resolve(null); }
  }), 3000, null);
}

// 한글 웹폰트는 유니코드 구간별로 수십 개 파일로 쪼개져 있다.
// 쓸 글자를 넘겨 필요한 구간만 받게 한다. 넘기지 않으면 전부 받으려 들고,
// 하나라도 안 끝나면 document.fonts.ready 가 영영 끝나지 않는다.
function ensureFonts(d) {
  if (!document.fonts || !document.fonts.load) return Promise.resolve(null);
  const sample = [
    d.tier, (d.desc || []).join(""), d.distance, d.genderLabel,
    (d.tiers || []).map((t) => t.label).join(""),
    (d.equivalents || []).map((e) => e.label).join(""),
    d.next ? d.next.label : "",
    "완주기록페이스비교기준거리별환산체력수준구간평균속도최고남음세남성여성초분시간",
  ].join("");
  return withTimeout(Promise.all([
    document.fonts.load('900 86px "Noto Sans KR"', sample),
    document.fonts.load('700 23px "Noto Sans KR"', sample),
    document.fonts.load('400 26px "Noto Sans KR"', sample),
  ]), 2500, null);
}

// toBlob 콜백을 끝내 부르지 않는 기기가 있다. 데이터 URL 로 우회한다.
function canvasToBlob(canvas) {
  return new Promise((resolve) => {
    let done = false;
    const finish = (b) => { if (!done) { done = true; resolve(b); } };
    const timer = setTimeout(() => {
      try {
        const base64 = canvas.toDataURL("image/png").split(",")[1];
        const bin = atob(base64);
        const arr = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
        finish(new Blob([arr], { type: "image/png" }));
      } catch (_) { finish(null); }
    }, 4000);
    try {
      canvas.toBlob((b) => { clearTimeout(timer); finish(b); }, "image/png");
    } catch (_) { clearTimeout(timer); finish(null); }
  });
}


async function buildCardBlob(d) {
  // 글꼴을 못 받아도 기본 글꼴로 그린다. 기다리다 멈추는 것보다 낫다.
  await ensureFonts(d);
  const kinds = Object.keys(ICON_PNG);
  const imgs = await Promise.all(
    [QR_PNG, RUNNER_PNG].concat(kinds.map((k) => ICON_PNG[k])).map(loadPng)
  );
  d.qr = imgs[0]; d.runnerImg = imgs[1];
  d.icons = {};
  kinds.forEach((k, i) => { d.icons[k] = imgs[i + 2]; });

  const canvas = document.createElement("canvas");
  canvas.width = CARD_W; canvas.height = CARD_H;
  drawCard(canvas.getContext("2d"), d);
  return canvasToBlob(canvas);
}


// 만든 카드를 먼저 보여준다.
//
// 전에는 버튼을 누르면 곧바로 운영체제 공유 시트가 떴다. 자기가 뭘 보내는지
// 못 본 채 보내게 되고, 데스크톱에서는 카카오톡이 "파일이 복사되었다"고만
// 하고 실제로 붙여넣기가 안 되는 일이 있었다. 미리 보여주고 저장과 공유를
// 고르게 하면, 안 되는 경로를 피해 저장 후 첨부로 갈 수 있다.
// 카카오톡으로 바로 보내기.
// 운영체제 공유 시트는 받는 앱이 무엇을 할지 우리가 통제할 수 없다.
// 카카오 SDK 를 쓰면 받는 사람을 고르는 즉시 전달된다. 다만 카카오는
// "메시지에 이미지를 넣으려면 카카오 서버에 올린 뒤 받은 URL 을 써야 한다"고
// 규정하므로, 누르기 전에 반드시 알리고 동의를 받는다.
//
// 이 페이지는 유입이 가장 많다. SDK 를 늘 불러오면 쓰지 않는 사람까지
// 값을 치르므로, 버튼을 누른 순간에만 내려받는다.
const KAKAO_KEY = "cfdf627cdfe54e49450a13c8ca8109aa";   // 공개용 JavaScript 키
const PAGE_URL = "https://calrank.vercel.app/level.html";
const KAKAO_SDK = "https://t1.kakaocdn.net/kakao_js_sdk/2.8.3/kakao.min.js";
// 카카오가 공개한 2.8.3 의 SRI 해시. 받은 파일이 이 해시와 다르면 브라우저가
// 실행을 거부한다. CDN 이 뚫리거나 중간에서 바꿔치기돼도 남의 코드가 이
// 페이지에서 돌지 않는다. SDK 버전을 올릴 때 이 값도 같이 바꿔야 한다.
// 출처: https://developers.kakao.com/docs/latest/ko/javascript/download
const KAKAO_SRI = "sha384-oroumrnFVE0xtgqyDZJARgERibXg2C28380uaUZz2kHDS5CR7tu20eGiOU6GkTpy";

function loadKakao() {
  return withTimeout(new Promise((resolve, reject) => {
    const ready = () => {
      try {
        if (!window.Kakao.isInitialized()) window.Kakao.init(KAKAO_KEY);
        resolve(window.Kakao);
      } catch (e) { reject(e); }
    };
    if (window.Kakao) { ready(); return; }
    const sc = document.createElement("script");
    sc.src = KAKAO_SDK;
    sc.integrity = KAKAO_SRI;
    sc.crossOrigin = "anonymous";   // integrity 는 CORS 로 받은 파일에만 걸린다
    sc.onload = ready;
    // 해시가 어긋나도 onerror 로 온다. 카카오 보내기만 막히고 저장·복사는 살아 있다.
    sc.onerror = () => reject(new Error("카카오 SDK 를 불러오지 못했습니다"));
    document.head.appendChild(sc);
  }), 9000, null);
}

// SDK 가 FileList 를 기대한다. File 하나를 FileList 로 감싼다.
function asFileList(file) {
  try {
    const dt = new DataTransfer();
    dt.items.add(file);
    return dt.files;
  } catch (_) { return [file]; }
}

let cardOverlay = null;

function closeCardPreview() {
  if (!cardOverlay) return;
  if (cardOverlay.dataset.url) URL.revokeObjectURL(cardOverlay.dataset.url);
  cardOverlay.remove();
  cardOverlay = null;
  document.removeEventListener("keydown", onPreviewKey);
  document.body.style.overflow = "";
}

function onPreviewKey(e) {
  if (e.key === "Escape") closeCardPreview();
}

function ensurePreviewStyle() {
  if (document.getElementById("lvPreviewStyle")) return;
  const st = document.createElement("style");
  st.id = "lvPreviewStyle";
  st.textContent = `
  .lvp-back{position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.93);
    -webkit-backdrop-filter:blur(3px);backdrop-filter:blur(3px);
    display:flex;align-items:center;justify-content:center;padding:18px;
    overflow-y:auto;-webkit-overflow-scrolling:touch;}
  .lvp-box{width:100%;max-width:420px;margin:auto;text-align:center;}
  .lvp-img{width:100%;height:auto;max-height:62vh;object-fit:contain;
    border-radius:14px;box-shadow:0 18px 50px rgba(0,0,0,.6);display:block;margin:0 auto;}
  .lvp-row{display:flex;flex-wrap:wrap;gap:10px;margin:16px 0 0;}
  .lvp-row button{flex:1 1 40%;padding:14px 10px;border:0;border-radius:10px;
    font-size:15px;font-weight:700;cursor:pointer;font-family:inherit;}
  .lvp-save{background:var(--accent,#FF3D1A);color:#fff;}
  .lvp-share{background:#fff;color:#111;}
  .lvp-copy{background:#2A2A2A;color:#fff;}
  .lvp-kakao{background:#FEE500;color:#191600;}
  .lvp-hint{font-size:12.5px;line-height:1.7;color:#B8B0AC;margin:14px 0 0;}
  .lvp-close{margin:12px 0 0;background:none;border:0;color:#9A9A9A;
    font-size:14px;cursor:pointer;font-family:inherit;padding:8px 14px;}
  `;
  document.head.appendChild(st);
}

function showCardPreview(blob, file, d) {
  ensurePreviewStyle();
  closeCardPreview();
  const url = URL.createObjectURL(blob);

  const back = document.createElement("div");
  back.className = "lvp-back";
  back.dataset.url = url;

  const canShare = !!(navigator.canShare && navigator.canShare({ files: [file] }));
  // 클립보드에 그림을 직접 넣을 수 있으면 그 길을 연다. 카카오톡 대화창에
  // Ctrl+V 로 바로 붙으므로, 운영체제 공유 시트를 거치지 않아도 된다.
  const canCopy = !!(navigator.clipboard && window.ClipboardItem && navigator.clipboard.write);
  const box = document.createElement("div");
  box.className = "lvp-box";
  box.innerHTML =
    `<img class="lvp-img" alt="내 러닝 등급 카드" src="${url}">` +
    `<div class="lvp-row">` +
    `<button type="button" class="lvp-save">이미지 저장</button>` +
    (canCopy ? `<button type="button" class="lvp-copy">이미지 복사</button>` : "") +
    (canShare ? `<button type="button" class="lvp-share">공유하기</button>` : "") +
    `</div>` +
    `<div class="lvp-row"><button type="button" class="lvp-kakao">카카오톡으로 보내기</button></div>` +
    `<p class="lvp-hint">${canShare
      ? "이미지를 길게 눌러 저장할 수도 있습니다."
      : "복사한 뒤 카카오톡 대화창에 붙여넣기(Ctrl+V)하면 바로 전송됩니다."}</p>` +
    `<button type="button" class="lvp-close">닫기</button>`;
  back.appendChild(box);

  box.querySelector(".lvp-save").addEventListener("click", () => {
    const a = document.createElement("a");
    a.href = url; a.download = "calrank-내등급.png";
    document.body.appendChild(a); a.click(); a.remove();
  });

  const copyBtn = box.querySelector(".lvp-copy");
  if (copyBtn) {
    copyBtn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
        copyBtn.textContent = "복사했습니다";
      } catch (_) {
        copyBtn.textContent = "저장해 주세요";
      }
      setTimeout(() => { copyBtn.textContent = "이미지 복사"; }, 2200);
    });
  }

  const shareBtn = box.querySelector(".lvp-share");
  if (shareBtn) {
    // 여기서 부르면 사용자가 방금 누른 동작이라 공유가 막히지 않는다.
    shareBtn.addEventListener("click", async () => {
      try {
        await navigator.share({ files: [file], title: "내 러닝 등급" });
      } catch (err) {
        if (err && err.name !== "AbortError") {
          shareBtn.textContent = "저장해 주세요";
          setTimeout(() => { shareBtn.textContent = "공유하기"; }, 2000);
        }
      }
    });
  }

  const kakaoBtn = box.querySelector(".lvp-kakao");
  if (kakaoBtn) {
    kakaoBtn.addEventListener("click", async () => {
      const ok = window.confirm(
        "카카오톡으로 바로 보내려면 카드 이미지를 카카오 서버에 올려야 합니다.\n" +
        "올린 이미지는 주소를 아는 사람이면 볼 수 있고, 카카오가 최대 100일 뒤 지웁니다.\n\n" +
        "올리지 않고 보내려면 '이미지 저장'이나 '이미지 복사'를 쓰세요.\n\n" +
        "계속할까요?");
      if (!ok) return;

      const label = kakaoBtn.textContent;
      kakaoBtn.disabled = true;
      kakaoBtn.textContent = "올리는 중…";
      try {
        const K = await loadKakao();
        if (!K) throw new Error("카카오 SDK 를 불러오지 못했습니다");
        const res = await K.Share.uploadImage({ file: asFileList(file) });
        const infos = (res && (res.infos || res)) || {};
        const imageUrl = infos.original && infos.original.url;
        if (!imageUrl) throw new Error("이미지 주소를 받지 못했습니다");

        const link = { webUrl: PAGE_URL, mobileWebUrl: PAGE_URL };
        K.Share.sendDefault({
          objectType: "feed",
          content: {
            title: `${d.tier} — 내 ${d.distance} 기록 등급`,
            description: `${d.finish} · 페이스 ${d.pace}/km · ${d.age}세 ${d.genderLabel} 기준`,
            imageUrl,
            imageWidth: CARD_W,
            imageHeight: CARD_H,
            link,
          },
          buttons: [{ title: "내 등급 확인하기", link }],
        });
        kakaoBtn.textContent = "카카오톡을 확인하세요";
      } catch (err) {
        kakaoBtn.textContent = "보내지 못했습니다";
      }
      setTimeout(() => { kakaoBtn.textContent = label; kakaoBtn.disabled = false; }, 2600);
    });
  }

  box.querySelector(".lvp-close").addEventListener("click", closeCardPreview);
  back.addEventListener("click", (e) => { if (e.target === back) closeCardPreview(); });
  document.addEventListener("keydown", onPreviewKey);
  document.body.style.overflow = "hidden";
  document.body.appendChild(back);
  cardOverlay = back;
}

async function shareCard(result, inputs, btn) {
  const original = btn.textContent;
  const reset = (msg, wait) => {
    btn.textContent = msg;
    btn.disabled = false;
    if (wait) setTimeout(() => { btn.textContent = original; }, wait);
  };
  btn.disabled = true;
  btn.textContent = "카드 만드는 중…";
  try {
    // 단계마다 제한을 뒀지만, 그래도 안 끝나면 버튼은 돌려놓는다.
    const data = cardData(result, inputs);
    const blob = await withTimeout(buildCardBlob(data), 12000, null);
    if (!blob) throw new Error("이미지를 만들지 못했습니다");
    // 운영체제 공유 시트로 넘기는 파일은 이름을 영문으로만 쓴다.
    // 윈도우에서 한글 이름 파일을 넘기면 받는 앱이 경로를 못 읽어
    // "복사했다"고만 하고 실제로는 아무것도 전달되지 않는 일이 있다.
    // 내려받을 때 쓰는 이름은 따로 둔다(그쪽은 한글이 문제되지 않는다).
    const file = new File([blob], "calrank-grade.png", { type: "image/png" });
    showCardPreview(blob, file, data);
    reset(original);
  } catch (err) {
    reset("다시 시도해 주세요", 2500);
  }
}

function init() {
  document.getElementById("levelForm").addEventListener("submit", (e) => {
    e.preventDefault();

    const gender = document.getElementById("lvGender").value;
    const birthYear = parseInt(document.getElementById("lvBirthYear").value, 10);
    const distanceKm = parseFloat(document.getElementById("lvDistance").value);
    const timeText = document.getElementById("lvTime").value.trim();

    const finishSec = parseTimeToSeconds(timeText);
    if (!finishSec) {
      alert("완주시간 형식을 확인해 주세요. 예: 58:00 또는 1:45:30");
      return;
    }

    const range = plausibleRange(distanceKm);
    if (range && (finishSec < range[0] || finishSec > range[1])) {
      alert(
        `입력하신 기록이 ${distLabel(distanceKm)} 기록으로 보기 어렵습니다.\n` +
        `${fmtClock(range[0])} ~ ${fmtClock(range[1])} 사이로 다시 확인해 주세요.`
      );
      return;
    }

    const age = new Date().getFullYear() - birthYear;
    const result = analyze({ finishSec, distanceKm, age, gender });
    renderResult(result, { age, gender, finishSec, distanceKm });
  });
}

init();
