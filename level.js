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
// 넣지 않은 것: 구간별 페이스(1km·2km…)와 네거티브 스플릿.
// 이 계산기는 완주 시간 하나만 받으므로 구간 기록이 존재하지 않는다.
// 그 자리에는 실제로 계산되는 거리별 환산 기록을 넣었다.
// 모든 처리는 브라우저 안에서 끝난다 — 서버로 아무것도 보내지 않는다.
// ──────────────────────────────────────────────────────────────

const CARD_W = 1200, CARD_H = 1200;
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
function gapToNextTier({ normalizedPace, finishSec, distanceKm, age, gender }) {
  const af = ageFactor(age), gf = GENDER_FACTOR[gender];
  let nextBound = null;
  for (let i = TIER_BOUNDS.length - 1; i >= 0; i--) {
    if (TIER_BOUNDS[i][0] < normalizedPace) { nextBound = TIER_BOUNDS[i]; break; }
  }
  if (!nextBound) return null;                       // 이미 최상위 구간
  const need10kPace = nextBound[0] * af * gf;
  const needFinish = (need10kPace * 10) / Math.pow(10 / distanceKm, 1.06);
  const diff = finishSec - needFinish;
  if (!(diff > 0)) return null;
  return { label: nextBound[1], diff };
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

function fitFont(ctx, text, weight, startPx, maxWidth, minPx) {
  let px = startPx;
  for (;;) {
    setFont(ctx, weight, px);
    if (ctx.measureText(text).width <= maxWidth || px <= (minPx || 24)) break;
    px -= 3;
  }
  return px;
}

// 월계수 가지. 줄기에서 바깥쪽으로 잎을 하나씩 뻗는다.
// 잎이 서로 겹치면 부채꼴 덩어리로 보이므로 간격과 길이를 맞춰 둔다.
function laurel(ctx, x, y, h, dir) {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(dir, 1);
  ctx.strokeStyle = ACCENT;
  ctx.lineWidth = Math.max(2, h * 0.022);
  ctx.lineCap = "round";
  ctx.beginPath();
  ctx.moveTo(0, -h / 2);
  ctx.quadraticCurveTo(-h * 0.20, 0, 0, h / 2);
  ctx.stroke();

  ctx.fillStyle = ACCENT;
  const n = 5;
  const leafL = h * 0.105, leafW = h * 0.032;
  for (let i = 0; i < n; i++) {
    const t = (i + 0.5) / n;
    const py = -h / 2 + t * h;
    const stemX = -Math.sin(t * Math.PI) * h * 0.20;
    // 줄기에 수직으로 가까운 방향. 위쪽 잎은 위로, 아래쪽 잎은 아래로 눕는다.
    const ang = (t - 0.5) * 1.9;
    ctx.save();
    ctx.translate(stemX, py);
    ctx.rotate(ang);
    ctx.beginPath();
    ctx.ellipse(-leafL, 0, leafL, leafW, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }
  ctx.restore();
}

// style.css 의 마라톤 엠블럼과 같은 선. 로고 자리에 쓴다.
// Path2D 에 기대지 않고 직접 긋는다 — 어떤 렌더러에서도 같은 그림이 나온다.
const EMBLEM_LINES = [
  [[12, 48], [20, 44], [26, 33], [36, 30]],   // 코스 선
  [[41, 51], [41, 15]],                        // 결승 기둥
  [[41, 16], [54, 20], [41, 24]],              // 깃발
];

function drawEmblem(ctx, x, y, size, color) {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(size / 64, size / 64);
  ctx.strokeStyle = color;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  ctx.globalAlpha = 0.32;
  ctx.lineWidth = 1.8;
  ctx.beginPath();
  ctx.arc(32, 32, 29, 0, Math.PI * 2);
  ctx.stroke();

  ctx.globalAlpha = 1;
  ctx.lineWidth = 3.5;
  EMBLEM_LINES.forEach((pts) => {
    ctx.beginPath();
    pts.forEach(([px, py], i) => (i ? ctx.lineTo(px, py) : ctx.moveTo(px, py)));
    ctx.stroke();
  });

  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(12, 48, 2.8, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

function hexagon(ctx, cx, cy, r) {
  ctx.beginPath();
  for (let i = 0; i < 6; i++) {
    const a = -Math.PI / 2 + i * Math.PI / 3;
    const px = cx + r * Math.cos(a), py = cy + r * Math.sin(a);
    i ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
  }
  ctx.closePath();
}

function iconCircle(ctx, cx, cy, r, kind) {
  ctx.save();
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.fillStyle = "rgba(255,61,26,.10)";
  ctx.fill();
  ctx.strokeStyle = "rgba(255,61,26,.45)";
  ctx.lineWidth = 2;
  ctx.stroke();

  ctx.strokeStyle = ACCENT;
  ctx.fillStyle = ACCENT;
  ctx.lineWidth = 2.4;
  ctx.lineCap = "round";
  const u = r / 30;                       // 30px 기준으로 그린 뒤 비례시킨다
  if (kind === "clock") {                 // 스톱워치
    ctx.beginPath(); ctx.arc(cx, cy + 2 * u, 12 * u, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx - 5 * u, cy - 13 * u); ctx.lineTo(cx + 5 * u, cy - 13 * u); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx, cy + 2 * u); ctx.lineTo(cx, cy - 5 * u); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx, cy + 2 * u); ctx.lineTo(cx + 6 * u, cy + 4 * u); ctx.stroke();
  } else if (kind === "gauge") {          // 속도계
    ctx.beginPath(); ctx.arc(cx, cy + 5 * u, 12 * u, Math.PI, 0); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx, cy + 5 * u); ctx.lineTo(cx + 8 * u, cy - 4 * u); ctx.stroke();
    ctx.beginPath(); ctx.arc(cx, cy + 5 * u, 2.2 * u, 0, Math.PI * 2); ctx.fill();
  } else {                                // 사람
    ctx.beginPath(); ctx.arc(cx, cy - 6 * u, 5.5 * u, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.arc(cx, cy + 14 * u, 11 * u, Math.PI * 1.15, Math.PI * 1.85); ctx.stroke();
  }
  ctx.restore();
}


// ── 카드 본체 ────────────────────────────────────────────────
function drawCard(ctx, d) {
  ctx.fillStyle = BG;
  ctx.fillRect(0, 0, CARD_W, CARD_H);
  const M = 28;
  ctx.fillStyle = PANEL_2;
  roundRect(ctx, M, M, CARD_W - M * 2, CARD_H - M * 2, 28);
  ctx.fill();
  ctx.strokeStyle = LINE; ctx.lineWidth = 2; ctx.stroke();

  const L = 72, R = CARD_W - 72;

  // ── 머리: 등급 ──────────────────────────────────────────
  ctx.textAlign = "left";
  ctx.fillStyle = INK_FAINT;
  setFont(ctx, 700, 23);
  ctx.letterSpacing = "4px";
  ctx.fillText("RUNNING PERFORMANCE GRADE", L + 56, 118);
  ctx.letterSpacing = "0px";

  const tierPx = fitFont(ctx, d.tier, 900, 86, 470, 46);
  ctx.fillStyle = INK;
  ctx.fillText(d.tier, L + 56, 200);
  const tierW = ctx.measureText(d.tier).width;

  laurel(ctx, L + 30, 178, 110, 1);
  laurel(ctx, L + 56 + tierW + 34, 178, 110, -1);

  ctx.fillStyle = INK_SOFT;
  setFont(ctx, 400, 26);
  d.desc.forEach((line, i) => ctx.fillText(line, L + 56, 250 + i * 38));

  // ── 머리: 단계 배지 ─────────────────────────────────────
  const bx = R - 150, by = 190, br = 125;
  const g = ctx.createLinearGradient(bx, by - br, bx, by + br);
  g.addColorStop(0, "rgba(255,61,26,.30)");
  g.addColorStop(1, "rgba(255,61,26,.06)");
  hexagon(ctx, bx, by, br); ctx.fillStyle = g; ctx.fill();
  ctx.strokeStyle = ACCENT; ctx.lineWidth = 4; ctx.stroke();
  hexagon(ctx, bx, by, br - 14);
  ctx.strokeStyle = "rgba(255,61,26,.35)"; ctx.lineWidth = 2; ctx.stroke();

  drawEmblem(ctx, bx - 26, by - 100, 52, ACCENT);

  ctx.textAlign = "center";
  ctx.fillStyle = INK_SOFT;
  setFont(ctx, 700, 20);
  ctx.letterSpacing = "3px";
  ctx.fillText("LEVEL", bx, by - 10);
  ctx.letterSpacing = "0px";
  ctx.fillStyle = ACCENT;
  setFont(ctx, 900, 86);
  ctx.fillText(String(d.step), bx - 14, by + 62);
  const stepW = ctx.measureText(String(d.step)).width;
  ctx.fillStyle = INK_FAINT;
  setFont(ctx, 700, 32);
  ctx.textAlign = "left";
  ctx.fillText(`/${d.steps}`, bx - 14 + stepW / 2 + 8, by + 62);

  // ── 기록 줄 ────────────────────────────────────────────
  const barY = 330, barH = 128;
  ctx.fillStyle = PANEL;
  roundRect(ctx, L, barY, R - L, barH, 18); ctx.fill();
  ctx.strokeStyle = LINE; ctx.lineWidth = 1.5; ctx.stroke();

  const cells = [
    ["완주 기록", d.finish, d.distance, "clock"],
    ["페이스", d.pace, "/km", "gauge"],
    ["비교 기준", `${d.age}세`, d.genderLabel, "person"],
  ];
  const cw = (R - L) / 3;
  cells.forEach(([label, value, unit, icon], i) => {
    const x0 = L + i * cw;
    if (i) {
      ctx.strokeStyle = LINE; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(x0, barY + 26); ctx.lineTo(x0, barY + barH - 26); ctx.stroke();
    }
    iconCircle(ctx, x0 + 58, barY + barH / 2, 30, icon);
    ctx.textAlign = "left";
    ctx.fillStyle = INK_FAINT;
    setFont(ctx, 400, 23);
    ctx.fillText(label, x0 + 102, barY + 54);
    ctx.fillStyle = INK;
    const vPx = fitFont(ctx, value, 900, 44, cw - 190, 26);
    ctx.fillText(value, x0 + 102, barY + 97);
    const vw = ctx.measureText(value).width;
    ctx.fillStyle = INK_SOFT;
    setFont(ctx, 400, 22);
    ctx.fillText(unit, x0 + 108 + vw, barY + 97);
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
  iconCircle(ctx, L + 64, spY + 43, 26, "gauge");
  ctx.fillStyle = INK_FAINT;
  setFont(ctx, 400, 21);
  ctx.fillText("평균 속도", L + 106, spY + 36);
  ctx.fillStyle = INK;
  setFont(ctx, 900, 36);
  ctx.fillText(d.speed, L + 106, spY + 72);
  const spw = ctx.measureText(d.speed).width;
  ctx.fillStyle = INK_SOFT;
  setFont(ctx, 400, 20);
  ctx.fillText("km/h", L + 112 + spw, spY + 72);

  ctx.fillStyle = INK_FAINT;
  setFont(ctx, 400, 18);
  ctx.fillText("Riegel 환산식 기준 · 실제 기록과 다를 수 있습니다", L + 30, pY + pH - 26);

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
  ctx.fillText(`${d.age}세 ${d.genderLabel} 기준 · 10km 환산`, qX + 30, pY + 82);

  const tY0 = pY + 104, tH = 44;
  d.tiers.forEach((t, i) => {
    const y = tY0 + i * tH;
    if (t.current) {
      ctx.fillStyle = ACCENT;
      roundRect(ctx, qX + 18, y, pW - 36, tH - 7, 8); ctx.fill();
      ctx.fillStyle = "#fff";
      setFont(ctx, 900, 23);
    } else {
      ctx.fillStyle = "rgba(255,255,255,.035)";
      roundRect(ctx, qX + 18, y, pW - 36, tH - 7, 8); ctx.fill();
      ctx.fillStyle = INK_SOFT;
      setFont(ctx, 400, 22);
    }
    ctx.fillText(t.label, qX + 38, y + 26);
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
  setFont(ctx, 400, 18);
  ctx.textAlign = "right";
  [
    "나이·성별 차이를 근사 반영한 참고용 추정치이며,",
    "공식 통계나 의학적 판단이 아닙니다.",
  ].forEach((line, i) => ctx.fillText(line, R, fY + 58 + i * 26));
  ctx.textAlign = "left";
}

// ── 데이터 ──────────────────────────────────────────────────
const EQUIV_DISTANCES = [[5, "5km"], [10, "10km"], [21.0975, "하프"], [42.195, "풀코스"]];

function cardData(result, inputs) {
  const { finishSec, distanceKm, age, gender } = inputs;
  const next = gapToNextTier({ normalizedPace: result.normalizedPace, finishSec, distanceKm, age, gender });

  // TIER_BOUNDS 는 빠른 순서다. 카드에는 느린 쪽부터 쌓아 올린다.
  const slowFirst = TIER_BOUNDS.slice().reverse();
  const idx = slowFirst.findIndex(([, label]) => label === result.tier.label);

  return {
    tier: result.tier.label,
    desc: clampLines(wrapKo(result.tier.desc, 25), 2),
    step: idx + 1,
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
                                                      : riegelTime(finishSec, distanceKm, km)),
      current: Math.abs(km - distanceKm) < 0.05,
    })),
    tiers: slowFirst.map(([, label]) => ({ label, current: label === result.tier.label })),
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

async function buildCardBlob(d) {
  // 한글이 네모로 찍히지 않도록 글꼴이 실제로 올라온 뒤에 그린다
  try {
    await Promise.all([
      document.fonts.load('900 86px "Noto Sans KR"'),
      document.fonts.load('700 23px "Noto Sans KR"'),
      document.fonts.load('400 26px "Noto Sans KR"'),
    ]);
    await document.fonts.ready;
  } catch (_) { /* 글꼴을 못 받아도 기본 글꼴로 그린다 */ }

  const canvas = document.createElement("canvas");
  canvas.width = CARD_W; canvas.height = CARD_H;
  drawCard(canvas.getContext("2d"), d);
  return new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
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
      btn.textContent = original; btn.disabled = false;
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
