const SUPABASE_URL = "https://mlbzsqeoqlyvnyzeegeu.supabase.co";
const SUPABASE_KEY = "sb_publishable_byKae86vGA0M5NjoZC0ELw_NMkm8ObR";
const sb = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

let currentUser = null;

async function init() {
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
      event_date: document.getElementById("seDate").value || null,
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
