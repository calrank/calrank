const SUPABASE_URL = "https://mlbzsqeoqlyvnyzeegeu.supabase.co";
const SUPABASE_KEY = "sb_publishable_byKae86vGA0M5NjoZC0ELw_NMkm8ObR";
const sb = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

const SPORT_META = {
  marathon: { label: "마라톤", tag: "MAR", color: "var(--marathon)" },
  cycling: { label: "자전거", tag: "BIK", color: "var(--cycling)" },
  trail: { label: "트레일", tag: "TRL", color: "var(--trail)" },
  triathlon: { label: "철인3종", tag: "TRI", color: "var(--triathlon)" },
  inline: { label: "인라인", tag: "INL", color: "var(--inline)" },
};

function getSeason(dateStr) {
  const m = new Date(dateStr).getMonth() + 1;
  if (m >= 3 && m <= 5) return "봄";
  if (m >= 6 && m <= 8) return "여름";
  if (m >= 9 && m <= 11) return "가을";
  return "겨울";
}

function buildEventTags(ev) {
  const tags = [];
  const sportLabel = (SPORT_META[ev.sport] || {}).label;
  if (sportLabel) tags.push({ label: sportLabel, href: `index.html?sport=${encodeURIComponent(ev.sport)}` });
  if (ev.region && ev.region !== "전국") tags.push({ label: ev.region, href: `index.html?region=${encodeURIComponent(ev.region)}` });
  try {
    const year = new Date(ev.date).getFullYear();
    const season = getSeason(ev.date);
    tags.push({ label: `${year}${season}`, href: `index.html?sport=${encodeURIComponent(ev.sport)}` });
  } catch (e) {}
  (ev.distances || []).forEach(d => {
    tags.push({ label: d, href: `index.html?sport=${encodeURIComponent(ev.sport)}` });
  });
  return tags;
}

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
  return { label: n < 0 ? "접수 마감" : `접수 D-${n}`, urgent: n >= 0 && n <= 7 };
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

