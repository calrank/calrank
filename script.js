const SUPABASE_URL = "https://mlbzsqeoqlyvnyzeegeu.supabase.co";
const SUPABASE_KEY = "sb_publishable_byKae86vGA0M5NjoZC0ELw_NMkm8ObR";
const sb = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

const SPORT_META = {
  marathon:   { label: "마라톤",  tag: "MAR", color: "var(--marathon)" },
  cycling:    { label: "자전거",  tag: "BIK", color: "var(--cycling)" },
  trail:      { label: "트레일",  tag: "TRL", color: "var(--trail)" },
  triathlon:  { label: "철인3종", tag: "TRI", color: "var(--triathlon)" },
};

const state = {
  events: [],
  sport: "all",
  month: "all",
  region: "all",
  status: "all",
  distBucket: "all",
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
  if (!ev.regDeadline) {
    if (ev.regClosed === true) return { label: "접수 마감", urgent: false };
    if (ev.regClosed === false) return { label: "접수중 (마감일 미확인)", urgent: false };
    return { label: "접수기간 미확인", urgent: false };
  }
  const n = daysUntil(ev.regDeadline);
  return { label: n < 0 ? "접수 마감" : `접수 D-${n}`, urgent: n >= 0 && n <= 7 };
}

function getRegStatus(ev) {
  if (!ev.regDeadline) {
    if (ev.regClosed === true) return "closed";
    if (ev.regClosed === false) return "open";
    return "unknown";
  }
  const n = daysUntil(ev.regDeadline);
  if (n < 0) return "closed";
  if (n <= 7) return "urgent";
  return "open";
}

function parseDistanceKm(text) {
  if (!text) return null;
  if (/하프/.test(text)) return 21.1;
  if (/풀코스|풀(?!.*코스)/.test(text) && !/미확인/.test(text)) return 42.2;
  const m1 = text.match(/(\d+(?:\.\d+)?)\s*km/i);
  if (m1) return parseFloat(m1[1]);
  const m2 = text.match(/(\d+(?:\.\d+)?)\s*K\b/i);
  if (m2) return parseFloat(m2[1]);
  return null;
}

function getDistanceBucket(ev) {
  const text = (ev.distances || []).join(" ");
  const kms = text.split(/[\s\/,]+/).map(part => parseDistanceKm(part)).filter(v => v != null);
  const fullText = parseDistanceKm(text);
  const km = kms.length ? Math.max(...kms) : fullText;
  if (km == null) return null;
  if (km <= 10) return "short";
  if (km <= 25) return "mid";
  if (km <= 50) return "long";
  return "ultra";
}

