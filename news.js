// calrank 종목뉴스 — 매일 자동 수집된 news.json을 필터링해서 보여줍니다.

const SPORT_LABEL = {
  marathon: "마라톤", cycling: "자전거", triathlon: "철인3종",
};

let allNews = [];
let currentSport = "all";

function timeAgoOrDate(dateStr) {
  const d = new Date(dateStr + "T00:00:00");
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diffDays = Math.round((today - d) / 86400000);
  if (diffDays === 0) return "오늘";
  if (diffDays === 1) return "어제";
  if (diffDays < 7) return `${diffDays}일 전`;
  return dateStr;
}

function setupSportChips() {
  const wrap = document.getElementById("newsSportChips");
  const sports = ["all", ...Object.keys(SPORT_LABEL)];
  wrap.innerHTML = "";
  sports.forEach(sport => {
    const chip = document.createElement("button");
    chip.className = "chip" + (sport === currentSport ? " active" : "");
    chip.textContent = sport === "all" ? "전체" : SPORT_LABEL[sport];
    chip.dataset.sport = sport;
    wrap.appendChild(chip);
  });

  wrap.addEventListener("click", (e) => {
    const btn = e.target.closest(".chip");
    if (!btn) return;
    currentSport = btn.dataset.sport;
    setupSportChips();
    renderList();
  });
}

function renderList() {
  const list = document.getElementById("newsList");
  const countEl = document.getElementById("newsCount");
  list.innerHTML = "";

  const filtered = currentSport === "all"
    ? allNews
    : allNews.filter(n => n.sport === currentSport);

  countEl.textContent = `${filtered.length}개 소식`;

  if (filtered.length === 0) {
    list.innerHTML = `<div class="empty-state">아직 소식이 없습니다.</div>`;
    return;
  }

  filtered.forEach(n => {
    const card = document.createElement("a");
    card.className = "news-card";
    card.href = n.sourceUrl;
    card.target = "_blank";
    card.rel = "noopener noreferrer";
    card.innerHTML = `
      <div class="news-card-top">
        <span class="news-sport-tag">${SPORT_LABEL[n.sport] || n.sport}</span>
        <span class="news-date">${timeAgoOrDate(n.date)}</span>
      </div>
      <p class="news-title">${n.title}</p>
      ${n.excerpt ? `<p class="news-excerpt">${n.excerpt}</p>` : ""}
      <p class="news-source">${n.sourceName} ↗</p>
    `;
    list.appendChild(card);
  });
}

async function init() {
  setupSportChips();
  try {
    const res = await fetch("news.json");
    allNews = await res.json();
  } catch (e) {
    console.error(e);
    allNews = [];
  }
  renderList();
}

init();
