// calrank 내 랭크 — Supabase 연동
const SUPABASE_URL = "https://mlbzsqeoqlyvnyzeegeu.supabase.co";
const SUPABASE_KEY = "sb_publishable_byKae86vGA0M5NjoZC0ELw_NMkm8ObR";

const sb = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

const SPORT_LABEL = {
  marathon: "마라톤", cycling: "자전거", trail: "트레일", triathlon: "철인3종",
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

const DISTANCE_KM = {
  marathon: { "5km": 5, "10km": 10, "half": 21.1, "full": 42.2 },
  cycling: { "50km": 50, "100km": 100, "150km": 150, "200km+": 200 },
  trail: { "20km": 20, "50km": 50, "100km": 100 },
};

function getDistanceKm(sport, distance) {
  return (DISTANCE_KM[sport] || {})[distance] || null;
}

function formatPace(seconds, km) {
  if (!seconds || !km) return null;
  const paceSec = seconds / km;
  const m = Math.floor(paceSec / 60);
  const s = Math.round(paceSec % 60);
  return `${m}'${String(s).padStart(2, "0")}"/km`;
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
        setDateValue(`${yyyy}-${mm}-${dd}`);
      }
      if (result.durationSeconds) {
        setTimeSelectsFromSeconds(result.durationSeconds);
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

  populateDateSelects();
  populateTimeSelects();
  populateDistanceSelect(document.getElementById("rfSport").value);
  ["rfSport", "rfDistance", "rfHour", "rfMin", "rfSec"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("change", updateRecordPreview);
  });
  await loadRecords();
  setupClaimSearch();
  setupProfileToggle();
}

function formatSecondsToTime(sec) {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  return h > 0
    ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
    : `${m}:${String(s).padStart(2, "0")}`;
}

let claimSearchBound = false;
function setupClaimSearch() {
  if (claimSearchBound) return;
  claimSearchBound = true;
  const btn = document.getElementById("claimSearchBtn");
  const input = document.getElementById("claimSearchInput");
  if (!btn || !input) return;
  const run = () => runClaimSearch();
  btn.addEventListener("click", run);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") run(); });
}

async function runClaimSearch() {
  const input = document.getElementById("claimSearchInput");
  const resultsEl = document.getElementById("claimResults");
  const name = (input.value || "").trim();
  if (!name) { resultsEl.innerHTML = ""; return; }

  resultsEl.innerHTML = '<p class="record-msg">검색 중…</p>';

  const { data, error } = await sb
    .from("official_records")
    .select("id, race_name, race_year, distance_category, athlete_name, finish_time_seconds, claimed_by_user_id")
    .ilike("athlete_name", `%${name}%`)
    .limit(20);

  if (error || !data || data.length === 0) {
    resultsEl.innerHTML = '<p class="record-msg">검색 결과가 없습니다. 이름이 정확한지 확인해주세요.</p>';
    return;
  }

  resultsEl.innerHTML = data.map(r => {
    const claimedByMe = r.claimed_by_user_id === currentUser.id;
    const claimedByOther = r.claimed_by_user_id && !claimedByMe;
    const timeStr = formatSecondsToTime(r.finish_time_seconds);
    const btnHtml = claimedByOther
      ? '<span class="import-sub">이미 다른 사용자가 클레임한 기록입니다</span>'
      : claimedByMe
      ? `<button class="modal-cal-btn claim-action-btn" data-action="unclaim" data-id="${r.id}">클레임 취소</button>`
      : `<button class="record-submit-btn claim-action-btn" data-action="claim" data-id="${r.id}" style="width:auto; padding:0 16px;">이 기록이 내 기록이에요</button>`;
    return `<div class="record-item"><p>${r.race_name} (${r.race_year}) · ${r.distance_category} · ${r.athlete_name} · ${timeStr}</p>${btnHtml}</div>`;
  }).join("");

  resultsEl.querySelectorAll(".claim-action-btn").forEach(b => {
    b.addEventListener("click", async () => {
      const id = b.getAttribute("data-id");
      const action = b.getAttribute("data-action");
      if (action === "claim") {
        await sb.from("official_records").update({ claimed_by_user_id: currentUser.id }).eq("id", id);
      } else {
        await sb.from("official_records").update({ claimed_by_user_id: null }).eq("id", id);
      }
      runClaimSearch();
    });
  });
}

