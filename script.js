const SUPABASE_URL = "https://mlbzsqeoqlyvnyzeegeu.supabase.co";
const SUPABASE_KEY = "sb_publishable_byKae86vGA0M5NjoZC0ELw_NMkm8ObR";
const sb = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

const SPORT_META = {
  marathon:   { label: "마라톤",  tag: "MAR", color: "var(--marathon)" },
  cycling:    { label: "자전거",  tag: "BIK", color: "var(--cycling)" },
  trail:      { label: "트레일",  tag: "TRL", color: "var(--trail)" },
  triathlon:  { label: "철인3종", tag: "TRI", color: "var(--triathlon)" },
  inline:     { label: "인라인", tag: "INL", color: "var(--inline)" },
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
  sel.value = state.region;
  sel.addEventListener("change", () => {
    state.region = sel.value;
    render();
  });
}

// 대회 카드에 후기 평점을 노출한다. 800개 카드마다 개별 조회하면 느리므로,
// event_reviews 테이블 전체를 한 번만 가져와 event_id별로 집계해 캐싱한다.
let reviewSummaryCache = null;
async function loadReviewSummaries() {
  try {
    const { data } = await sb.from("event_reviews").select("event_id, rating");
    const grouped = {};
    (data || []).forEach(r => {
      if (!grouped[r.event_id]) grouped[r.event_id] = { sum: 0, count: 0 };
      grouped[r.event_id].sum += r.rating;
      grouped[r.event_id].count += 1;
    });
    reviewSummaryCache = {};
    Object.keys(grouped).forEach(id => {
      reviewSummaryCache[id] = {
        avg: grouped[id].sum / grouped[id].count,
        count: grouped[id].count,
      };
    });
  } catch (e) {
    reviewSummaryCache = {};
  }
}

const TIER_ICON = { "플래티넘": "💠", "골드": "🏅", "실버": "🥈", "브론즈": "🥉", "일반": "" };

// calrank 자체 "규모·인지도 지수"를 간단한 표로 보여준다. 참가자 후기 평점과는
// 완전히 다른 지표임을 항상 명시하고, 근거(19개 항목)를 투명하게 공개한다.
function buildScaleIndexTable(eventId) {
  const rating = eventRatingsCache && eventRatingsCache[eventId];
  if (!rating) return "";
  const rows = rating.criteria.map(c => `
    <tr>
      <td class="scale-idx-label">${c.label}</td>
      <td class="scale-idx-check">${c.achieved ? "✓" : "–"}</td>
    </tr>
  `).join("");

  return `
    <div class="scale-index-box">
      <p class="scale-index-title">${TIER_ICON[rating.tier] || ""} calrank 규모·인지도 지수 — ${rating.tier} (${rating.indexScore}/100)</p>
      <table class="scale-index-table">
        <tbody>${rows}</tbody>
      </table>
      <p class="scale-index-disclaimer">${rating.disclaimer}</p>
    </div>
  `;
}

// "찜하기" — localStorage 기반 개인화 저장 목록. 서버 계정 없이도 관심 대회를
// 모아볼 수 있게 하고, saved-events.html에서 접수마감 임박순으로 재방문을 유도한다.
const SAVED_EVENTS_KEY = "calrank-saved-events";

function getSavedEventIds() {
  try {
    return JSON.parse(localStorage.getItem(SAVED_EVENTS_KEY) || "[]");
  } catch (e) {
    return [];
  }
}

function isEventSaved(id) {
  return getSavedEventIds().includes(id);
}

function toggleSavedEvent(id) {
  const saved = getSavedEventIds();
  const idx = saved.indexOf(id);
  if (idx >= 0) {
    saved.splice(idx, 1);
  } else {
    saved.push(id);
  }
  try {
    localStorage.setItem(SAVED_EVENTS_KEY, JSON.stringify(saved));
  } catch (e) {}
  return idx < 0;
}

