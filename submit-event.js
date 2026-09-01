const SUPABASE_URL = "https://mlbzsqeoqlyvnyzeegeu.supabase.co";
const SUPABASE_KEY = "sb_publishable_byKae86vGA0M5NjoZC0ELw_NMkm8ObR";
const sb = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

let currentUser = null;

function populateSubmitDateSelects() {
  const yearSel = document.getElementById("seYear");
  const monthSel = document.getElementById("seMonth");
  const daySel = document.getElementById("seDay");
  if (!yearSel || yearSel.options.length > 0) return;
  [yearSel, monthSel, daySel].forEach(sel => {
    const blank = document.createElement("option");
    blank.value = ""; blank.textContent = "미정";
    sel.appendChild(blank);
  });
  const nowY = new Date().getFullYear();
  for (let y = nowY + 2; y >= nowY; y--) {
    const opt = document.createElement("option");
    opt.value = y; opt.textContent = y + "년";
    yearSel.appendChild(opt);
  }
  for (let m = 1; m <= 12; m++) {
    const opt = document.createElement("option");
    opt.value = String(m).padStart(2, "0"); opt.textContent = m + "월";
    monthSel.appendChild(opt);
  }
  for (let d = 1; d <= 31; d++) {
    const opt = document.createElement("option");
    opt.value = String(d).padStart(2, "0"); opt.textContent = d + "일";
    daySel.appendChild(opt);
  }
}

function getSubmitDateValue() {
  const y = document.getElementById("seYear").value;
  const m = document.getElementById("seMonth").value;
  const d = document.getElementById("seDay").value;
  if (!y || !m || !d) return null;
  return `${y}-${m}-${d}`;
}

async function init() {
  populateSubmitDateSelects();
  const { data: { session } } = await sb.auth.getSession();
  if (session?.user) {
    currentUser = session.user;
    document.getElementById("submitFormSection").style.display = "block";
    document.getElementById("loginRequiredNotice").style.display = "none";
  } else {
    document.getElementById("submitFormSection").style.display = "none";
    document.getElementById("loginRequiredNotice").style.display = "block";
  }

  document.getElementById("submitEventForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const msgEl = document.getElementById("submitMsg");
    const name = document.getElementById("seName").value.trim();
    if (!name) return;

    const payload = {
      submitted_by: currentUser.id,
      event_name: name,
      sport: document.getElementById("seSport").value,
      event_date: getSubmitDateValue(),
      location: document.getElementById("seLocation").value.trim() || null,
      region: document.getElementById("seRegion").value.trim() || null,
      apply_url: document.getElementById("seApplyUrl").value.trim() || null,
      notes: document.getElementById("seNotes").value.trim() || null,
    };

    const { error } = await sb.from("event_submissions").insert(payload);
    if (error) {
      msgEl.textContent = "제보 등록에 실패했습니다. 잠시 후 다시 시도해주세요.";
    } else {
      msgEl.textContent = "제보해주셔서 감사합니다! 검토 후 캘린더에 반영해드릴게요.";
      document.getElementById("submitEventForm").reset();
    }
  });
}

init();
