// calrank 내 체력 등급 확인 — 로그인 없이 바로 계산 (전부 브라우저에서 처리)

const AGE_ANCHORS = [
  [20, 0.90], [30, 0.93], [40, 0.96], [50, 1.00], [60, 1.10], [70, 1.25], [80, 1.45],
];

const GENDER_FACTOR = { male: 1.00, female: 1.11 };

// 오름차순(빠른 순): bound = 해당 등급의 '느린 쪽' 경계 (초/km)
const TIER_BOUNDS = [
  [240, "상당한 러너", "동호인 최상위권입니다. 이 페이스를 꾸준히 유지하는 것 자체가 훈련이 잘 되어 있다는 뜻이에요."],
  [270, "러닝 상급자", "동호인 사이에서도 확실히 빠른 편입니다. 대회에서 상위권을 노려볼 만한 수준이에요."],
  [300, "매우 좋은 편", "평균을 크게 웃도는 체력입니다. 꾸준한 훈련이 실제 기록으로 잘 전환되고 있어요."],
  [348, "상당히 좋은 편", "일반적인 동호인 평균을 확실히 넘어선 수준입니다. 운동을 꽤 하는 편이라고 볼 수 있어요."],
  [390, "평균 이상", "또래·동성 평균보다 좋은 편입니다. 꾸준히 달리고 계신 게 기록으로 드러나고 있어요."],
  [450, "보통", "일반적인 체력 수준입니다. 지금의 페이스도 꾸준히 유지하면 좋은 기반이 됩니다."],
  [540, "초보/기초체력", "이제 막 시작하는 단계이거나 기초체력을 다지는 중이에요. 완주 자체가 하미 있는 시작입니다."],
];

function riegelTime(t1Sec, d1Km, d2Km) {
  return t1Sec * Math.pow(d2Km / d1Km, 1.06);
}

function ageFactor(age) {
  if (age <= AGE_ANCHORS[0][0]) return AGE_ANCHORS[0][1];
  if (age >= AGE_ANCHORS[AGE_ANCHORS.length - 1][0]) return AGE_ANCHORS[AGE_ANCHORS.length - 1][1];
  for (let i = 0; i < AGE_ANCHORS.length - 1; i++) {
    const [a0, f0] = AGE_ANCHORS[i];
    const [a1, f1] = AGE_ANCHORS[i + 1];
    if (age >= a0 && age <= a1) {
      const ratio = (age - a0) / (a1 - a0);
      return f0 + (f1 - f0) * ratio;
    }
  }
}

function getTier(paceSecPerKm) {
  for (const [bound, label, desc] of TIER_BOUNDS) {
    if (paceSecPerKm <= bound) return { label, desc };
  }
  return { label: "초보/기초체력", desc: TIER_BOUNDS[TIER_BOUNDS.length - 1][2] };
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

  const equiv10kTime = riegelTime(finishSec, distanceKm, 10);
  const equiv10kPace = equiv10kTime / 10;

  const af = ageFactor(age);
  const gf = GENDER_FACTOR[gender];
  const normalizedPace = equiv10kPace / af / gf;

  const tier = getTier(normalizedPace);

  return { actualPaceSec, speedKmh, equiv10kPace, normalizedPace, tier };
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
    <p class="level-tier-table-title">체력 수준 구간 (${inputs.age}세 ${genderLabel} 기준, 10km 환산)</p>
    <div class="level-tier-table">
      ${TIER_BOUNDS.slice().reverse().map(([bound, label]) => {
        const isCurrent = label === tier.label;
        return `<div class="level-tier-row${isCurrent ? " current" : ""}"><span>${label}</span></div>`;
      }).join("")}
    </div>
  `;
  el.style.display = "block";
  el.scrollIntoView({ behavior: "smooth", block: "nearest" });
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

    const age = new Date().getFullYear() - birthYear;
    const result = analyze({ finishSec, distanceKm, age, gender });
    renderResult(result, { age, gender });
  });
}

init();