async function renderSaveWidget(eventId) {
  const el = document.getElementById("saveWidget");
  if (!el) return;

  const { data: { session } } = await sb.auth.getSession();
  const { data: countData } = await sb.rpc("get_save_count", { p_event_id: eventId });
  const count = countData || 0;

  let isSaved = false;
  if (session?.user) {
    const { data } = await sb.from("event_saves").select("id").eq("event_id", eventId).eq("user_id", session.user.id).maybeSingle();
    isSaved = !!data;
  }

  el.innerHTML = `
    <button id="saveToggleBtn" class="modal-cal-btn" style="width:100%;">
      ${isSaved ? "★ 찜 완료" : "☆ 찜하기"} ${count > 0 ? `(${count}명이 찜함)` : ""}
    </button>
  `;

  document.getElementById("saveToggleBtn").addEventListener("click", async () => {
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

function timeAgo(dateStr) {
  const diffMs = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (days < 1) return "오늘";
  if (days < 30) return `${days}일 전`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}개월 전`;
  return `${Math.floor(months / 12)}년 전`;
}

let reviewSubmitBound = false;
async function renderReviews(eventId) {
  const summaryEl = document.getElementById("reviewSummary");
  const listEl = document.getElementById("reviewList");
  if (!summaryEl || !listEl) return;

  const { data: summaryData } = await sb.rpc("get_review_summary", { p_event_id: eventId });
  const summary = Array.isArray(summaryData) ? summaryData[0] : summaryData;
  const avg = summary ? Number(summary.avg_rating) : 0;
  const count = summary ? Number(summary.review_count) : 0;
  summaryEl.textContent = count > 0
    ? `⭐ 평균 ${avg.toFixed(1)}점 (${count}개 후기)`
    : "아직 후기가 없습니다. 첫 후기를 남겨보세요!";

  const { data: reviews } = await sb
    .from("event_reviews")
    .select("id, rating, comment, created_at, user_id")
    .eq("event_id", eventId)
    .order("created_at", { ascending: false })
    .limit(20);

  if (!reviews || reviews.length === 0) {
    listEl.innerHTML = "";
  } else {
    listEl.innerHTML = reviews.map(r => {
      const stars = "★".repeat(r.rating) + "☆".repeat(5 - r.rating);
      return `<div class="record-item"><p>${stars} <span class="hero-sub" style="display:inline;">· ${timeAgo(r.created_at)}</span></p>${r.comment ? `<p>${r.comment}</p>` : ""}</div>`;
    }).join("");
  }

  if (!reviewSubmitBound) {
    reviewSubmitBound = true;
    document.getElementById("reviewSubmitBtn").addEventListener("click", async () => {
      const { data: { session } } = await sb.auth.getSession();
      if (!session?.user) {
        alert("로그인이 필요한 기능입니다. 내 랭크 페이지에서 로그인해주세요.");
        location.href = "myrank.html";
        return;
      }
      const rating = Number(document.getElementById("reviewRatingSelect").value);
      const comment = document.getElementById("reviewComment").value.trim();
      const msgEl = document.getElementById("reviewMsg");
      const { error } = await sb.from("event_reviews").upsert({
        event_id: eventId,
        user_id: session.user.id,
        rating,
        comment: comment || null,
      }, { onConflict: "event_id,user_id" });
      msgEl.textContent = error ? "후기 등록에 실패했습니다." : "후기가 등록되었습니다. 감사합니다!";
      document.getElementById("reviewComment").value = "";
      renderReviews(eventId);
    });
  }
}

function setupShareAndMap(ev, pageUrl) {
  const mapLink = document.getElementById("mapLink");
  if (mapLink) {
    const query = encodeURIComponent(ev.location || ev.name);
    mapLink.href = `https://map.kakao.com/?q=${query}`;
  }

  const shareBtn = document.getElementById("shareEventBtn");
  if (shareBtn) {
    shareBtn.addEventListener("click", async () => {
      const shareData = {
        title: ev.name,
        text: `${ev.name} 같이 가실 분 찾습니다! | ${formatDate(ev.date, ev.time)} · ${ev.location}`,
        url: pageUrl,
      };
      if (navigator.share) {
        try { await navigator.share(shareData); } catch (e) { /* 사용자가 취소한 경우 등 무시 */ }
      } else if (navigator.clipboard) {
        await navigator.clipboard.writeText(pageUrl);
        alert("링크가 복사되었습니다! 친구에게 공유해보세요.");
      }
    });
  }
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

  renderSaveWidget(ev.id);
  renderReviews(ev.id);

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
    <div class="event-tags" style="margin-top:16px; display:flex; flex-wrap:wrap; gap:6px;">${buildEventTags(ev).map(tag => `<a href="${tag.href}" class="chip" style="text-decoration:none; font-size:12px; padding:4px 10px;">#${tag.label}</a>`).join("")}</div>
    <div id="weatherWidget"></div>
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

  setupShareAndMap(ev, pageUrl);
  renderWeatherWidget(ev);
}

init();

async function renderWeatherWidget(ev) {
  const el = document.getElementById("weatherWidget");
  if (!el || !ev.lat || !ev.lng) return;
  const target = new Date(ev.date + "T00:00:00");
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const diffDays = Math.round((target - today) / 86400000);
  if (diffDays < 0 || diffDays > 15) return;
  try {
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${ev.lat}&longitude=${ev.lng}&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode&timezone=Asia%2FSeoul&start_date=${ev.date}&end_date=${ev.date}`;
    const res = await fetch(url);
    const data = await res.json();
    const d = data.daily;
    if (!d || !d.time || d.time.length === 0) return;
    const tMax = Math.round(d.temperature_2m_max[0]);
    const tMin = Math.round(d.temperature_2m_min[0]);
    const rain = d.precipitation_probability_max[0];
    const code = d.weathercode[0];
    const iconMap = { 0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️", 45: "🌫️", 48: "🌫️", 51: "🌦️", 61: "🌧️", 63: "🌧️", 65: "🌧️", 71: "🌨️", 73: "🌨️", 75: "🌨️", 80: "🌦️", 95: "⛈️" };
    const icon = iconMap[code] || "🌡️";
    el.innerHTML = `
      <div style="margin-top:16px; padding:14px; border-radius:10px; background:var(--surface,#141414); border:1px solid var(--border,#2A2A2A); display:flex; align-items:center; gap:12px;">
        <div style="font-size:32px;">${icon}</div>
        <div>
          <p style="margin:0; font-size:13px; color:var(--ink-faint,#6A6A6A);">대회 당일 예상 날씨</p>
          <p style="margin:2px 0 0; font-size:16px; font-weight:700;">${tMin}° / ${tMax}°C · 강수확률 ${rain}%</p>
        </div>
      </div>
    `;
  } catch (e) {}
}