async function setupProfileToggle() {
  const toggle = document.getElementById("profilePublicToggle");
  const linkBox = document.getElementById("profileLinkBox");
  const linkText = document.getElementById("profileLinkText");
  if (!toggle) return;

  const { data: profile } = await sb
    .from("profiles")
    .select("profile_public")
    .eq("id", currentUser.id)
    .single();

  const isPublic = !!(profile && profile.profile_public);
  toggle.checked = isPublic;
  const profileUrl = `https://calrank.vercel.app/profile.html?id=${currentUser.id}`;
  if (isPublic) {
    linkBox.style.display = "block";
    linkText.textContent = profileUrl;
  }

  toggle.addEventListener("change", async () => {
    const newValue = toggle.checked;
    await sb.from("profiles").update({ profile_public: newValue }).eq("id", currentUser.id);
    if (newValue) {
      linkBox.style.display = "block";
      linkText.textContent = profileUrl;
    } else {
      linkBox.style.display = "none";
    }
  });
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

let editingRecordId = null;

function handleEditRecord(id) {
  const r = currentRecords.find(rec => String(rec.id) === String(id));
  if (!r) return;
  document.getElementById("rfName").value = r.race_name || "";
  setDateValue(r.race_date || "");
  document.getElementById("rfSport").value = r.sport;
  populateDistanceSelect(r.sport);
  document.getElementById("rfDistance").value = r.distance_category;
  setTimeSelectsFromSeconds(r.finish_time_seconds);
  document.getElementById("rfNotes").value = r.notes || "";
  updateRecordPreview();
  editingRecordId = id;
  document.getElementById("recordFormTitle").textContent = "기록 수정";
  document.getElementById("recordSubmitBtn").textContent = "수정 완료";
  document.getElementById("recordCancelBtn").style.display = "inline-block";
  document.getElementById("recordForm").scrollIntoView({ behavior: "smooth", block: "center" });
}

function cancelEditRecord() {
  editingRecordId = null;
  document.getElementById("recordForm").reset();
  document.getElementById("recordFormTitle").textContent = "대회 기록 추가";
  document.getElementById("recordSubmitBtn").textContent = "기록 추가";
  document.getElementById("recordCancelBtn").style.display = "none";
  populateDistanceSelect(document.getElementById("rfSport").value);
  const today = new Date();
  document.getElementById("rfYear").value = today.getFullYear();
  document.getElementById("rfMonth").value = String(today.getMonth() + 1).padStart(2, "0");
  document.getElementById("rfDay").value = String(today.getDate()).padStart(2, "0");
  setTimeSelectsFromSeconds(null);
  updateRecordPreview();
}

function populateDateSelects() {
  const yearSel = document.getElementById("rfYear");
  const monthSel = document.getElementById("rfMonth");
  const daySel = document.getElementById("rfDay");
  if (!yearSel || yearSel.options.length > 0) return;
  const nowY = new Date().getFullYear();
  for (let y = nowY + 1; y >= nowY - 10; y--) {
    const opt = document.createElement("option");
    opt.value = y; opt.textContent = y + "년";
    yearSel.appendChild(opt);
  }
  for (let m = 1; m <= 12; m++) {
    const opt = document.createElement("option");
    opt.value = String(m).padStart(2, "0"); opt.textContent = m + "월";
    monthSel.appendChild(opt);
  }
  for (let d = 1; d <= 31; d++) {
    const opt = document.createElement("option");
    opt.value = String(d).padStart(2, "0"); opt.textContent = d + "일";
    daySel.appendChild(opt);
  }
  const today = new Date();
  yearSel.value = today.getFullYear();
  monthSel.value = String(today.getMonth() + 1).padStart(2, "0");
  daySel.value = String(today.getDate()).padStart(2, "0");
}

function getDateValue() {
  const y = document.getElementById("rfYear").value;
  const m = document.getElementById("rfMonth").value;
  const d = document.getElementById("rfDay").value;
  return `${y}-${m}-${d}`;
}

function setDateValue(dateStr) {
  if (!dateStr) return;
  const [y, m, d] = dateStr.split("-");
  document.getElementById("rfYear").value = y;
  document.getElementById("rfMonth").value = m;
  document.getElementById("rfDay").value = d;
}

function populateTimeSelects() {
  const hourSel = document.getElementById("rfHour");
  const minSel = document.getElementById("rfMin");
  const secSel = document.getElementById("rfSec");
  if (!hourSel || hourSel.options.length > 0) return;
  [hourSel, minSel, secSel].forEach(sel => {
    const blank = document.createElement("option");
    blank.value = ""; blank.textContent = "-";
    sel.appendChild(blank);
  });
  for (let h = 0; h <= 30; h++) {
    const opt = document.createElement("option");
    opt.value = h; opt.textContent = String(h).padStart(2, "0") + "시";
    hourSel.appendChild(opt);
  }
  for (let m = 0; m <= 59; m++) {
    const optM = document.createElement("option");
    optM.value = m; optM.textContent = String(m).padStart(2, "0") + "분";
    minSel.appendChild(optM);
    const optS = document.createElement("option");
    optS.value = m; optS.textContent = String(m).padStart(2, "0") + "초";
    secSel.appendChild(optS);
  }
}

function getTimeSecondsFromSelects() {
  const h = document.getElementById("rfHour").value;
  const m = document.getElementById("rfMin").value;
  const s = document.getElementById("rfSec").value;
  if (h === "" || m === "" || s === "") return null;
  return Number(h) * 3600 + Number(m) * 60 + Number(s);
}

function setTimeSelectsFromSeconds(totalSeconds) {
  const hourSel = document.getElementById("rfHour");
  const minSel = document.getElementById("rfMin");
  const secSel = document.getElementById("rfSec");
  if (totalSeconds == null) {
    hourSel.value = ""; minSel.value = ""; secSel.value = "";
    return;
  }
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  hourSel.value = h; minSel.value = m; secSel.value = s;
}

function updateRecordPreview() {
  const previewEl = document.getElementById("recordPreview");
  if (!previewEl) return;
  const sport = document.getElementById("rfSport").value;
  const distance = document.getElementById("rfDistance").value;
  const seconds = getTimeSecondsFromSelects();
  if (!distance || seconds == null) {
    previewEl.textContent = "";
    return;
  }
  const distLabel = distanceLabel(sport, distance);
  const timeLabel = formatSeconds(seconds);
  const km = getDistanceKm(sport, distance);
  const pace = formatPace(seconds, km);
  previewEl.textContent = `예상 기록: ${distLabel} · ${timeLabel}` + (pace ? ` · 페이스 ${pace}` : "");
}

async function handleRecordSubmit(e) {
  e.preventDefault();
  const msgEl = document.getElementById("recordMsg");
  const name = document.getElementById("rfName").value.trim();
  const date = getDateValue();
  const sport = document.getElementById("rfSport").value;
  const distance = document.getElementById("rfDistance").value;
  const notes = document.getElementById("rfNotes").value.trim();

  const finishSeconds = getTimeSecondsFromSelects();

  const payload = {
    race_name: name,
    race_date: date,
    sport,
    distance_category: distance,
    finish_time_seconds: finishSeconds,
    notes: notes || null,
  };

  let error;
  if (editingRecordId) {
    ({ error } = await sb.from("personal_records").update(payload).eq("id", editingRecordId));
  } else {
    ({ error } = await sb.from("personal_records").insert({ user_id: currentUser.id, ...payload }));
  }

  if (error) {
    msgEl.textContent = "저장 실패: " + error.message;
    msgEl.className = "record-msg error";
    return;
  }

  msgEl.textContent = editingRecordId ? "기록이 수정되었습니다." : "기록이 저장되었습니다.";
  msgEl.className = "record-msg";
  e.target.reset();
  document.getElementById("importMsg").textContent = "";
  cancelEditRecord();
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
        <p class="rr-meta">${r.race_date} · ${distanceLabel(r.sport, r.distance_category)}${r.finish_time_seconds ? " · " + formatSeconds(r.finish_time_seconds) : ""}${(() => { const km = getDistanceKm(r.sport, r.distance_category); const pace = formatPace(r.finish_time_seconds, km); return pace ? " · " + pace : ""; })()}${r.notes ? " · " + r.notes : ""}</p>
      </div>
      <button class="rr-edit" data-id="${r.id}" aria-label="수정" style="margin-right:4px;">✏️</button>
        <button class="rr-delete" data-id="${r.id}" aria-label="삭제">✕</button>
    `;
    list.appendChild(row);
  });

  list.querySelectorAll(".rr-delete").forEach(btn => {
    btn.addEventListener("click", () => handleDeleteRecord(btn.dataset.id));
  });
  list.querySelectorAll(".rr-edit").forEach(btn => {
    btn.addEventListener("click", () => handleEditRecord(btn.dataset.id));
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

function getCertRecords() {
  return (currentRecords || []).filter(r => r.race_name && r.finish_time_seconds != null);
}

async function openCertModal() {
  const records = getCertRecords();
  const sel = document.getElementById("certRecordSelect");
  if (records.length === 0) {
    sel.innerHTML = '<option value="">등록된 완주 기록이 없습니다</option>';
    document.getElementById("certModalOverlay").classList.add("open");
    return;
  }
  sel.innerHTML = records.map((r, i) => {
    const label = `${r.race_name} · ${SPORT_LABEL[r.sport] || r.sport} ${distanceLabel(r.sport, r.distance_category)} · ${formatSeconds(r.finish_time_seconds)}`;
    return `<option value="${i}">${label}</option>`;
  }).join("");
  document.getElementById("certModalOverlay").classList.add("open");
  const canvas = document.getElementById("certCanvas");
  await drawCertificate(canvas, records[0]);
  sel.onchange = async () => {
    await drawCertificate(canvas, records[Number(sel.value)]);
  };
}

function closeCertModal() {
  document.getElementById("certModalOverlay").classList.remove("open");
}

function downloadCertificate() {
  const canvas = document.getElementById("certCanvas");
  canvas.toBlob(blob => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "calrank-certificate.png";
    a.click();
    URL.revokeObjectURL(url);
  }, "image/png");
}

async function drawCertificate(canvas, record) {
  const W = 1600, H = 1131;
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

  const PAPER = "#F7F3E8";
  const INK = "#1A1A1A";
  const INK_SOFT = "#6B6558";
  const ACCENT = "#FF3D1A";

  ctx.fillStyle = PAPER;
  ctx.fillRect(0, 0, W, H);

  const isEN = !!(document.getElementById("certLangToggle") || {}).checked;

  ctx.save();
  ctx.globalAlpha = 0.05;
  ctx.fillStyle = INK;
  ctx.font = "900 40px 'Black Han Sans'";
  ctx.translate(W / 2, H / 2);
  ctx.rotate(-Math.PI / 8);
  for (let y = -H; y < H; y += 90) {
    for (let x = -W; x < W; x += 320) {
      ctx.fillText("CALRANK", x, y);
    }
  }
  ctx.restore();

  ctx.strokeStyle = INK;
  ctx.lineWidth = 3;
  ctx.strokeRect(28, 28, W - 56, H - 56);
  ctx.strokeStyle = ACCENT;
  ctx.lineWidth = 1.5;
  ctx.strokeRect(40, 40, W - 80, H - 80);

  // corner flourishes
  ctx.strokeStyle = ACCENT;
  ctx.lineWidth = 2;
  const cl = 26, co = 40;
  [[co, co, 1, 1], [W - co, co, -1, 1], [co, H - co, 1, -1], [W - co, H - co, -1, -1]].forEach(([x, y, dx, dy]) => {
    ctx.beginPath();
    ctx.moveTo(x + cl * dx, y);
    ctx.lineTo(x, y);
    ctx.lineTo(x, y + cl * dy);
    ctx.stroke();
  });

  const cx = W / 2, sealY = 130, sealR = 46;
  ctx.save();
  ctx.strokeStyle = ACCENT;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.arc(cx, sealY, sealR, 0, Math.PI * 2);
  ctx.stroke();
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(cx, sealY, sealR - 8, 0, Math.PI * 2);
  ctx.stroke();
  // tick marks around seal ring
  for (let i = 0; i < 24; i++) {
    const a = (i / 24) * Math.PI * 2;
    const r1 = sealR + 6, r2 = sealR + 11;
    ctx.beginPath();
    ctx.moveTo(cx + Math.cos(a) * r1, sealY + Math.sin(a) * r1);
    ctx.lineTo(cx + Math.cos(a) * r2, sealY + Math.sin(a) * r2);
    ctx.lineWidth = 1.2;
    ctx.stroke();
  }
  ctx.fillStyle = ACCENT;
  ctx.beginPath();
  ctx.moveTo(cx - 20, sealY - 20);
  ctx.lineTo(cx + 20, sealY - 20);
  ctx.lineTo(cx + 8, sealY);
  ctx.lineTo(cx + 20, sealY + 20);
  ctx.lineTo(cx - 20, sealY + 20);
  ctx.lineTo(cx - 8, sealY);
  ctx.closePath();
  ctx.fill();
  ctx.restore();

  ctx.fillStyle = INK_SOFT;
  ctx.font = "bold 13px 'Noto Sans KR'";
  ctx.textAlign = "center";
  ctx.textBaseline = "alphabetic";
  ctx.fillText("C A L R A N K   O F F I C I A L", cx, sealY + sealR + 24);

  ctx.fillStyle = INK;
  ctx.font = isEN ? "900 44px 'Black Han Sans'" : "900 56px 'Black Han Sans'";
  ctx.fillText(isEN ? "CERTIFICATE OF COMPLETION" : "완 주 인 증 서", cx, 290);

  ctx.strokeStyle = INK_SOFT;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(cx - 90, 312);
  ctx.lineTo(cx + 90, 312);
  ctx.stroke();

  ctx.fillStyle = INK_SOFT;
  ctx.font = "16px 'Noto Sans KR'";
  ctx.fillText(isEN ? "This certifies that the athlete below has successfully completed the race" : "이 증서는 아래 러너가 다음 대회를 완주했음을 증명합니다", cx, 355);

  const nameInput = (document.getElementById("certNameInput") || {}).value || "";
  const name = (nameInput.trim() || (document.getElementById("displayName").textContent || "회원").trim());
  ctx.fillStyle = INK;
  ctx.font = "700 52px 'Noto Sans KR'";
  ctx.fillText(name, cx, 440);

  ctx.font = "22px 'Noto Sans KR'";
  ctx.fillStyle = INK;
  ctx.fillText(record.race_name, cx, 510);

  ctx.fillStyle = INK_SOFT;
  ctx.font = "16px 'Noto Sans KR'";
  const sportLabel = SPORT_LABEL[record.sport] || record.sport;
  const distLabel = distanceLabel(record.sport, record.distance_category);
  const dateLabel = record.race_date || "";
  ctx.fillText(`${sportLabel} · ${distLabel} · ${dateLabel}`, cx, 545);

  ctx.fillStyle = ACCENT;
  ctx.font = "900 72px 'Black Han Sans'";
  ctx.fillText(formatSeconds(record.finish_time_seconds), cx, 650);

  ctx.fillStyle = INK_SOFT;
  ctx.font = "13px 'Noto Sans KR'";
  ctx.fillText(isEN ? "FINISH TIME" : "완주 기록", cx, 675);

  const paceKm = getDistanceKm(record.sport, record.distance_category);
  const paceStr = formatPace(record.finish_time_seconds, paceKm);
  if (paceStr) {
    ctx.fillStyle = INK_SOFT;
    ctx.font = "18px 'Noto Sans KR'";
    ctx.fillText((isEN ? "Pace " : "페이스 ") + paceStr, cx, 705);
  }

  ctx.textAlign = "left";
  const today = new Date().toISOString().slice(0, 10);
  ctx.fillStyle = INK_SOFT;
  ctx.font = "12px 'Noto Sans KR'";
  ctx.fillText((isEN ? "Issued: " : "발급일: ") + today, 70, H - 70);
  const certId = `CR-${(record.race_name.length + record.finish_time_seconds).toString(16).toUpperCase()}`;
  ctx.fillText((isEN ? "Cert No: " : "인증번호: ") + certId, 70, H - 50);

  ctx.textAlign = "right";
  ctx.fillStyle = INK;
  ctx.font = "700 20px 'Black Han Sans'";
  ctx.fillText("CALRANK", W - 70, H - 60);
  ctx.fillStyle = INK_SOFT;
  ctx.font = "12px 'Noto Sans KR'";
  ctx.fillText("calrank.vercel.app", W - 70, H - 42);
  ctx.textAlign = "left";
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
  document.getElementById("recordCancelBtn").addEventListener("click", cancelEditRecord);

  document.getElementById("certBtn").addEventListener("click", openCertModal);
  document.getElementById("certModalClose").addEventListener("click", closeCertModal);
  document.getElementById("certModalOverlay").addEventListener("click", (e) => {
    if (e.target.id === "certModalOverlay") closeCertModal();
  });
  document.getElementById("certDownloadBtn").addEventListener("click", downloadCertificate);

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
