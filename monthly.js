const SPORT_META = {
  marathon: { label: "마라톤", tag: "MAR", color: "var(--marathon)" },
  cycling: { label: "자전거", tag: "BIK", color: "var(--cycling)" },
  trail: { label: "트레일", tag: "TRL", color: "var(--trail)" },
  triathlon: { label: "철인3종", tag: "TRI", color: "var(--triathlon)" },
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
  return { label: n < 0 ? "접수 마감" : `D-${n}`, urgent: n >= 0 && n <= 7 };
}

function isWeekend(dateStr) {
  const d = new Date(dateStr).getDay();
  return d === 0 || d === 6;
}

function renderCard(ev) {
  const meta = SPORT_META[ev.sport] || SPORT_META.marathon;
  const dday = ddayInfo(ev);
  const card = document.createElement("article");
  card.className = "event-card";
  card.setAttribute("data-id", ev.id);
  card.setAttribute("role", "button");
  card.setAttribute("tabindex", "0");
  card.style.setProperty("--sport-color", meta.color);
  card.innerHTML = `
    <span class="ev-tag">${meta.tag}</span>
    <div class="event-body">
      <div class="event-top">
        <span class="event-name">${ev.name}</span>
        <span class="dday-badge ${dday.urgent ? "dday-urgent" : ""}">${dday.label}</span>
      </div>
      <p class="event-meta">${ev.location} · ${formatDate(ev.date, ev.time)}${ev.organizer ? " · " + ev.organizer : ""}</p>
    </div>
    <span class="event-chevron">›</span>
  `;
  return card;
}

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

let allEvents = [];

function openDetail(id) {
  const ev = allEvents.find(e => e.id === id);
  if (!ev) return;
  const meta = SPORT_META[ev.sport] || SPORT_META.marathon;
  const dday = ddayInfo(ev);
  const body = document.getElementById("modalBody");
  body.style.setProperty("--sport-color", meta.color);
  body.innerHTML = `
    <div class="modal-top-row">
      <span class="modal-tag">${meta.tag}</span>
      <span class="dday-badge ${dday.urgent ? "dday-urgent" : ""}">${dday.label}</span>
    </div>
    <p class="modal-title">${ev.name}</p>
    <div class="modal-fields">
      <div class="modal-field-row"><span class="k">일시</span><span class="v">${formatDate(ev.date, ev.time)}</span></div>
      <div class="modal-field-row"><span class="k">장소</span><span class="v">${ev.location}</span></div>
      <div class="modal-field-row"><span class="k">종목/거리</span><span class="v">${ev.distances.join(" / ")}</span></div>
      <div class="modal-field-row"><span class="k">주최</span><span class="v">${ev.organizer || "미확인"}${ev.organizerPhone ? " · " + ev.organizerPhone : ""}</span></div>
    </div>
    <button class="modal-apply-btn" id="applyBtn">신청하기 ↗</button>
    <button class="modal-cal-btn" id="calBtn">캘린더에 저장</button>
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
  const targetSport = window.TARGET_SPORT || "marathon";
  const targetKeyword = window.TARGET_KEYWORD || null;
  const pageLabel = window.PAGE_SPORT_LABEL || (SPORT_META[targetSport] || SPORT_META.marathon).label;
  try {
    const res = await fetch("events.json");
    allEvents = await res.json();
  } catch (err) {
    document.getElementById("resultCount").textContent = "대회 데이터를 불러오지 못했습니다.";
    return;
  }

  const now = new Date();
  const y = now.getFullYear();
  const m = now.getMonth() + 1;

  let filtered;
  if (targetKeyword) {
    document.getElementById("pageTitle").textContent = `${pageLabel} 대회 일정 총정리`;
    document.title = `${pageLabel} 대회 일정 총정리 — calrank`;
    filtered = allEvents
      .filter(ev => (ev.distances || []).some(d => d.includes(targetKeyword)))
      .filter(ev => new Date(ev.date) >= new Date(new Date().toDateString()))
      .sort((a, b) => new Date(a.date) - new Date(b.date));
  } else {
    document.getElementById("pageTitle").textContent = `${y}년 ${m}월 주말 ${pageLabel} 대회 총정리`;
    document.title = `${y}년 ${m}월 주말 ${pageLabel} 대회 총정리 — calrank`;
    filtered = allEvents
      .filter(ev => ev.sport === targetSport)
      .filter(ev => {
        const d = new Date(ev.date);
        return d.getFullYear() === y && d.getMonth() + 1 === m;
      })
      .filter(ev => isWeekend(ev.date))
      .sort((a, b) => new Date(a.date) - new Date(b.date));
  }

  const grid = document.getElementById("eventGrid");
  const countEl = document.getElementById("resultCount");
  countEl.textContent = `${filtered.length}개 대회`;

  if (filtered.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = targetKeyword
      ? `현재 등록된 ${pageLabel} 대회가 없습니다.`
      : `이번 달 주말에는 등록된 ${pageLabel} 대회가 없습니다.`;
    grid.appendChild(empty);
  } else {
    filtered.forEach(ev => grid.appendChild(renderCard(ev)));
    grid.querySelectorAll(".event-card").forEach(card => {
      const open = () => openDetail(card.getAttribute("data-id"));
      card.addEventListener("click", open);
      card.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); }
      });
    });
  }
}

init();
