// calrank 내 랭크 — Supabase 연동
const SUPABASE_URL = "https://mlbzsqeoqlyvnyzeegeu.supabase.co";
const SUPABASE_KEY = "sb_publishable_byKae86vGA0M5NjoZC0ELw_NMkm8ObR";

const sb = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

const SPORT_LABEL = {
  marathon: "마라톤", cycling: "자전거", trail: "트레일",
  hyrox: "하이록스", triathlon: "철인3종",
};

const DISTANCE_OPTIONS = {
  marathon: [
    ["5km", "5km"], ["10km", "10km"], ["half", "하프(21.1km)"], ["full", "풀(42.2km)"],
  ],
  cycling: [
    ["50km", "50km"], ["100km", "100km"], ["150km", "150km(그란폰도)"], ["200km+", "200km 이상"],
  ],
  trail: [
    ["20km", "20km급"], ["50km", "50km급"], ["100km", "100km급"],
  ],
  hyrox: [
    ["open", "오픈(Open)"], ["pro", "프로(Pro)"],
  ],
  triathlon: [
    ["sprint", "스프린트"], ["olympic", "올림픽"], ["half70_3", "하프(70.3)"], ["full", "풀(아이언맨)"],
  ],
};

const TIER_BENCHMARKS = {
  marathon: {
    "5km": [[20 * 60, "상위권"], [25 * 60, "준수"], [Infinity, "완주"]],
    "10km": [[45 * 60, "상위권"], [55 * 60, "준수"], [Infinity, "완주"]],
    half: [[105 * 60, "상위권"], [120 * 60, "준수"], [Infinity, "완주"]],
    full: [[210 * 60, "엘리트"], [240 * 60, "상위권"], [270 * 60, "준수"], [Infinity, "완주"]],
  },
  hyrox: {
    open: [[75 * 60, "상위권"], [90 * 60, "준수"], [Infinity, "완주"]],
    pro: [[90 * 60, "상위권"], [110 * 60, "준수"], [Infinity, "완주"]],
  },
  triathlon: {
    sprint: [[75 * 60, "상위권"], [105 * 60, "준수"], [Infinity, "완주"]],
    olympic: [[150 * 60, "상위권"], [195 * 60, "준수"], [Infinity, "완주"]],
    half70_3: [[300 * 60, "상위권"], [390 * 60, "준수"], [Infinity, "완주"]],
    full: [[660 * 60, "상위권"], [810 * 60, "준수"], [Infinity, "완주"]],
  },
};

let currentUser = null;
let currentRecords = [];

function parseTimeToSeconds(text) {
  if (!text) return null;
  const parts = text.split(":").map(Number);
  if (parts.some(isNaN)) return null;
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  return null;
}

function formatSeconds(sec) {
  if (sec == null) return "-";
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  return h > 0
    ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
    : `${m}:${String(s).padStart(2, "0")}`;
}

function distanceLabel(sport, dist) {
  const opt = (DISTANCE_OPTIONS[sport] || []).find(([v]) => v === dist);
  return opt ? opt[1] : dist;
}

function getTier(sport, distance, seconds) {
  const bands = TIER_BENCHMARKS[sport]?.[distance];
  if (!bands || seconds == null) return null;
  for (const [limit, label] of bands) {
    if (seconds <= limit) return label;
  }
  return null;
}

function hasTimeTier(sport) {
  return sport === "marathon" || sport === "hyrox" || sport === "triathlon";
}

function populateDistanceSelect(sport) {
  const sel = document.getElementById("rfDistance");
  sel.innerHTML = "";
  (DISTANCE_OPTIONS[sport] || []).forEach(([value, label]) => {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = label;
    sel.appendChild(opt);
  });
}

function haversineMeters(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const toRad = (d) => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.asin(Math.sqrt(a));
}

function parseGpx(xmlDoc) {
  const points = Array.from(xmlDoc.getElementsByTagName("trkpt"));
  if (points.length < 2) return null;

  let distanceMeters = 0;
  let prevLat = null, prevLon = null;
  let startTime = null, endTime = null;

  for (const pt of points) {
    const lat = parseFloat(pt.getAttribute("lat"));
    const lon = parseFloat(pt.getAttribute("lon"));
    const timeEl = pt.getElementsByTagName("time")[0];
    const time = timeEl ? new Date(timeEl.textContent) : null;

    if (prevLat != null) {
      distanceMeters += haversineMeters(prevLat, prevLon, lat, lon);
    }
    prevLat = lat;
    prevLon = lon;

    if (time && !isNaN(time.getTime())) {
      if (!startTime) startTime = time;
      endTime = time;
    }
  }

  const nameEl = xmlDoc.getElementsByTagName("name")[0];
  const name = nameEl ? nameEl.textContent.trim() : null;

  return {
    distanceMeters,
    durationSeconds: startTime && endTime ? Math.round((endTime - startTime) / 1000) : null,
    startTime,
    name,
  };
}

