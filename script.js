const SPORT_META = {
  marathon:   { label: "마라톤",  icon: "ti-run",     bg: "var(--marathon-bg)",   ink: "var(--marathon-ink)",   tint: "var(--marathon-tint)" },
  cycling:    { label: "자전거",  icon: "ti-bike",    bg: "var(--cycling-bg)",    ink: "var(--cycling-ink)",    tint: "var(--cycling-tint)" },
  trail:      { label: "트레일",  icon: "ti-mountain",bg: "var(--trail-bg)",      ink: "var(--trail-ink)",      tint: "var(--trail-tint)" },
  hyrox:      { label: "하이록스",icon: "ti-barbell", bg: "var(--hyrox-bg)",      ink: "var(--hyrox-ink)",      tint: "var(--hyrox-tint)" },
  triathlon:  { label: "철인3종", icon: "ti-swimming",bg: "var(--triathlon-bg)",  ink: "var(--triathlon-ink)",  tint: "var(--triathlon-tint)" },
};

const state = {
  events: [],
  sport: "all",
  month: "all",
  region: "all",
};

function daysUntil(dateStr) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(dateStr);
  return Math.round((target - today) / (1000 * 60 * 60 * 24));
}

function formatDate(dateStr, timeStr) {
  const d = new Date(dateStr);
  const days = ["일", "월", "화", "수", "목", "금", "토"];
  const timePart = timeStr && timeStr !== "미확인" ? ` ${timeStr}` : "";
  return `${d.getMonth() + 1}.${d.getDate()}(${days[d.getDay()]})${timePart}`;
}

function ddayInfo(ev) {
  if (!ev.regDeadline) return { label: "접수기간 미확인", urgent: false };
  const n = daysUntil(ev.regDeadline);
  return { label: n < 0 ? "접수 마감" : `접수 D-${n}`, urgent: n >= 0 && n <= 7 };
}

function monthKey(dateStr) {
  const d = new Date(dateStr);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function monthLabel(key) {
  const [, m] = key.split("-");
  return `${parseInt(m, 10)}월`;
}

/* ---- 필터 UI 구성 ---- */

function setupSportChips() {
  const wrap = document.getElementById("sportChips");
  const all = document.createElement("button");
  all.className = "chip active";
  all.textContent = "전체";
  all.dataset.sport = "all";
  wrap.appendChild(all);

  Object.entries(SPORT_META).forEach(([key, meta]) => {
    const chip = document.createElement("button");
    chip.className = "chip";
    chip.textContent = meta.label;
    chip.dataset.sport = key;
    wrap.appendChild(chip);
  });

  wrap.addEventListener("click", (e) => {
    const btn = e.target.closest(".chip");
    if (!btn) return;
    wrap.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
    btn.classList.add("active");
    state.sport = btn.dataset.sport;
    render();
  });
}

function setupMonthTabs() {
  const wrap = document.getElementById("monthTabs");
  const months = [...new Set(state.events.map(ev => monthKey(ev.date)))].sort();

  const all = document.createElement("button");
  all.className = "chip active";
  all.textContent = "전체 기간";
  all.dataset.month = "all";
  wrap.appendChild(all);

  months.forEach(key => {
    const chip = document.createElement("button");
    chip.className = "chip";
    chip.textContent = monthLabel(key);
    chip.dataset.month = key;
    wrap.appendChild(chip);
  });

  wrap.addEventListener("click", (e) => {
    const btn = e.target.closest(".chip");
    if (!btn) return;
    wrap.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
    btn.classList.add("active");
    state.month = btn.dataset.month;
    render();
  });
}

function setupRegionSelect() {
  const sel = document.getElementById("regionSelect");
  const regions = [...new Set(state.events.map(ev => ev.region || "전국"))].sort();
  const optAll = document.createElement("option");
  optAll.value = "all";
  optAll.textContent = "전체 지역";
  sel.appendChild(optAll);
  regions.forEach(r => {
    const opt = document.createElement("option");
    opt.value = r;
    opt.textContent = r;
    sel.appendChild(opt);
  });
  sel.addEventListener("change", () => {
    state.region = sel.value;
    render();
  });
}

/* ---- 카드 렌더링 ---- */

function renderCard(ev) {
  const meta = SPORT_META[ev.sport] || SPORT_META.marathon;
  const dday = ddayInfo(ev);

  const card = document.createElement("article");
  card.className = "event-card";
  card.setAttribute("data-id", ev.id);
  card.setAttribute("role", "button");
  card.setAttribute("tabindex", "0");
  card.style.setProperty("--sport-tint", meta.tint);
  card.style.setProperty("--sport-color", meta.bg);
  card.style.setProperty("--sport-ink", meta.ink);

  card.innerHTML = `
    <div class="ev-icon"><i class="ti ${meta.icon}" aria-hidden="true"></i></div>
    <div class="event-body">
      <div class="event-top">
        <span class="sport-badge">${meta.label}</span>
        <span class="dday-badge ${dday.urgent ? "dday-urgent" : "dday-normal"}">${dday.label}</span>
      </div>
      <p class="event-name">${ev.name}</p>
      <p class="event-meta">${ev.location} · ${formatDate(ev.date, ev.time)}</p>
      <p class="event-organizer">${ev.organizer ? "주최 " + ev.organizer : "주최 정보 미확인"}</p>
    </div>
  `;
  return card;
}

function render() {
  const grid = document.getElementById("eventGrid");
  const countEl = document.getElementById("resultCount");
  grid.innerHTML = "";

  const filtered = state.events
    .filter(ev => state.sport === "all" || ev.sport === state.sport)
    .filter(ev => state.month === "all" || monthKey(ev.date) === state.month)
    .filter(ev => state.region === "all" || (ev.region || "전국") === state.region)
    .sort((a, b) => new Date(a.date) - new Date(b.date));

  countEl.textContent = `${filtered.length}개 대회`;

  if (filtered.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "조건에 맞는 대회가 없습니다.";
    grid.appendChild(empty);
    return;
  }

  filtered.forEach(ev => grid.appendChild(renderCard(ev)));

  grid.querySelectorAll(".event-card").forEach(card => {
    const open = () => openDetail(card.getAttribute("data-id"));
    card.addEventListener("click", open);
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); }
    });
  });
}

