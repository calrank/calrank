const SPORT_META = {
  marathon: { label: "마라톤", tag: "MAR", color: "var(--marathon)" },
  cycling: { label: "자전거", tag: "BIK", color: "var(--cycling)" },
  trail: { label: "트레일", tag: "TRL", color: "var(--trail)" },
  hyrox: { label: "하이록스", tag: "HYX", color: "var(--hyrox)" },
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
  return `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일(${days[d.getDay()]})${timePart}`;
}

function ddayInfo(ev) {
  if (!ev.regDeadline) return { label: "접수기간 미확인", urgent: false };
  const n = daysUntil(ev.regDeadline);
  return { label: n < 0 ? "접수 마감" : `D-${n}`, urgent: n >= 0 && n <= 7 };
}

function getParam(name) {
  return new URLSearchParams(location.search).get(name);
}

function renderNotFound() {
  document.getElementById("eventContent").innerHTML = `
    <section class="hero">
      <h1>대회 정보를 찾을 수 없습니다</h1>
      <p class="hero-sub">삭제되었거나 잘못된 주소일 수 있습니다.</p>
    </section>
  `;
}

async function init() {
  const id = getParam("id");
  if (!id) { renderNotFound(); return; }

  let allEvents;
  try {
    const res = await fetch("events.json");
    allEvents = await res.json();
  } catch (err) {
    renderNotFound();
    return;
  }

  const ev = allEvents.find(e => e.id === id);
  if (!ev) { renderNotFound(); return; }

  const meta = SPORT_META[ev.sport] || SPORT_META.marathon;
  const dday = ddayInfo(ev);
  const pageTitle = `${ev.name} — calrank`;
  const pageDesc = `${ev.name} | ${formatDate(ev.date, ev.time)} | ${ev.location} | ${ev.distances.join(", ")} | calrank에서 대회 일정과 접수 정보를 확인하세요.`;
  const pageUrl = `https://calrank.vercel.app/event.html?id=${encodeURIComponent(ev.id)}`;

  document.title = pageTitle;
  document.getElementById("pageTitleTag").textContent = pageTitle;
  document.getElementById("metaDesc").setAttribute("content", pageDesc);
  document.getElementById("ogTitle").setAttribute("content", pageTitle);
  document.getElementById("ogDesc").setAttribute("content", pageDesc);
  document.getElementById("ogUrl").setAttribute("content", pageUrl);
  document.getElementById("twTitle").setAttribute("content", pageTitle);
  document.getElementById("twDesc").setAttribute("content", pageDesc);

  const canonical = document.createElement("link");
  canonical.rel = "canonical";
  canonical.href = pageUrl;
  document.head.appendChild(canonical);

  document.getElementById("eventContent").innerHTML = `
    <section class="hero">
      <p class="hero-sub">${meta.label} · <span class="dday-badge ${dday.urgent ? "dday-urgent" : ""}">${dday.label}</span></p>
      <h1>${ev.name}</h1>
    </section>
    <div class="modal-fields" style="margin-top:24px;">
      <div class="modal-field-row"><span class="k">일시</span><span class="v">${formatDate(ev.date, ev.time)}</span></div>
      <div class="modal-field-row"><span class="k">장소</span><span class="v">${ev.location}</span></div>
      <div class="modal-field-row"><span class="k">종목/거리</span><span class="v">${ev.distances.join(" / ")}</span></div>
      <div class="modal-field-row"><span class="k">주최</span><span class="v">${ev.organizer || "미확인"}${ev.organizerPhone ? " · " + ev.organizerPhone : ""}</span></div>
    </div>
    <a class="modal-apply-btn" style="display:inline-block;text-decoration:none;margin-top:24px;" href="${ev.applyUrl || ev.sourceUrl || "#"}" target="_blank" rel="noopener">신청하기 ↗</a>
  `;

  const schema = {
    "@context": "https://schema.org",
    "@type": "SportsEvent",
    "name": ev.name,
    "startDate": ev.date,
    "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
    "eventStatus": "https://schema.org/EventScheduled",
    "location": { "@type": "Place", "name": ev.location, "address": ev.location },
    "organizer": ev.organizer ? { "@type": "Organization", "name": ev.organizer } : undefined,
    "url": pageUrl,
  };
  const script = document.createElement("script");
  script.type = "application/ld+json";
  script.textContent = JSON.stringify(schema);
  document.head.appendChild(script);
}

init();
