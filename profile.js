// calrank 공개 러너 프로필
const SUPABASE_URL = "https://mlbzsqeoqlyvnyzeegeu.supabase.co";
const SUPABASE_KEY = "sb_publishable_byKae86vGA0M5NjoZC0ELw_NMkm8ObR";
const sb = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

const SPORT_LABEL = { marathon: "마라톤", cycling: "자전거", trail: "트레일", triathlon: "철인3종" };

function formatSecondsToTime(sec) {
  if (sec == null) return null;
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  return h > 0
    ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
    : `${m}:${String(s).padStart(2, "0")}`;
}

function getParam(name) {
  return new URLSearchParams(location.search).get(name);
}

function renderNotFound() {
  document.getElementById("profileContent").innerHTML = `
    <section class="hero">
      <h1>비공개 프로필입니다</h1>
      <p class="hero-sub">이 프로필은 존재하지 않거나 공개 설정이 되어 있지 않습니다.</p>
    </section>
    <a href="index.html" class="modal-cal-btn" style="display:inline-block; text-decoration:none; padding:12px 20px;">calrank 캘린더로 가기</a>
  `;
}

async function init() {
  const userId = getParam("id");
  if (!userId) { renderNotFound(); return; }

  const { data, error } = await sb.rpc("get_public_profile", { p_user_id: userId });
  const profile = Array.isArray(data) ? data[0] : data;

  if (error || !profile || !profile.display_name) { renderNotFound(); return; }

  const memberSince = profile.member_since
    ? new Date(profile.member_since).toLocaleDateString("ko-KR", { year: "numeric", month: "long" })
    : "";

  const bestTimes = [
    ["marathon", profile.best_marathon_seconds],
    ["trail", profile.best_trail_seconds],
    ["cycling", profile.best_cycling_seconds],
    ["triathlon", profile.best_triathlon_seconds],
  ].filter(([, sec]) => sec != null);

  const pageTitle = `${profile.display_name}님의 러너 프로필 — calrank`;
  document.getElementById("pageTitleTag").textContent = pageTitle;
  document.getElementById("ogTitle").setAttribute("content", pageTitle);
  const desc = `누적 ${profile.total_records}개 대회 기록 · 공식기록 ${profile.official_count}개 보유`;
  document.getElementById("metaDesc").setAttribute("content", desc);
  document.getElementById("ogDesc").setAttribute("content", desc);

  document.getElementById("profileContent").innerHTML = `
    <section class="hero">
      <h1>${profile.display_name}님의 러너 프로필</h1>
      <p class="hero-sub">${memberSince} 부터 calrank와 함께 달리는 중</p>
      <div class="hero-stats">
        <span class="hero-stat"><b>${profile.total_records}</b>개 완주 기록</span>
        <span class="hero-stat"><b>${profile.official_count}</b>개 공식기록 보유</span>
      </div>
    </section>
    <div class="record-form-card">
      <p class="record-form-title">종목별 최고 기록 (PR)</p>
      ${bestTimes.length === 0
        ? '<p class="import-sub">아직 등록된 기록이 없습니다.</p>'
        : bestTimes.map(([sport, sec]) => `
            <div class="record-item">
              <p>${SPORT_LABEL[sport]} · <strong>${formatSecondsToTime(sec)}</strong></p>
            </div>
          `).join("")
      }
    </div>
    <p class="import-sub" style="margin-top:16px;"><a href="index.html" style="color:inherit; text-decoration:underline;">calrank에서 나도 대회 찾아보기 →</a></p>
  `;
}

init();
