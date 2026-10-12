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
  [540, "초보/기초체력", "이제 막 시작하는 단계이거나 기초체력을 다지는 중이에요. 완주 자체가 의미 있는 시작입니다."],
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
    <button type="button" class="lv-share-btn" id="lvShareBtn">📷 이미지로 저장 · 공유하기</button>
    <p class="lv-share-hint">가입하지 않아도 됩니다. 이미지는 휴대폰 안에서 만들어지고 서버로 올라가지 않습니다.</p>
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
// 그래서 로그인 없이 결과를 이미지로 만들어 준다. 안드로이드·아이폰은
// 공유 시트로 바로 카카오톡에 올릴 수 있고, 데스크톱은 내려받는다.
// 모든 처리는 브라우저 안에서 끝난다 — 서버로 아무것도 보내지 않는다.
// ──────────────────────────────────────────────────────────────

const CARD_W = 1080, CARD_H = 1080;
const BG = "#0B0B0B", ACCENT = "#FF3D1A";
const INK = "#FFFFFF", INK_SOFT = "#B8B0AC", INK_FAINT = "#7A7470";

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
function gapToNextTier({ normalizedPace, finishSec, distanceKm, age, gender }) {
  const af = ageFactor(age), gf = GENDER_FACTOR[gender];
  let nextBound = null;
  for (let i = TIER_BOUNDS.length - 1; i >= 0; i--) {
    if (TIER_BOUNDS[i][0] < normalizedPace) { nextBound = TIER_BOUNDS[i]; break; }
  }
  if (!nextBound) return null;                       // 이미 최상위 구간
  const need10kPace = nextBound[0] * af * gf;        // 10km 환산 페이스(초/km)
  const need10kTime = need10kPace * 10;
  // riegelTime 의 역: t1 = t2 / (d2/d1)^1.06
  const needFinish = need10kTime / Math.pow(10 / distanceKm, 1.06);
  const diff = finishSec - needFinish;
  if (!(diff > 0)) return null;
  return { label: nextBound[1], diff };
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

// 긴 등급 이름이 카드 밖으로 나가지 않도록 폭에 맞춰 글자 크기를 줄인다
function fitFont(ctx, text, weight, startPx, maxWidth) {
  let px = startPx;
  do {
    ctx.font = `${weight} ${px}px "Noto Sans KR", sans-serif`;
    if (ctx.measureText(text).width <= maxWidth) break;
    px -= 4;
  } while (px > 28);
  return px;
}

function drawCard(ctx, d) {
  ctx.fillStyle = BG;
  ctx.fillRect(0, 0, CARD_W, CARD_H);
  ctx.fillStyle = ACCENT;
  ctx.fillRect(0, 0, CARD_W, 12);

  const cx = CARD_W / 2;
  ctx.textAlign = "center";

  // 거리 · 완주시간
  ctx.fillStyle = INK_SOFT;
  ctx.font = '700 40px "Noto Sans KR", sans-serif';
  ctx.fillText(`${d.distance} 완주`, cx, 170);

  ctx.fillStyle = INK;
  ctx.font = '900 150px "Noto Sans KR", sans-serif';
  ctx.fillText(d.finish, cx, 320);

  // 등급
  ctx.fillStyle = ACCENT;
  fitFont(ctx, d.tier, 900, 96, CARD_W - 160);
  ctx.fillText(d.tier, cx, 470);

  ctx.fillStyle = INK_FAINT;
  ctx.font = '400 34px "Noto Sans KR", sans-serif';
  ctx.fillText(`${d.age}세 ${d.genderLabel} 기준`, cx, 530);

  // 페이스 · 시속
  const boxY = 600, boxH = 150, gap = 24, boxW = (CARD_W - 160 - gap) / 2;
  [["페이스", d.pace], ["시속", d.speed]].forEach(([label, value], i) => {
    const x = 80 + i * (boxW + gap);
    ctx.fillStyle = "rgba(255,255,255,.05)";
    roundRect(ctx, x, boxY, boxW, boxH, 16);
    ctx.fill();
    ctx.fillStyle = INK_FAINT;
    ctx.font = '400 30px "Noto Sans KR", sans-serif';
    ctx.fillText(label, x + boxW / 2, boxY + 56);
    ctx.fillStyle = INK;
    ctx.font = '900 52px "Noto Sans KR", sans-serif';
    ctx.fillText(value, x + boxW / 2, boxY + 118);
  });

  // 다음 등급까지
  if (d.next) {
    ctx.fillStyle = "rgba(255,61,26,.10)";
    roundRect(ctx, 80, 790, CARD_W - 160, 120, 16);
    ctx.fill();
    ctx.fillStyle = INK_SOFT;
    ctx.font = '400 32px "Noto Sans KR", sans-serif';
    ctx.fillText(`'${d.next.label}'까지`, cx, 840);
    ctx.fillStyle = ACCENT;
    ctx.font = '900 54px "Noto Sans KR", sans-serif';
    ctx.fillText(`${fmtGap(d.next.diff)} 남음`, cx, 898);
  }

  // 꼬리말
  ctx.fillStyle = INK;
  ctx.font = '900 44px "Noto Sans KR", sans-serif';
  ctx.letterSpacing = "6px";
  ctx.fillText("CALRANK", cx, 1000);
  ctx.letterSpacing = "0px";
  ctx.fillStyle = INK_FAINT;
  ctx.font = '400 28px "Noto Sans KR", sans-serif';
  ctx.fillText("calrank.vercel.app · 나이·성별 보정 러닝 등급", cx, 1042);
}

async function buildCardBlob(d) {
  // 한글이 네모로 찍히지 않도록 글꼴이 실제로 올라온 뒤에 그린다
  try {
    await document.fonts.load('900 150px "Noto Sans KR"');
    await document.fonts.load('400 34px "Noto Sans KR"');
    await document.fonts.ready;
  } catch (_) { /* 글꼴을 못 받아도 기본 글꼴로 그린다 */ }

  const canvas = document.createElement("canvas");
  canvas.width = CARD_W; canvas.height = CARD_H;
  drawCard(canvas.getContext("2d"), d);
  return new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
}

function cardData(result, inputs) {
  const next = gapToNextTier({
    normalizedPace: result.normalizedPace,
    finishSec: inputs.finishSec,
    distanceKm: inputs.distanceKm,
    age: inputs.age,
    gender: inputs.gender,
  });
  return {
    distance: distLabel(inputs.distanceKm),
    finish: fmtClock(inputs.finishSec),
    tier: result.tier.label,
    age: inputs.age,
    genderLabel: inputs.gender === "male" ? "남성" : "여성",
    pace: formatPace(result.actualPaceSec),
    speed: `${result.speedKmh.toFixed(1)}km/h`,
    next,
  };
}

async function shareCard(result, inputs, btn) {
  const original = btn.textContent;
  btn.disabled = true;
  btn.textContent = "카드 만드는 중…";
  try {
    const blob = await buildCardBlob(cardData(result, inputs));
    if (!blob) throw new Error("이미지를 만들지 못했습니다");
    const file = new File([blob], "calrank-내등급.png", { type: "image/png" });

    // 모바일이 방문자의 3분의 2다. 공유 시트가 되면 그걸 먼저 쓴다.
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      await navigator.share({ files: [file], title: "내 러닝 등급" });
      btn.textContent = original;
      btn.disabled = false;
      return;
    }
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = file.name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
    btn.textContent = "✅ 저장했습니다";
    setTimeout(() => { btn.textContent = original; btn.disabled = false; }, 2500);
  } catch (err) {
    // 공유 시트에서 사용자가 취소한 경우는 오류가 아니다
    if (!(err && err.name === "AbortError")) {
      btn.textContent = "만들지 못했습니다";
      setTimeout(() => { btn.textContent = original; }, 2500);
    } else {
      btn.textContent = original;
    }
    btn.disabled = false;
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

    const age = new Date().getFullYear() - birthYear;
    const result = analyze({ finishSec, distanceKm, age, gender });
    renderResult(result, { age, gender, finishSec, distanceKm });
  });
}

init();