function renderCard(ev) {
  const meta = SPORT_META[ev.sport] || SPORT_META.marathon;
  const dday = ddayInfo(ev);
  const review = reviewSummaryCache && reviewSummaryCache[ev.id];
  const reviewBadgeHtml = review
    ? `<span class="ev-review-badge">⭐ ${review.avg.toFixed(1)} (${review.count})</span>`
    : "";
  const rating = eventRatingsCache && eventRatingsCache[ev.id];
  // 유저 후기(⭐)와 헷갈리지 않도록, calrank 자체 규모·인지도 지수는
  // 별 모양이 아닌 티어 아이콘 + 숫자로만 표시한다.
  const scaleBadgeHtml = rating && rating.tier !== "일반"
    ? `<span class="ev-scale-badge" title="calrank 규모·인지도 지수(참고용)">${TIER_ICON[rating.tier] || ""} ${rating.tier} ${rating.indexScore}</span>`
    : "";

  // 진짜 <a href> 로 만든다. 예전에는 <article role="button"> 에 클릭 이벤트만
  // 달아 두어서, 대회 상세 페이지(e/<id>.html)로 가는 링크가 사이트 어디에도
  // 없었다. 검색엔진은 사이트맵으로 주소를 "발견"만 하고 크롤링하지 않았다
  // (구글 색인 보고서: 발견됨 - 현재 색인이 생성되지 않음 493개).
  // 사람에게도 이득이다 — 가운데 클릭·새 탭으로 열기가 이제 동작한다.
  const card = document.createElement("a");
  card.className = "event-card";
  card.href = "e/" + encodeURIComponent(ev.id) + ".html";
  card.setAttribute("data-id", ev.id);
  card.style.setProperty("--sport-color", meta.color);

  const savedInitial = isEventSaved(ev.id);
  card.innerHTML = `
    <span class="ev-tag">${meta.tag}</span>
    <button class="ev-save-btn ${savedInitial ? "saved" : ""}" data-save-id="${ev.id}" aria-label="찜하기" title="찜하기">${savedInitial ? "❤️" : "🤍"}</button>
    <div class="event-body">
      <div class="event-top">
        <span class="event-name">${ev.name}</span>
        ${scaleBadgeHtml}
        <span class="dday-badge ${dday.urgent ? "dday-urgent" : ""}">${dday.label}</span>
      </div>
      <p class="event-meta">${ev.location} · ${formatDate(ev.date, ev.time)}${ev.organizer ? " · " + ev.organizer : ""}${reviewBadgeHtml}</p>
    </div>
    <span class="event-chevron">›</span>
  `;
  const saveBtn = card.querySelector(".ev-save-btn");
  saveBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    const nowSaved = toggleSavedEvent(ev.id);
    saveBtn.textContent = nowSaved ? "❤️" : "🤍";
    saveBtn.classList.toggle("saved", nowSaved);
  });
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
    card.addEventListener("click", (e) => {
      // 새 탭으로 열려는 조작(ctrl/cmd/shift/가운데 버튼)은 그대로 둔다.
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
      e.preventDefault();
      openDetail(card.getAttribute("data-id"));
    });
  });

  const mapDiv = document.getElementById("mapContainer");
  if (mapDiv && mapDiv.style.display !== "none") renderMap(filtered);
}

let mapInstance = null;
let mapMarkersLayer = null;
let leafletLoadPromise = null;

// Leaflet(지도 라이브러리)은 "지도로 보기" 버튼을 실제로 누르기 전까지는
// 아무도 쓰지 않는데, 예전에는 페이지를 열 때마다 무조건 CSS/JS를 받아왔다.
// 초기 로딩 속도를 확실히 체감되게 줄이기 위해 클릭 시점에만 지연 로드한다.
function loadLeaflet() {
  if (typeof L !== "undefined") return Promise.resolve();
  if (leafletLoadPromise) return leafletLoadPromise;
  leafletLoadPromise = new Promise((resolve, reject) => {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
    document.head.appendChild(link);

    const script = document.createElement("script");
    script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
    script.onload = resolve;
    script.onerror = reject;
    document.body.appendChild(script);
  });
  return leafletLoadPromise;
}

function renderMap(filteredEvents) {
  const mapDiv = document.getElementById("mapContainer");
  if (!mapDiv || typeof L === "undefined") return;

  const withCoords = filteredEvents.filter(ev => ev.lat && ev.lng);

  const legendEl = document.getElementById("mapLegend");
  if (legendEl) {
    const usedSports = [...new Set(withCoords.map(ev => ev.sport))];
    legendEl.style.display = usedSports.length ? "flex" : "none";
    legendEl.innerHTML = usedSports.map(s => {
      const meta = SPORT_META[s] || SPORT_META.marathon;
      return `<span style="display:inline-flex; align-items:center; gap:6px;"><span style="width:10px; height:10px; border-radius:50%; background:${meta.color}; display:inline-block;"></span>${meta.label}</span>`;
    }).join("");
  }

  if (!mapInstance) {
    mapInstance = L.map("mapContainer").setView([36.5, 127.8], 7);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 18,
    }).addTo(mapInstance);
    mapMarkersLayer = L.layerGroup().addTo(mapInstance);
  }

  mapMarkersLayer.clearLayers();
  withCoords.forEach(ev => {
    const meta = SPORT_META[ev.sport] || SPORT_META.marathon;
    const marker = L.circleMarker([ev.lat, ev.lng], {
      radius: 7,
      color: meta.color,
      fillColor: meta.color,
      fillOpacity: 0.85,
      weight: 2,
    });
    marker.bindTooltip(ev.name, { direction: "top" });
    marker.on("click", () => openDetail(ev.id));
    marker.addTo(mapMarkersLayer);
  });

  setTimeout(() => { if (mapInstance) mapInstance.invalidateSize(); }, 100);
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
    ${buildScaleIndexTable(ev.id)}
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

