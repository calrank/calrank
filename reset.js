// calrank 비밀번호 재설정 페이지
//
// 흐름: myrank.html 에서 resetPasswordForEmail(email, {redirectTo: /reset.html})
//       -> 메일의 링크를 누르면 이 페이지로 복구 세션을 들고 돌아온다
//       -> updateUser({password}) 로 새 비밀번호를 저장한다
//
// supabase-js 는 기본값(detectSessionInUrl: true)으로 주소의 토큰을 스스로
// 처리하는데 그게 비동기라서, 이벤트와 폴링을 함께 걸어 두 경로 모두 받는다.
// 또 링크 방식이 implicit(#access_token=...) 인지 PKCE(?code=...) 인지에
// 따라 이벤트 이름이 달라지므로, 이름을 따지지 않고 "세션이 생겼는지"만 본다.

const SUPABASE_URL = "https://mlbzsqeoqlyvnyzeegeu.supabase.co";
const SUPABASE_KEY = "sb_publishable_byKae86vGA0M5NjoZC0ELw_NMkm8ObR";

const sb = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

const $ = (id) => document.getElementById(id);

const RAW = (location.hash || "") + (location.search || "");
const HAS_TOKEN = /access_token=|type=recovery|[?&]code=/.test(RAW);
const HAS_ERROR = /[#?&]error=|error_code=/.test(RAW);

let settled = false;

function say(el, text, kind) {
  el.textContent = text;
  el.className = "auth-msg" + (kind ? " " + kind : "");
}

function stage(name) {
  ["rsLoading", "rsForm", "rsExpired", "rsDone"].forEach((id) => {
    $(id).classList.toggle("on", id === name);
  });
}

function openPasswordForm() {
  if (settled) return;
  settled = true;
  stage("rsForm");
  $("rsPw1").focus();
}

function openExpired(message) {
  if (settled) return;
  settled = true;
  if (message) $("rsExpiredMsg").textContent = message;
  stage("rsExpired");
}

// 에러 메시지를 사람이 읽을 수 있는 말로 바꾼다
function friendly(error) {
  const m = String((error && error.message) || "");
  const status = error && error.status;
  if (status === 429 || /rate limit|too many|over_email_send/i.test(m)) {
    return "잠시 후 다시 시도해 주세요. 메일 발송 횟수에 제한이 있습니다.";
  }
  if (/should be different|same.{0,12}(old|previous)/i.test(m)) {
    return "이전과 다른 비밀번호를 입력해 주세요.";
  }
  if (/at least|too short|6 characters|weak.{0,10}password/i.test(m)) {
    return "비밀번호는 6자 이상이어야 합니다.";
  }
  if (/session|expired|invalid|jwt|token/i.test(m)) {
    return "링크가 만료됐습니다. 메일을 다시 받아 주세요.";
  }
  return m || "알 수 없는 오류가 발생했습니다.";
}

// 토큰을 주소창과 방문기록에서 지운다 (어깨 너머로 노출되거나 공유되지 않도록)
function scrubUrl() {
  try {
    history.replaceState(null, "", location.pathname);
  } catch (_) { /* 무시 */ }
}

async function submitNewPassword(e) {
  e.preventDefault();
  const msg = $("rsMsg");
  const btn = $("rsPwBtn");
  const p1 = $("rsPw1").value;
  const p2 = $("rsPw2").value;

  if (p1.length < 6) return say(msg, "비밀번호는 6자 이상이어야 합니다.", "error");
  if (p1 !== p2) return say(msg, "두 비밀번호가 서로 다릅니다. 다시 확인해 주세요.", "error");

  say(msg, "변경 중...");
  btn.disabled = true;
  const { error } = await sb.auth.updateUser({ password: p1 });
  btn.disabled = false;

  if (error) {
    // 세션이 끊긴 경우엔 다시 받을 수 있는 화면으로 돌려보낸다
    if (/session|expired|jwt|not authenticated|auth session missing/i.test(String(error.message || ""))) {
      settled = false;
      scrubUrl();
      openExpired("링크 유효기간이 지났습니다. 가입한 이메일을 넣으면 새 링크를 보내드립니다.");
      return;
    }
    return say(msg, friendly(error), "error");
  }

  scrubUrl();
  settled = true;
  stage("rsDone");
}

async function resendLink(e) {
  e.preventDefault();
  const msg = $("rsAgainMsg");
  const btn = $("rsAgainBtn");
  const email = $("rsAgainEmail").value.trim();
  if (!email) return;

  say(msg, "보내는 중...");
  btn.disabled = true;
  const { error } = await sb.auth.resetPasswordForEmail(email, {
    redirectTo: location.origin + "/reset.html",
  });
  btn.disabled = false;

  if (error) return say(msg, friendly(error), "error");

  // 가입된 메일인지 여부는 알려주지 않는다 (계정 존재 여부가 드러나지 않도록)
  say(msg, email + " 로 재설정 링크를 보냈습니다. 받은 편지함과 스팸함을 확인해 주세요.", "ok");
}

async function boot() {
  $("rsPwForm").addEventListener("submit", submitNewPassword);
  $("rsAgainForm").addEventListener("submit", resendLink);

  // Supabase 가 링크를 거부한 경우 (#error=access_denied&error_code=otp_expired 등).
  // 이 판정은 세션 복구보다 먼저 해야 한다. 뒤로 미루면, 같은 브라우저에 남아 있던
  // 다른 사람의 로그인 세션이 먼저 살아나 "만료된 링크로 남의 비밀번호를 바꾸는"
  // 화면이 열린다(공용 PC). 거부된 링크는 무조건 재발송 화면으로 보낸다.
  if (HAS_ERROR) {
    // hash 와 search 를 따로 읽는다 (둘을 이어 붙이면 값이 섞인다)
    const parts = [location.hash.replace(/^#/, ""), location.search.replace(/^\?/, "")];
    let code = "";
    for (const part of parts) {
      const p = new URLSearchParams(part);
      code = code || p.get("error_code") || p.get("error") || "";
    }
    scrubUrl();
    openExpired(/expired/i.test(code)
      ? "링크 유효기간이 지났습니다. 가입한 이메일을 넣으면 새 링크를 보내드립니다."
      : "이 링크로는 비밀번호를 바꿀 수 없습니다. 가입한 이메일을 넣으면 새 링크를 보내드립니다.");
    return;
  }

  // 토큰 처리가 끝나면 세션이 생기고 이벤트가 온다
  sb.auth.onAuthStateChange((_event, session) => {
    if (session) openPasswordForm();
  });

  // 토큰이 있으면 처리될 때까지 잠깐 기다린다 (최대 약 3초)
  const tries = HAS_TOKEN ? 30 : 1;
  for (let i = 0; i < tries; i++) {
    const { data } = await sb.auth.getSession();
    if (data && data.session) {
      scrubUrl();
      openPasswordForm();
      return;
    }
    if (settled) return;
    if (i < tries - 1) await new Promise((r) => setTimeout(r, 100));
  }

  // 토큰 없이 그냥 들어온 경우에도 바로 메일을 받을 수 있게 해 준다
  openExpired();
}

boot();