function monthKey(dateStr) {
  const d = new Date(dateStr);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function monthLabel(key) {
  const [, m] = key.split("-");
  return `${parseInt(m, 10)}월`;
}

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

function setupStatusChips() {
  const wrap = document.getElementById("statusChips");
  if (!wrap) return;
  const options = [
    ["all", "전체"],
    ["open", "접수중"],
    ["urgent", "마감임박"],
    ["closed", "마감"],
  ];
  options.forEach(([value, label]) => {
    const chip = document.createElement("button");
    chip.className = value === "all" ? "chip active" : "chip";
    chip.textContent = label;
    chip.dataset.status = value;
    wrap.appendChild(chip);
  });

  wrap.addEventListener("click", (e) => {
    const btn = e.target.closest(".chip");
    if (!btn) return;
    wrap.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
    btn.classList.add("active");
    state.status = btn.dataset.status;
    render();
  });
}

function setupDistBucketChips() {
  const wrap = document.getElementById("distBucketChips");
  if (!wrap) return;
  const options = [
    ["all", "전체 거리"],
    ["short", "~10km"],
    ["mid", "10~25km"],
    ["long", "25~50km"],
    ["ultra", "50km~"],
  ];
  options.forEach(([value, label]) => {
    const chip = document.createElement("button");
    chip.className = value === "all" ? "chip active" : "chip";
    chip.textContent = label;
    chip.dataset.dist = value;
    wrap.appendChild(chip);
  });

  wrap.addEventListener("click", (e) => {
    const btn = e.target.closest(".chip");
    if (!btn) return;
    wrap.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
    btn.classList.add("active");
    state.distBucket = btn.dataset.dist;
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

function render() {
  const grid = document.getElementById("eventGrid");
  const countEl = document.getElementById("resultCount");
  grid.innerHTML = "";

  const filtered = state.events
    .filter(ev => state.sport === "all" || ev.sport === state.sport)
    .filter(ev => state.month === "all" || monthKey(ev.date) === state.month)
    .filter(ev => state.region === "all" || (ev.region || "전국") === state.region)
    .filter(ev => state.status === "all" || getRegStatus(ev) === state.status)
    .filter(ev => state.distBucket === "all" || getDistanceBucket(ev) === state.distBucket)
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

async function renderSaveWidget(eventId) {
  const el = document.getElementById("saveWidgetModal");
  if (!el) return;
  const { data: { session } } = await sb.auth.getSession();
  const { data: countData } = await sb.rpc("get_save_count", { p_event_id: eventId });
  const count = countData || 0;
  let isSaved = false;
  if (session?.user) {
    const { data } = await sb.from("event_saves").select("id").eq("event_id", eventId).eq("user_id", session.user.id).maybeSingle();
    isSaved = !!data;
  }
  el.innerHTML = `<button id="saveToggleBtnModal" class="modal-cal-btn" style="width:100%;">${isSaved ? "★ 찜 완료" : "☆ 찜하기"} ${count > 0 ? `(${count}명이 찜함)` : ""}</button>`;
  document.getElementById("saveToggleBtnModal").addEventListener("click", async () => {
    const { data: { session: s } } = await sb.auth.getSession();
    if (!s?.user) {
      alert("로그인이 필요한 기능입니다. 내 랭크 페이지에서 로그인해주세요.");
      location.href = "myrank.html";
      return;
    }
    if (isSaved) {
      await sb.from("event_saves").delete().eq("event_id", eventId).eq("user_id", s.user.id);
    } else {
      await sb.from("event_saves").insert({ event_id: eventId, user_id: s.user.id });
    }
    renderSaveWidget(eventId);
  });
}

function openDetail(id) {
  const ev = state.events.find(e => e.id === id);
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
    <div id="saveWidgetModal" style="margin-top:8px;"></div>
    <a class="modal-cal-btn" style="display:block;text-align:center;text-decoration:none;box-sizing:border-box;" href="event.html?id=${encodeURIComponent(ev.id)}">상세 페이지 보기</a>
    <p class="modal-disclaimer">calrank는 대회 주최측이 공개한 일정 정보를 정리해 제공합니다. 접수 조건 등 정확한 내용은 신청 페이지에서 다시 확인해 주세요.</p>
  `;

  document.getElementById("applyBtn").addEventListener("click", () => {
    window.open(ev.applyUrl || ev.sourceUrl || "#", "_blank", "noopener");
  });
  document.getElementById("calBtn").addEventListener("click", () => downloadIcs(ev));

  document.getElementById("modalOverlay").classList.add("open");
  document.body.style.overflow = "hidden";
  renderSaveWidget(id);
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

function injectEventSchema(events) {
  const upcoming = events
    .filter(ev => ev.date && new Date(ev.date) >= new Date(new Date().toDateString()))
    .sort((a, b) => new Date(a.date) - new Date(b.date))
    .slice(0, 30);

  const itemListElement = upcoming.map((ev, i) => ({
    "@type": "ListItem",
    "position": i + 1,
    "item": {
      "@type": "SportsEvent",
      "name": ev.name,
      "startDate": ev.date,
      "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
      "eventStatus": "https://schema.org/EventScheduled",
      "location": {
        "@type": "Place",
        "name": ev.location || "전국",
        "address": ev.location || "전국",
      },
      "organizer": ev.organizer ? { "@type": "Organization", "name": ev.organizer } : undefined,
      "url": `https://calrank.vercel.app/event.html?id=${encodeURIComponent(ev.id)}`,
    },
  }));

  const schema = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    "name": "calrank 대회 캘린더",
    "itemListElement": itemListElement,
  };

  const script = document.createElement("script");
  script.type = "application/ld+json";
  script.textContent = JSON.stringify(schema);
  document.head.appendChild(script);
}

async function init() {
  setupModal();
  try {
    const res = await fetch("events.json");
    state.events = await res.json();
    injectEventSchema(state.events);
  } catch (err) {
    document.getElementById("resultCount").textContent =
      "대회 데이터를 불러오지 못했습니다. 로컬 서버로 실행 중인지 확인해 주세요.";
    console.error(err);
    return;
  }
  setupSportChips();
  setupStatusChips();
  setupDistBucketChips();
  setupMonthTabs();
  setupRegionSelect();
  render();
}

init();
