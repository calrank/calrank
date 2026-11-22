// calrank 메일 링크 확인 페이지
//
// 가입·비밀번호 재설정 메일의 버튼은 Supabase 주소가 아니라 이 페이지로 온다.
//   /auth-confirm.html?token_hash=...&type=signup|recovery|email_change|invite
// 보낸 도메인(mail.calrank.kr)과 링크 도메인(calrank.kr)을 같은 계열로 맞추면
// 받는 쪽 스팸 검사에서 유리하고, 사용자도 어디로 가는 링크인지 알아볼 수 있다.
//
// 버튼을 눌렀을 때만 verifyOtp 를 호출한다. 페이지가 열리자마자 인증하면 메일 보안
// 검사기가 링크를 먼저 열어 1회용 토큰을 써 버려, 정작 사용자는 "만료"를 보게 된다.

const SUPABASE_URL = "https://mlbzsqeoqlyvnyzeegeu.supabase.co";
const SUPABASE_KEY = "sb_publishable_byKae86vGA0M5NjoZC0ELw_NMkm8ObR";

const $ = (id) => document.getElementById(id);
const TYPES = {
  signup: {
    title: "이메일 인증",
    sub: "가입을 마무리합니다.",
    ready: "아래 버튼을 누르면 이메일 인증이 끝나고 로그인됩니다.",
    go: "인증 완료하기",
  },
  email_change: {
    title: "이메일 변경 확인",
    sub: "새 이메일 주소를 확인합니다.",
    ready: "아래 버튼을 누르면 이메일 주소 변경이 확정됩니다.",
    go: "변경 확정하기",
  },
  invite: {
    title: "초대 확인",
    sub: "초대받은 계정을 확인합니다.",
    ready: "아래 버튼을 누르면 계정이 활성화됩니다.",
    go: "계속하기",
  },
  recovery: {
    title: "비밀번호 재설정",
    sub: "새 비밀번호를 정하기 전에 링크를 확인합니다.",
    ready: "아래 버튼을 누르면 새 비밀번호를 정하는 화면으로 넘어갑니다.",
    go: "새 비밀번호 정하러 가기",
  },
};

function stage(name) {
  ["acLoading", "acReady", "acDone", "acFail"].forEach((id) => {
    $(id).classList.toggle("on", id === name);
  });
}

function scrubUrl() {
  try { history.replaceState(null, "", location.pathname); } catch (_) { /* 무시 */ }
}

function fail(title, msg, ctaText, ctaHref) {
  $("acTitle").textContent = "링크를 확인하지 못했습니다";
  $("acSub").textContent = "";
  $("acFailTitle").textContent = title;
  $("acFailMsg").textContent = msg;
  $("acFailCta").textContent = ctaText;
  $("acFailCta").setAttribute("href", ctaHref);
  stage("acFail");
}

// 링크가 만료됐거나 이미 쓴 경우: 종류별로 다음에 할 일을 알려 준다.
function expired(type) {
  if (type === "recovery") {
    return fail("링크 유효기간이 지났거나 이미 사용했습니다",
      "재설정 링크는 한 번만 쓸 수 있고 일정 시간이 지나면 만료됩니다. 새 링크를 받아 주세요.",
      "재설정 링크 다시 받기", "reset.html");
  }
  if (type === "signup") {
    return fail("링크 유효기간이 지났거나 이미 인증했습니다",
      "이미 인증을 마쳤다면 로그인하면 됩니다. 로그인이 안 되면 로그인 화면에서 회원가입을 다시 눌러 새 인증 메일을 받을 수 있습니다.",
      "로그인하기", "myrank.html");
  }
  return fail("링크를 사용할 수 없습니다",
    "유효기간이 지났거나 이미 사용한 링크입니다. 로그인 화면에서 다시 시도해 주세요.",
    "로그인하기", "myrank.html");
}

function done(type) {
  scrubUrl();
  if (type === "recovery") { location.replace("reset.html"); return; }
  // 같은 탭에서는 storage 이벤트가 오지 않아 헤더가 로그아웃 모양으로 남는다. 한 번 알려 준다.
  try { window.dispatchEvent(new StorageEvent("storage", { key: "sb-mlbzsqeoqlyvnyzeegeu-auth-token" })); } catch (_) { /* 무시 */ }
  $("acTitle").textContent = TYPES[type].title;
  $("acSub").textContent = "";
  if (type === "signup" || type === "invite") {
    $("acDoneTitle").textContent = "이메일 인증이 끝났습니다";
    $("acDoneMsg").textContent = "로그인된 상태입니다. 닉네임은 나중에 정해도 됩니다.";
    $("acNickHint").hidden = false;
  } else {
    $("acDoneTitle").textContent = "이메일 주소를 바꿨습니다";
    $("acDoneMsg").textContent = "다음 로그인부터 새 이메일 주소를 쓰면 됩니다.";
  }
  stage("acDone");
}

function boot() {
  const q = new URLSearchParams(location.search);
  const hash = (q.get("token_hash") || "").trim();
  const type = (q.get("type") || "").trim();

  // 토큰은 16진 문자열이다. 그 밖의 값은 서버에 보내지 않는다.
  if (!/^[A-Za-z0-9_-]{16,128}$/.test(hash) || !TYPES[type]) {
    scrubUrl();
    return fail("링크 주소가 올바르지 않습니다",
      "메일의 버튼을 그대로 눌러 들어와야 합니다. 주소가 잘렸다면 메일에서 다시 눌러 주세요.",
      "로그인하기", "myrank.html");
  }

  const t = TYPES[type];
  $("acTitle").textContent = t.title;
  $("acSub").textContent = t.sub;
  $("acReadyMsg").textContent = t.ready;
  $("acGo").textContent = t.go;
  stage("acReady");

  $("acNick").addEventListener("click", (e) => {
    e.preventDefault();
    if (window.CalrankAuth) window.CalrankAuth.openSheet();
  });

  let busy = false;
  $("acGo").addEventListener("click", async () => {
    if (busy) return;
    busy = true;
    $("acGo").disabled = true;
    $("acMsg").textContent = "확인하는 중...";
    let sb;
    try {
      sb = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
    } catch (_) {
      busy = false; $("acGo").disabled = false;
      $("acMsg").textContent = "연결하지 못했습니다. 잠시 뒤 다시 눌러 주세요.";
      return;
    }
    try {
      const { error } = await sb.auth.verifyOtp({ token_hash: hash, type });
      if (!error) return done(type);
      const m = String(error.message || "") + String(error.code || "");
      if (error.status === 429 || /rate|too many/i.test(m)) {
        busy = false; $("acGo").disabled = false;
        $("acMsg").textContent = "요청이 많습니다. 잠시 뒤 다시 눌러 주세요.";
        return;
      }
      if (/expired|invalid|used|otp|token/i.test(m) || error.status === 403 || error.status === 400 || error.status === 422) {
        scrubUrl();
        return expired(type);
      }
      busy = false; $("acGo").disabled = false;
      $("acMsg").textContent = "인증하지 못했습니다. 잠시 뒤 다시 눌러 주세요.";
    } catch (_) {
      busy = false; $("acGo").disabled = false;
      $("acMsg").textContent = "연결하지 못했습니다. 인터넷 연결을 확인하고 다시 눌러 주세요.";
    }
  });
}

boot();