function parseTcx(xmlDoc) {
  const laps = Array.from(xmlDoc.getElementsByTagName("Lap"));
  if (laps.length === 0) return null;

  let distanceMeters = 0;
  let durationSeconds = 0;

  laps.forEach(lap => {
    const distEl = lap.getElementsByTagName("DistanceMeters")[0];
    const timeEl = lap.getElementsByTagName("TotalTimeSeconds")[0];
    if (distEl) distanceMeters += parseFloat(distEl.textContent) || 0;
    if (timeEl) durationSeconds += parseFloat(timeEl.textContent) || 0;
  });

  const activityEl = xmlDoc.getElementsByTagName("Activity")[0];
  const idEl = activityEl ? activityEl.getElementsByTagName("Id")[0] : null;
  const startTime = idEl ? new Date(idEl.textContent) : null;
  const sportAttr = activityEl ? activityEl.getAttribute("Sport") : null;

  return {
    distanceMeters,
    durationSeconds: Math.round(durationSeconds),
    startTime: startTime && !isNaN(startTime.getTime()) ? startTime : null,
    name: sportAttr,
  };
}

function guessDistanceCategory(sport, km) {
  if (sport === "marathon") {
    if (km >= 40) return "full";
    if (km >= 19) return "half";
    if (km >= 8) return "10km";
    return "5km";
  }
  if (sport === "trail") {
    if (km >= 80) return "100km";
    if (km >= 35) return "50km";
    return "20km";
  }
  if (sport === "cycling") {
    if (km >= 180) return "200km+";
    if (km >= 120) return "150km";
    if (km >= 70) return "100km";
    return "50km";
  }
  return null;
}

function handleFileImport(e) {
  const file = e.target.files[0];
  if (!file) return;
  const msgEl = document.getElementById("importMsg");
  msgEl.textContent = "분석 중...";
  msgEl.className = "import-msg";

  const reader = new FileReader();
  reader.onload = (evt) => {
    try {
      const xmlDoc = new DOMParser().parseFromString(evt.target.result, "application/xml");
      if (xmlDoc.getElementsByTagName("parsererror").length > 0) {
        throw new Error("파일 형식을 읽을 수 없어요");
      }

      const isTcx = file.name.toLowerCase().endsWith(".tcx") || xmlDoc.getElementsByTagName("TrainingCenterDatabase").length > 0;
      const result = isTcx ? parseTcx(xmlDoc) : parseGpx(xmlDoc);

      if (!result || !result.distanceMeters) {
        throw new Error("거리/시간 정보를 찾지 못했어요");
      }

      const km = result.distanceMeters / 1000;
      const sport = document.getElementById("rfSport").value;
      const guessedDist = guessDistanceCategory(sport, km);

      if (result.name) document.getElementById("rfName").value = result.name;
      if (result.startTime) {
        const d = result.startTime;
        const yyyy = d.getFullYear();
        const mm = String(d.getMonth() + 1).padStart(2, "0");
        const dd = String(d.getDate()).padStart(2, "0");
        document.getElementById("rfDate").value = `${yyyy}-${mm}-${dd}`;
      }
      if (result.durationSeconds) {
        document.getElementById("rfTime").value = formatSeconds(result.durationSeconds);
      }
      if (guessedDist) {
        document.getElementById("rfDistance").value = guessedDist;
      }

      msgEl.textContent = `인식된 거리: ${km.toFixed(1)}km · 아래 폼을 확인하고 저장해주세요`;
      msgEl.className = "import-msg success";
    } catch (err) {
      msgEl.textContent = "가져오기 실패: " + err.message;
      msgEl.className = "import-msg error";
    }
  };
  reader.readAsText(file);
}

let authMode = "signin";

function setupAuthTabs() {
  document.querySelectorAll(".auth-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".auth-tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      authMode = tab.dataset.mode;
      document.getElementById("authSubmitBtn").textContent = authMode === "signin" ? "로그인" : "회원가입";
      document.getElementById("authMsg").textContent = "";
    });
  });
}