/* ---- 상세 모달 ---- */

function buildIcs(ev) {
  const dt = ev.date.replace(/-/g, "");
  const uid = `${ev.id}@calrank.vercel.app`;
  return [
    "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//calrank//KO",
    "BEGIN:VEVENT",
    `UID:${uid}`,
    `DTSTART;VALUE=DATE:${dt}`,
    `SUMMARY:${ev.name}`,
    `LOCATION:${ev.location}`,
    `DESCRIPTION:calrank에서 자동 생성됨. 신청 페이지: ${ev.applyUrl || ev.sourceUrl || ""}`,
    "END:VEVENT", "END:VCALENDAR",
  ].join("\r\n");
}

function downloadIcs(ev) {
  const blob = new Blob([buildIcs(ev)], { type: "text/calendar;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${ev.name}.ics`;
  a.click();
  URL.revokeObjectURL(url);
}

function openDetail(id) {
  const ev = state.events.find(e => e.id === id);
  if (!ev) return;
  const meta = SPORT_META[ev.sport] || SPORT_META.marathon;
  const dday = ddayInfo(ev);

  const body = document.getElementById("modalBody");
  body.innerHTML = `
    <div class="modal-icon-row">
      <div class="ev-icon" style="--sport-color:${meta.bg};--sport-ink:${meta.ink};">
        <i class="ti ${meta.icon}" aria-hidden="true"></i>
      </div>
      <div>
        <p class="modal-sport" style="color:${meta.ink}">${meta.label}</p>
        <p class="modal-title">${ev.name}</p>
      </div>
    </div>
    <dl class="modal-fields">
      <dt>일시</dt><dd>${formatDate(ev.date, ev.time)}</dd>
      <dt>장소</dt><dd>${ev.location}</dd>
      <dt>종목/거리</dt><dd>${ev.distances.join(" / ")}</dd>
      <dt>주최</dt><dd>${ev.organizer || "미확인"}${ev.organizerPhone ? " · ☎" + ev.organizerPhone : ""}</dd>
      <dt>접수</dt><dd>${dday.label}</dd>
    </dl>
    <button class="modal-apply-btn" id="applyBtn">신청 페이지 바로가기<i class="ti ti-external-link" aria-hidden="true"></i></button>
    <button class="modal-cal-btn" id="calBtn"><i class="ti ti-calendar-plus" aria-hidden="true"></i>내 캘린더에 추가</button>
    <p class="modal-disclaimer">calrank는 대회 주최측이 공개한 일정 정보를 정리해 제공합니다. 접수 조건 등 정확한 내용은 신청 페이지에서 다시 확인해 주세요.</p>
  `;

  document.getElementById("applyBtn").addEventListener("click", () => {
    window.open(ev.applyUrl || ev.sourceUrl || "#", "_blank", "noopener");
  });
  document.getElementById("calBtn").addEventListener("click", () => downloadIcs(ev));

  document.getElementById("modalOverlay").classList.add("open");
  document.body.style.overflow = "hidden";
}

function closeDetail() {
  document.getElementById("modalOverlay").classList.remove("open");
  document.body.style.overflow = "";
}

function setupModal() {
  const overlay = document.getElementById("modalOverlay");
  overlay.addEventListener("click", (e) => { if (e.target === overlay) closeDetail(); });
  document.getElementById("modalClose").addEventListener("click", closeDetail);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDetail(); });
}

async function init() {
  setupModal();
  try {
    const res = await fetch("events.json");
    state.events = await res.json();
  } catch (err) {
    document.getElementById("resultCount").textContent =
      "대회 데이터를 불러오지 못했습니다. 로컬 서버로 실행 중인지 확인해 주세요.";
    console.error(err);
    return;
  }
  setupSportChips();
  setupMonthTabs();
  setupRegionSelect();
  render();
}

init();
