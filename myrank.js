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

async function init() {
  setupAuthTabs();
  document.getElementById("authForm").addEventListener("submit", handleAuthSubmit);
  document.getElementById("signOutBtn").addEventListener("click", handleSignOut);
  document.getElementById("recordForm").addEventListener("submit", handleRecordSubmit);
  document.getElementById("rfSport").addEventListener("change", (e) => populateDistanceSelect(e.target.value));

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
