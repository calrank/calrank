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

function renderCard(ev) {
  const sc = SPORT_COLORS[ev.sport] || { color: "#333", bg: "#eee" };
  const isSaved = state.saved.has(ev.id);

  let ddayBadgeHtml = "";
  if (ev.regDeadline) {
    const regDday = daysUntil(ev.regDeadline);
    const isUrgent = regDday >= 0 && regDday <= 7;
    const ddayLabel = regDday < 0 ? "접수 마감" : `접수 D-${regDday}`;
    ddayBadgeHtml = `<span class="dday-badge ${isUrgent ? "dday-urgent" : "dday-normal"}">${ddayLabel}</span>`;
  } else {
    ddayBadgeHtml = `<span class="dday-badge dday-normal">접수기간 미확인</span>`;
  }

  const card = document.createElement("article");
  card.className = "event-card";
  card.style.setProperty("--sport-color", sc.color);
  card.style.setProperty("--sport-bg", sc.bg);

  card.innerHTML = `
    <div class="event-card-top">
      <span class="sport-badge">${ev.sportLabel}</span>
      ${ddayBadgeHtml}
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
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-id");
      if (state.saved.has(id)) {
        state.saved.delete(id);
      } else {
        state.saved.add(id);
      }
      render();
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

async function init() {
  setupFilters();
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