function animateCount(el, target, duration) {
  const start = 0;
  const startTime = performance.now();
  function tick(now) {
    const progress = Math.min((now - startTime) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const value = Math.round(start + (target - start) * eased);
    el.textContent = value.toLocaleString("ko-KR");
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

function renderHeroStats() {
  const wrap = document.getElementById("heroStats");
  if (!wrap) return;
  const totalCount = state.events.length;
  const sportCount = new Set(state.events.map(ev => ev.sport)).size;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const urgentCount = state.events.filter(ev => getRegStatus(ev) === "urgent").length;

  wrap.innerHTML = `
    <span class="hero-stat"><b id="statTotal">0</b>개 대회 진행중</span>
    <span class="hero-stat"><b id="statSport">0</b>개 종목</span>
    <span class="hero-stat"><b id="statUrgent">0</b>개 접수마감임박</span>
  `;
  animateCount(document.getElementById("statTotal"), totalCount, 900);
  animateCount(document.getElementById("statSport"), sportCount, 700);
  animateCount(document.getElementById("statUrgent"), urgentCount, 900);
}

let eventRatingsCache = {};
async function loadEventRatings() {
  try {
    const res = await fetch("event_ratings.json");
    eventRatingsCache = await res.json();
  } catch (e) {
    eventRatingsCache = {};
  }
}

async function init() {
  setupModal();
  try {
    const res = await fetch("events.json");
    state.events = await res.json();
    await loadEventRatings();
    injectEventSchema(state.events);

    const urlParams = new URLSearchParams(location.search);
    const urlSport = urlParams.get("sport");
    if (urlSport && SPORT_META[urlSport]) state.sport = urlSport;
    const urlRegion = urlParams.get("region");
    if (urlRegion) state.region = urlRegion;
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
  renderHeroStats();

  // 리뷰 평점은 초기 렌더링을 지연시키지 않도록 백그라운드로 불러온 뒤
  // 조용히 다시 그려서 배지를 붙인다.
  loadReviewSummaries().then(() => render());

  const mapToggleBtn = document.getElementById("mapToggleBtn");
  if (mapToggleBtn) {
    mapToggleBtn.addEventListener("click", async () => {
      const grid = document.getElementById("eventGrid");
      const mapDiv = document.getElementById("mapContainer");
      const countEl = document.getElementById("resultCount");
      const showingMap = mapDiv.style.display !== "none";
      if (showingMap) {
        mapDiv.style.display = "none";
        grid.style.display = "";
        countEl.style.display = "";
        mapToggleBtn.textContent = "🗺️ 지도로 보기";
      } else {
        mapToggleBtn.textContent = "지도 불러오는 중...";
        try {
          await loadLeaflet();
        } catch (e) {
          mapToggleBtn.textContent = "🗺️ 지도로 보기";
          return;
        }
        mapDiv.style.display = "block";
        grid.style.display = "none";
        countEl.style.display = "none";
        mapToggleBtn.textContent = "📋 목록으로 보기";
        render();
      }
    });
  }

  setupCalendarSubscribe();
}

// ── 캘린더 구독 ──────────────────────────────────────────────────────────
// 전체 1,000여 개를 한 덩어리로 주면 아무도 구독하지 않으므로 종목별 피드를 고르게 한다.
// 알림은 서버가 아니라 구독자의 캘린더 앱이 ICS 안의 VALARM 을 보고 직접 보낸다.
const SUB_FEEDS = [
  ["", "전체"],
  ["-marathon", "마라톤"],
  ["-trail", "트레일"],
  ["-cycling", "자전거"],
  ["-triathlon", "철인3종"],
  ["-inline", "인라인"],
];

function setupCalendarSubscribe() {
  const btn = document.getElementById("subscribeBtn");
  const panel = document.getElementById("subscribeInfo");
  const wrap = document.getElementById("subSports");
  const go = document.getElementById("subGo");
  const urlEl = document.getElementById("subscribeUrl");
  const copyBtn = document.getElementById("subCopy");
  if (!btn || !panel || !wrap || !go || !urlEl) return;

  const origin = "calrank.vercel.app";
  let picked = "";

  let apply = function () {
    const path = "/feed" + picked + ".ics";
    go.href = "webcal://" + origin + path;
    urlEl.textContent = "https://" + origin + path;
    wrap.querySelectorAll(".sub-sport").forEach((b) => {
      b.classList.toggle("on", b.dataset.suffix === picked);
    });
  };

  SUB_FEEDS.forEach(([suffix, label]) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "sub-sport";
    b.dataset.suffix = suffix;
    b.textContent = label;
    b.addEventListener("click", () => { picked = suffix; apply(); });
    wrap.appendChild(b);
  });
  apply();

  btn.addEventListener("click", () => {
    panel.style.display = panel.style.display === "none" ? "block" : "none";
  });

  // 플랫폼마다 되는 길이 다르다. 안 되는 방법을 1순위로 보여 주면 거기서 끝난다.
  //  · iOS/macOS : webcal:// 를 누르면 캘린더 앱이 바로 받는다.
  //  · 안드로이드: 폰에서는 구독 자체가 불가능하다. 구글 캘린더 고객센터가
  //    "To subscribe to a new calendar, you must use a computer web browser"
  //    라고 못박고 있다. PC 에서 한 번 등록하면 폰으로 동기화된다.
  //  · PC        : 구글 캘린더의 'URL로 추가' 화면을 바로 열어 준다.
  var ua = navigator.userAgent || "";
  var isApple = /iPhone|iPad|iPod|Macintosh/.test(ua);
  var isAndroid = /Android/.test(ua);
  var guide = document.getElementById("subGuide");

  function applyPlatform() {
    var https = urlEl.textContent;
    if (isAndroid) {
      go.textContent = "📋 주소 복사 (PC에서 등록)";
      go.href = "#";
      go.onclick = function (e) { e.preventDefault(); copyBtn.click(); };
      if (guide) {
        guide.innerHTML = "안드로이드는 <b>폰에서 캘린더 구독을 추가할 수 없습니다</b> — " +
          "구글 캘린더가 \u201C새 캘린더를 구독하려면 PC 웹 브라우저를 사용해야 한다\u201D고 " +
          "안내하고 있습니다. PC에서 한 번만 등록하면 폰으로 자동 동기화됩니다.<br>" +
          "<b>폰에서 지금 바로 하시려면</b>, 대회 상세 페이지의 " +
          "\u2018📅 내 캘린더에 추가\u2019 를 쓰시면 됩니다. 대회 한 건씩 바로 들어갑니다.";
      }
    } else if (isApple) {
      go.textContent = "📅 내 캘린더에 추가";
      go.onclick = null;
      if (guide) guide.textContent = "누르면 캘린더 앱이 열립니다. 구독을 눌러 주세요.";
    } else {
      go.textContent = "📅 구글 캘린더에 추가";
      go.href = "https://calendar.google.com/calendar/u/0/r?cid=" + encodeURIComponent(https);
      go.target = "_blank";
      go.rel = "noopener";
      go.onclick = null;
      if (guide) {
        guide.textContent = "구글 캘린더가 열리면 \u2018추가\u2019 를 눌러 주세요. " +
          "애플 캘린더를 쓰신다면 아래 주소를 복사해 \u2018구독 캘린더 추가\u2019 에 넣으시면 됩니다.";
      }
    }
  }

  var baseApply = apply;
  apply = function () { baseApply(); applyPlatform(); };
  apply();

  if (copyBtn) {
    copyBtn.addEventListener("click", async () => {
      const text = urlEl.textContent;
      try {
        await navigator.clipboard.writeText(text);
      } catch (_) {
        // clipboard API 가 막힌 환경(비 HTTPS, 구형 브라우저)에서는 선택만 해 준다
        const r = document.createRange();
        r.selectNodeContents(urlEl);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(r);
      }
      const old = copyBtn.textContent;
      copyBtn.textContent = "복사됨";
      setTimeout(() => { copyBtn.textContent = old; }, 1500);
    });
  }
}

init();