async function handleAuthSubmit(e) {
  e.preventDefault();
  const email = document.getElementById("authEmail").value.trim();
  const password = document.getElementById("authPassword").value;
  const msgEl = document.getElementById("authMsg");
  msgEl.textContent = "처리 중...";
  msgEl.className = "auth-msg";

  const { error } = authMode === "signin"
    ? await sb.auth.signInWithPassword({ email, password })
    : await sb.auth.signUp({ email, password });

  if (error) {
    msgEl.textContent = error.message;
    msgEl.className = "auth-msg error";
    return;
  }

  if (authMode === "signup") {
    msgEl.textContent = "가입 완료! 이메일 인증이 필요할 수 있습니다. 로그인해 주세요.";
    msgEl.className = "auth-msg";
    return;
  }

  await refreshSession();
}

async function handleSignOut() {
  await sb.auth.signOut();
  currentUser = null;
  currentRecords = [];
  showAuthSection();
}

function showAuthSection() {
  document.getElementById("authSection").style.display = "block";
  document.getElementById("dashSection").style.display = "none";
}

async function showDashSection() {
  document.getElementById("authSection").style.display = "none";
  document.getElementById("dashSection").style.display = "block";

  const { data: profile } = await sb
    .from("profiles")
    .select("display_name")
    .eq("id", currentUser.id)
    .single();

  document.getElementById("displayName").textContent =
    profile?.display_name || currentUser.email.split("@")[0];

  populateDistanceSelect(document.getElementById("rfSport").value);
  await loadRecords();
}

async function refreshSession() {
  const { data: { session } } = await sb.auth.getSession();
  if (session?.user) {
    currentUser = session.user;
    await showDashSection();
  } else {
    showAuthSection();
  }
}

async function loadRecords() {
  const { data, error } = await sb
    .from("personal_records")
    .select("*")
    .order("race_date", { ascending: false });

  if (error) {
    console.error(error);
    return;
  }
  currentRecords = data || [];
  renderTiers();
  renderRecordList();
}

async function handleRecordSubmit(e) {
  e.preventDefault();
  const msgEl = document.getElementById("recordMsg");
  const name = document.getElementById("rfName").value.trim();
  const date = document.getElementById("rfDate").value;
  const sport = document.getElementById("rfSport").value;
  const distance = document.getElementById("rfDistance").value;
  const timeText = document.getElementById("rfTime").value.trim();
  const notes = document.getElementById("rfNotes").value.trim();

  const finishSeconds = timeText ? parseTimeToSeconds(timeText) : null;
  if (timeText && finishSeconds == null) {
    msgEl.textContent = "완주시간 형식이 올바르지 않습니다. 예: 1:45:30 또는 19:30";
    msgEl.className = "record-msg error";
    return;
  }

  const { error } = await sb.from("personal_records").insert({
    user_id: currentUser.id,
    race_name: name,
    race_date: date,
    sport,
    distance_category: distance,
    finish_time_seconds: finishSeconds,
    notes: notes || null,
  });

  if (error) {
    msgEl.textContent = "저장 실패: " + error.message;
    msgEl.className = "record-msg error";
    return;
  }

  msgEl.textContent = "기록이 저장되었습니다.";
  msgEl.className = "record-msg";
  e.target.reset();
  document.getElementById("importMsg").textContent = "";
  populateDistanceSelect(document.getElementById("rfSport").value);
  await loadRecords();
}

async function handleDeleteRecord(id) {
  await sb.from("personal_records").delete().eq("id", id);
  await loadRecords();
}

function renderTiers() {
  const grid = document.getElementById("tierGrid");
  grid.innerHTML = "";

  const sportOrder = ["marathon", "hyrox", "triathlon", "cycling", "trail"];
  let hasAny = false;

  sportOrder.forEach(sport => {
    const distOptions = (DISTANCE_OPTIONS[sport] || []).map(([v]) => v);

    distOptions.forEach(dist => {
      const recs = currentRecords.filter(r => r.sport === sport && r.distance_category === dist);
      if (recs.length === 0) return;
      hasAny = true;

      const card = document.createElement("div");
      card.className = "tier-card";

      if (hasTimeTier(sport)) {
        const best = recs.filter(r => r.finish_time_seconds)
          .sort((a, b) => a.finish_time_seconds - b.finish_time_seconds)[0];
        if (!best) {
          card.innerHTML = `
            <p class="tier-sport">${SPORT_LABEL[sport]}</p>
            <p class="tier-dist">${distanceLabel(sport, dist)}</p>
            <span class="tier-badge tier-badge-plain">완주 ${recs.length}회</span>
          `;
        } else {
          const tier = getTier(sport, dist, best.finish_time_seconds);
          card.innerHTML = `
            <p class="tier-sport">${SPORT_LABEL[sport]}</p>
            <p class="tier-dist">${distanceLabel(sport, dist)}</p>
            <p class="tier-time">${formatSeconds(best.finish_time_seconds)}</p>
            <span class="tier-badge">${tier || "-"}</span>
          `;
        }
      } else {
        card.innerHTML = `
          <p class="tier-sport">${SPORT_LABEL[sport]}</p>
          <p class="tier-dist">${distanceLabel(sport, dist)}</p>
          <span class="tier-badge tier-badge-plain">완주 ${recs.length}회</span>
        `;
      }

      grid.appendChild(card);
    });
  });

  if (!hasAny) {
    grid.innerHTML = `<p class="tier-empty">대회 기록을 추가하면 종목별 기록이 여기 표시됩니다.</p>`;
  }
}

