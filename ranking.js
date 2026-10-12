// calrank 대회랭킹 — 마스킹된 공개 랭킹 + 로그인 시 내 순위 근처
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
  // triathlon: 공식기록 크롤러가 아직 없어 실제 데이터가 전혀 없으므로, 소스가 마련될 때까지 탭을 숨깁니다.
};

let currentSport = "marathon";
let currentDistance = "10km";
let currentUser = null;

// 거리에 비해 사람이 낼 수 없는 기록은 보여 주지 않는다.
// 한계는 세계기록보다 조금 아래로 잡았다
// (마라톤 2:00:35, 하프 56:42, 10km 26:24, 5km 12:49 — 도로 세계기록).
// 수집 단계에도 같은 검증이 있지만, 이미 저장된 잘못된 기록이 화면에
// 올라오지 않도록 여기서 한 번 더 막는다. 실제로 1999~2001년 하프
// 기록이 풀코스로 들어가 1:05:23 이 "풀코스 최고 기록"으로 떠 있었다.
const PLAUSIBLE_SECONDS = {
  "full": [7000, 36000],
  "half": [3300, 18000],
  "10km": [1500, 9000],
  "5km": [720, 5400],
};

function isPlausible(row) {
  const sec = Number(row && row.finish_time_seconds);
  if (!Number.isFinite(sec) || sec <= 0) return false;
  const bounds = PLAUSIBLE_SECONDS[currentDistance] ||
                 PLAUSIBLE_SECONDS[row && row.distance_category];
  if (!bounds) return true;
  return sec >= bounds[0] && sec <= bounds[1];
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

function setupSportChips() {
  const wrap = document.getElementById("sportChipsR");
  wrap.innerHTML = "";
  Object.keys(DISTANCE_OPTIONS).forEach(sport => {
    const chip = document.createElement("button");
    chip.className = "chip" + (sport === currentSport ? " active" : "");
    chip.textContent = SPORT_LABEL[sport];
    chip.dataset.sport = sport;
    wrap.appendChild(chip);
  });

  wrap.addEventListener("click", (e) => {
    const btn = e.target.closest(".chip");
    if (!btn) return;
    currentSport = btn.dataset.sport;
    currentDistance = DISTANCE_OPTIONS[currentSport][0][0];
    setupSportChips();
    setupDistChips();
    loadRankings();
  });
}

function setupDistChips() {
  const wrap = document.getElementById("distChipsR");
  wrap.innerHTML = "";
  DISTANCE_OPTIONS[currentSport].forEach(([value, label]) => {
    const chip = document.createElement("button");
    chip.className = "chip" + (value === currentDistance ? " active" : "");
    chip.textContent = label;
    chip.dataset.dist = value;
    wrap.appendChild(chip);
  });

  wrap.addEventListener("click", (e) => {
    const btn = e.target.closest(".chip");
    if (!btn) return;
    currentDistance = btn.dataset.dist;
    setupDistChips();
    loadRankings();
  });
}

async function loadRankings() {
  const { data, error } = await sb.rpc("get_top_rankings", {
    p_sport: currentSport,
    p_distance: currentDistance,
    p_limit: 100,
  });

  if (error) {
    console.error(error);
    document.getElementById("rankList").innerHTML =
      `<div class="empty-state">랭킹을 불러오지 못했습니다.</div>`;
    return;
  }

  const rows = (data || []).filter(isPlausible);
  renderPodiumAndList(rows);
  await loadMyContext();
}

function renderPodiumAndList(rows) {
  const podium = document.getElementById("podium");
  const list = document.getElementById("rankList");
  podium.innerHTML = "";
  list.innerHTML = "";

  if (rows.length === 0) {
    podium.style.display = "none";
    list.innerHTML = `<div class="empty-state">아직 이 종목/거리에 등록된 기록이 없습니다. 첫 기록의 주인공이 되어보세요!</div>`;
    return;
  }

  podium.style.display = "grid";
  const top3 = rows.slice(0, 3);
  const rest = rows.slice(3);

  const medalOrder = [1, 0, 2];
  medalOrder.forEach(idx => {
    const r = top3[idx];
    if (!r) return;
    const card = document.createElement("div");
    card.className = "podium-card" + (r.rank === 1 ? " podium-first" : "");
    card.innerHTML = `
      <p class="podium-rank">${r.rank}위</p>
      <p class="podium-name">${r.masked_name}${r.is_official ? ' <span class="official-badge">공식</span>' : ''}</p>
      <p class="podium-time">${formatSeconds(r.finish_time_seconds)}</p>
      <p class="podium-race">${r.race_year}년 · ${r.race_name}</p>
    `;
    podium.appendChild(card);
  });

  rest.forEach(r => {
    list.appendChild(buildRankRow(r));
  });
}

function buildRankRow(r) {
  const row = document.createElement("div");
  row.className = "rank-row" + (r.is_me ? " rank-row-me" : "");
  row.innerHTML = `
    <span class="rank-num">${r.rank}</span>
    <div class="rank-body">
      <p class="rank-name">${r.masked_name}${r.is_official ? ' <span class="official-badge">공식</span>' : ''}</p>
      <p class="rank-race">${r.race_year}년 · ${r.race_name}</p>
    </div>
    <span class="rank-time">${formatSeconds(r.finish_time_seconds)}</span>
  `;
  return row;
}

async function loadMyContext() {
  const contextCard = document.getElementById("myContextCard");
  const loginHint = document.getElementById("loginHint");

  const { data: { session } } = await sb.auth.getSession();
  if (!session?.user) {
    currentUser = null;
    contextCard.style.display = "none";
    loginHint.style.display = "block";
    return;
  }
  currentUser = session.user;
  loginHint.style.display = "none";

  const { data, error } = await sb.rpc("get_my_rank_context", {
    p_sport: currentSport,
    p_distance: currentDistance,
    p_above: 5,
    p_below: 5,
  });

  if (error || !data || data.length === 0) {
    contextCard.style.display = "none";
    return;
  }

  contextCard.style.display = "block";
  const list = document.getElementById("myContextList");
  list.innerHTML = "";
  data.forEach(r => list.appendChild(buildRankRow(r)));
}

// 종목별 최고 기록(챔피언)을 한눈에 보여준다. 필터를 조작하지 않아도
// "지금 여기 사람들이 얼마나 뛰고 있는지" 구경할 거리를 만들어 재방문을 유도한다.
async function loadChampions() {
  const grid = document.getElementById("championGrid");
  if (!grid) return;

  const targets = [];
  Object.keys(DISTANCE_OPTIONS).forEach(sport => {
    DISTANCE_OPTIONS[sport].forEach(([value, label]) => {
      targets.push({ sport, distance: value, label });
    });
  });

  const results = await Promise.all(targets.map(async (t) => {
    // 말이 안 되는 기록이 섞여 있을 수 있으니 여유 있게 받아 걸러낸다
    const { data } = await sb.rpc("get_top_rankings", {
      p_sport: t.sport, p_distance: t.distance, p_limit: 20,
    });
    const bounds = PLAUSIBLE_SECONDS[t.distance];
    const ok = (data || []).filter(r => {
      const sec = Number(r && r.finish_time_seconds);
      if (!Number.isFinite(sec) || sec <= 0) return false;
      return !bounds || (sec >= bounds[0] && sec <= bounds[1]);
    });
    return { ...t, top: ok[0] || null };
  }));

  grid.innerHTML = "";
  results.forEach(r => {
    if (!r.top) return; // 아직 기록이 없는 종목/거리는 건너뛴다
    const card = document.createElement("a");
    card.href = "#";
    card.className = "champion-card";
    card.dataset.sport = r.sport;
    card.dataset.dist = r.distance;
    card.innerHTML = `
      <p class="champion-sport">${SPORT_LABEL[r.sport]} · ${r.label}</p>
      <p class="champion-name">${r.top.masked_name}${r.top.is_official ? ' <span class="official-badge">공식</span>' : ''}</p>
      <p class="champion-time">${formatSeconds(r.top.finish_time_seconds)}</p>
    `;
    card.addEventListener("click", (e) => {
      e.preventDefault();
      currentSport = r.sport;
      currentDistance = r.distance;
      setupSportChips();
      setupDistChips();
      loadRankings();
      document.getElementById("podium")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    grid.appendChild(card);
  });

  if (!grid.children.length) {
    grid.innerHTML = '<p class="champion-empty">아직 등록된 기록이 없습니다. 첫 챔피언이 되어보세요!</p>';
  }
}

async function init() {
  setupSportChips();
  setupDistChips();
  await loadRankings();
  await loadChampions();
}

init();
