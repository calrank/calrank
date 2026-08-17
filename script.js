const SPORT_COLORS = {
  marathon:   { color: "var(--marathon)",   bg: "var(--marathon-bg)" },
  cycling:    { color: "var(--cycling)",    bg: "var(--cycling-bg)" },
  trail:      { color: "var(--trail)",      bg: "var(--trail-bg)" },
  hyrox:      { color: "var(--hyrox)",      bg: "var(--hyrox-bg)" },
  triathlon:  { color: "var(--triathlon)",  bg: "var(--triathlon-bg)" },
};

const state = {
  events: [],
  filter: "all",
  saved: new Set(),
};

function daysUntil(dateStr) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(dateStr);
  const diffMs = target - today;
  return Math.round(diffMs / (1000 * 60 * 60 * 24));
}

function formatDate(dateStr, timeStr) {
  const d = new Date(dateStr);
  const days = ["일", "월", "화", "수", "목", "금", "토"];
  const timePart = timeStr && timeStr !== "미확인" ? ` ${timeStr}` : "";
  return `${d.getMonth() + 1}.${d.getDate()}(${days[d.getDay()]})${timePart}`;
}

function ddayInfo(ev) {
  if (!ev.regDeadline) {
    return { label: "접수기간 미확인", urgent: false };
  }
  const regDday = daysUntil(ev.regDeadline);
  const urgent = regDday >= 0 && regDday <= 7;
  const label = regDday < 0 ? "접수 마감" : `접수 D-${regDday}`;
  return { label, urgent };
}

function renderCard(ev) {
  const sc = SPORT_COLORS[ev.sport] || { color: "#333", bg: "#eee" };
  const isSaved = state.saved.has(ev.id);
  const dday = ddayInfo(ev);

  const card = document.createElement("article");
  card.className = "event-card";
  card.setAttribute("data-id", ev.id);
  card.setAttribute("role", "button");
  card.setAttribute("tabindex", "0");
  card.style.setProperty("--sport-color", sc.color);
  card.style.setProperty("--sport-bg", sc.bg);

  card.innerHTML = `
    <div class="event-card-top">
      <span class="sport-badge">${ev.sportLabel}</span>
      <span class="dday-badge ${dday.urgent ? "dday-urgent" : "dday-normal"}">${dday.label}</span>
    </div>
    <p class="event-name">${ev.name}</p>
    <p class="event-meta">${ev.location} · ${formatDate(ev.date, ev.time)}</p>
    <p class="event-distances">${ev.distances.join(" / ")}</p>
    <div class="event-foot">
      <span class="saves">찜 ${ev.saves + (isSaved ? 1 : 0)}</span>
      <button class="save-btn" data-id="${ev.id}" aria-label="찜하기" aria-pressed="${isSaved}">${isSaved ? "♥" : "♡"}</button>
    </div>
  `;
  return card;
}

function render() {
  const grid = document.getElementById("eventGrid");
  const countEl = document.getElementById("resultCount");
  grid.innerHTML = "";

  const filtered = state.events
    .filter(ev => state.filter === "all" || ev.sport === state.filter)
    .sort((a, b) => new Date(a.date) - new Date(b.date));

  countEl.textContent = `${filtered.length}개 대회`;

  if (filtered.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "해당 종목의 예정된 대회가 없습니다.";
    grid.appendChild(empty);
    return;
  }

  filtered.forEach(ev => grid.appendChild(renderCard(ev)));

  grid.querySelectorAll(".save-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = btn.getAttribute("data-id");
      if (state.saved.has(id)) {
        state.saved.delete(id);
      } else {
        state.saved.add(id);
      }
      render();
    });
  });

  grid.querySelectorAll(".event-card").forEach(card => {
    const open = () => openDetail(card.getAttribute("data-id"));
    card.addEventListener("click", open);
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        open();
      }
    });
  });
}

function setupFilters() {
  document.querySelectorAll(".chip").forEach(chip => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      state.filter = chip.getAttribute("data-sport");
      render();
    });
  });
}

/* ---- 상세보기 모달 ---- */

function buildModal() {
  const overlay = document.createElement("div");
  overlay.id = "detailOverlay";
  overlay.className = "modal-overlay";
  overlay.innerHTML = `
    <div class="modal-card" role="dialog" aria-modal="true">
      <button class="modal-close" id="modalClose" aria-label="닫기">✕</button>
      <div id="modalBody"></div>
    </div>
  `;
  document.body.appendChild(overlay);

  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) closeDetail();
  });
  document.getElementById("modalClose").addEventListener("click", closeDetail);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeDetail();
  });
}

function openDetail(id) {
  const ev = state.events.find(e => e.id === id);
  if (!ev) return;

  const sc = SPORT_COLORS[ev.sport] || { color: "#333", bg: "#eee" };
  const dday = ddayInfo(ev);
  const isSaved = state.saved.has(ev.id);

  const body = document.getElementById("modalBody");
  body.innerHTML = `
    <div class="modal-top">
      <span class="sport-badge" style="background:${sc.bg};color:${sc.color};">${ev.sportLabel}</span>
      <span class="dday-badge ${dday.urgent ? "dday-urgent" : "dday-normal"}">${dday.label}</span>
    </div>
    <h2 class="modal-title">${ev.name}</h2>
    <dl class="modal-fields">
      <dt>일시</dt><dd>${formatDate(ev.date, ev.time)}</dd>
      <dt>장소</dt><dd>${ev.location}</dd>
      <dt>종목/거리</dt><dd>${ev.distances.join(" / ")}</dd>
      <dt>접수</dt><dd>${dday.label}</dd>
      <dt>찜</dt><dd>${ev.saves + (isSaved ? 1 : 0)}명</dd>
    </dl>
    <div class="modal-actions">
      <button class="modal-save-btn" id="modalSaveBtn">${isSaved ? "♥ 찜 취소" : "♡ 찜하기"}</button>
      ${ev.sourceUrl ? `<a class="modal-source-link" href="${ev.sourceUrl}" target="_blank" rel="noopener">원본 출처 보기 ↗</a>` : ""}
    </div>
    <p class="modal-disclaimer">calrank는 대회 주최측이 공개한 일정 정보를 정리해 제공합니다. 접수 조건 등 정확한 내용은 원본 출처에서 다시 확인해 주세요.</p>
  `;

  document.getElementById("modalSaveBtn").addEventListener("click", () => {
    if (state.saved.has(ev.id)) {
      state.saved.delete(ev.id);
    } else {
      state.saved.add(ev.id);
    }
    render();
    openDetail(ev.id);
  });

  document.getElementById("detailOverlay").classList.add("open");
  document.body.style.overflow = "hidden";
}

function closeDetail() {
  const overlay = document.getElementById("detailOverlay");
  overlay.classList.remove("open");
  document.body.style.overflow = "";
}

async function init() {
  setupFilters();
  buildModal();
  try {
    const res = await fetch("events.json");
    state.events = await res.json();
  } catch (err) {
    document.getElementById("resultCount").textContent =
      "대회 데이터를 불러오지 못했습니다. 로컬 서버로 실행 중인지 확인해 주세요.";
    console.error(err);
    return;
  }
  render();
}

init();