function renderRecordList() {
  const list = document.getElementById("recordList");
  const countEl = document.getElementById("recordCount");
  list.innerHTML = "";

  countEl.textContent = `${currentRecords.length}개 기록`;

  if (currentRecords.length === 0) {
    list.innerHTML = `<div class="empty-state">아직 저장된 기록이 없습니다.</div>`;
    return;
  }

  currentRecords.forEach(r => {
    const row = document.createElement("div");
    row.className = "record-row";
    row.innerHTML = `
      <span class="rr-tag">${SPORT_LABEL[r.sport] || r.sport}</span>
      <div class="rr-body">
        <p class="rr-name">${r.race_name}</p>
        <p class="rr-meta">${r.race_date} · ${distanceLabel(r.sport, r.distance_category)}${r.finish_time_seconds ? " · " + formatSeconds(r.finish_time_seconds) : ""}${r.notes ? " · " + r.notes : ""}</p>
      </div>
      <button class="rr-delete" data-id="${r.id}" aria-label="삭제">✕</button>
    `;
    list.appendChild(row);
  });

  list.querySelectorAll(".rr-delete").forEach(btn => {
    btn.addEventListener("click", () => handleDeleteRecord(btn.dataset.id));
  });
}

const SPORT_COLOR = {
marathon: "#FF3D1A", cycling: "#5B8DEF", trail: "#4CAF7D", hyrox: "#F2C230", triathlon: "#B37FEA",
};

function buildShareRows() {
const rows = [];
const sportOrder = ["marathon", "hyrox", "triathlon", "cycling", "trail"];
sportOrder.forEach(sport => {
const distOptions = (DISTANCE_OPTIONS[sport] || []).map(([v]) => v);
distOptions.forEach(dist => {
const recs = currentRecords.filter(r => r.sport === sport && r.distance_category === dist);
if (recs.length === 0) return;
if (hasTimeTier(sport)) {
const best = recs.filter(r => r.finish_time_seconds).sort((a, b) => a.finish_time_seconds - b.finish_time_seconds)[0];
rows.push({
sport,
sportLabel: SPORT_LABEL[sport],
distLabel: distanceLabel(sport, dist),
time: best ? formatSeconds(best.finish_time_seconds) : null,
tier: best ? (getTier(sport, dist, best.finish_time_seconds) || "-") : `완주 ${recs.length}회`,
});
} else {
rows.push({
sport,
sportLabel: SPORT_LABEL[sport],
distLabel: distanceLabel(sport, dist),
time: null,
tier: `완주 ${recs.length}회`,
});
}
});
});
return rows;
}

async function drawShareCard(canvas) {
const W = 720, H = 960;
const dpr = 2;
canvas.width = W * dpr;
canvas.height = H * dpr;
canvas.style.width = "100%";
canvas.style.height = "auto";
canvas.style.aspectRatio = `${W} / ${H}`;
const ctx = canvas.getContext("2d");
ctx.scale(dpr, dpr);

if (document.fonts && document.fonts.ready) {
try { await document.fonts.ready; } catch (e) {}
}

const grad = ctx.createLinearGradient(0, 0, 0, H);
grad.addColorStop(0, "#0B0B0B");
grad.addColorStop(1, "#141414");
ctx.fillStyle = grad;
ctx.fillRect(0, 0, W, H);

ctx.fillStyle = "#FF3D1A";
ctx.fillRect(0, 0, W, 6);

ctx.fillStyle = "#FFFFFF";
ctx.font = "40px 'Black Han Sans'";
ctx.textBaseline = "alphabetic";
ctx.fillText("CALRANK", 48, 92);

ctx.fillStyle = "#6A6A6A";
ctx.font = "13px 'Noto Sans KR'";
ctx.fillText("calrank.vercel.app", 48, 114);

const name = document.getElementById("displayName").textContent || "회원";
ctx.fillStyle = "#9A9A9A";
ctx.font = "16px 'Noto Sans KR'";
ctx.fillText(`${name}님의 기록`, 48, 160);

ctx.strokeStyle = "#2E2E2E";
ctx.beginPath();
ctx.moveTo(48, 182);
ctx.lineTo(W - 48, 182);
ctx.stroke();

const rows = buildShareRows();
let y = 236;

if (rows.length === 0) {
ctx.fillStyle = "#6A6A6A";
ctx.font = "15px 'Noto Sans KR'";
ctx.fillText("아직 등록된 기록이 없습니다.", 48, y);
}

rows.slice(0, 6).forEach(row => {
const color = SPORT_COLOR[row.sport] || "#9A9A9A";

ctx.fillStyle = color;
ctx.font = "bold 11px 'Noto Sans KR'";
ctx.fillText(row.sportLabel, 48, y);

ctx.fillStyle = "#DADADA";
ctx.font = "bold 18px 'Noto Sans KR'";
ctx.fillText(row.distLabel, 48, y + 28);

if (row.time) {
ctx.fillStyle = "#FFFFFF";
ctx.font = "34px 'Black Han Sans'";
ctx.fillText(row.time, 48, y + 70);
}

const badgeText = row.tier || "";
ctx.font = "bold 13px 'Noto Sans KR'";
const badgeWidth = ctx.measureText(badgeText).width + 24;
const badgeX = W - 48 - badgeWidth;
const badgeY = y + 16;
ctx.strokeStyle = color;
ctx.lineWidth = 1;
ctx.strokeRect(badgeX, badgeY - 20, badgeWidth, 30);
ctx.fillStyle = color;
ctx.fillText(badgeText, badgeX + 12, badgeY);

y += 108;
});

ctx.fillStyle = "#6A6A6A";
ctx.font = "12px 'Noto Sans KR'";
ctx.fillText("나만의 페이스, 나만의 랭크 — calrank", 48, H - 40);
}

async function openShareModal() {
document.getElementById("shareModalOverlay").classList.add("open");
const canvas = document.getElementById("shareCanvas");
await drawShareCard(canvas);
}

function closeShareModal() {
document.getElementById("shareModalOverlay").classList.remove("open");
}

function downloadShareCard() {
const canvas = document.getElementById("shareCanvas");
canvas.toBlob(blob => {
const url = URL.createObjectURL(blob);
const a = document.createElement("a");
a.href = url;
a.download = "calrank-my-record.png";
a.click();
URL.revokeObjectURL(url);
}, "image/png");
}

async function nativeShareCard() {
const canvas = document.getElementById("shareCanvas");
canvas.toBlob(async blob => {
const file = new File([blob], "calrank-my-record.png", { type: "image/png" });
if (navigator.canShare && navigator.canShare({ files: [file] })) {
try {
await navigator.share({
files: [file],
title: "CALRANK 내 기록",
text: "내 대회 기록을 확인해보세요! calrank.vercel.app",
});
} catch (e) {
/* 사용자가 공유를 취소한 경우 */
}
} else {
downloadShareCard();
}
}, "image/png");
}

async function init() {
  setupAuthTabs();
  document.getElementById("authForm").addEventListener("submit", handleAuthSubmit);
  document.getElementById("signOutBtn").addEventListener("click", handleSignOut);
  document.getElementById("recordForm").addEventListener("submit", handleRecordSubmit);
  document.getElementById("rfSport").addEventListener("change", (e) => populateDistanceSelect(e.target.value));
  document.getElementById("gpxFileInput").addEventListener("change", handleFileImport);
document.getElementById("shareBtn").addEventListener("click", openShareModal);
document.getElementById("shareModalClose").addEventListener("click", closeShareModal);
document.getElementById("shareModalOverlay").addEventListener("click", (e) => {
if (e.target.id === "shareModalOverlay") closeShareModal();
});
document.getElementById("shareDownloadBtn").addEventListener("click", downloadShareCard);
document.getElementById("shareNativeBtn").addEventListener("click", nativeShareCard);

  populateDistanceSelect("marathon");

  sb.auth.onAuthStateChange((_event, session) => {
    if (session?.user) {
      currentUser = session.user;
      showDashSection();
    } else {
      currentUser = null;
      showAuthSection();
    }
  });

  await refreshSession();
}

init();
