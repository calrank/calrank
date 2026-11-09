"""
calrank 대회 상세 정적 페이지 생성 스크립트

배경: event.html?id=... 는 서버가 "불러오는 중…"만 내려주고 내용을 자바스크립트가
채우는 구조라, 검색엔진(특히 JS 실행이 약한 크롤러)에게는 대회 정보가 거의
보이지 않았다. 이 스크립트는 events.json의 대회마다 서버 단계에서 이미 내용이
채워진 정적 페이지(e/<id>.html)를 만든다.

- 템플릿은 event.html을 그대로 재사용한다. (event.html을 고치면 다음 생성 때 반영)
- 페이지에 들어가는 문장은 전부 events.json의 실제 값으로만 조립한다.
  후기·별점처럼 실제로 없는 정보는 절대 만들어 넣지 않는다.
- 기존 event.js가 그대로 동작하도록 window.EVENT_ID 등을 심어 준다.
  (후기·찜하기·날씨·공유는 정적 페이지에서도 같은 코드로 작동한다)
"""
import html
import json
import math
import re
from datetime import date, datetime, timedelta
import sys
from pathlib import Path
from urllib.parse import quote, unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_nav import site_header  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://calrank.vercel.app"
OUT_DIR = ROOT / "e"
# "○○마라톤 기록"은 대회가 끝난 뒤에 검색된다. 60일 만에 페이지를 지우면
# 검색 수요가 생기는 바로 그 시점에 받을 페이지가 없어지므로 길게 보존한다.
KEEP_DAYS_AFTER = 1095  # 약 3년

SPORT_LABEL = {
    "marathon": "마라톤", "cycling": "자전거", "trail": "트레일러닝",
    "triathlon": "철인3종", "inline": "인라인",
}
REGION_SLUG = {
    "서울": "seoul", "경기": "gyeonggi", "인천": "incheon", "부산": "busan",
    "대구": "daegu", "광주": "gwangju", "대전": "daejeon", "울산": "ulsan",
    "세종": "sejong", "강원": "gangwon", "충북": "chungbuk", "충남": "chungnam",
    "전북": "jeonbuk", "전남": "jeonnam", "경북": "gyeongbuk", "경남": "gyeongnam",
    "제주": "jeju",
}
WEEKDAY = ["월", "화", "수", "목", "금", "토", "일"]


def josa_eun_neun(word: str) -> str:
    """마지막 글자의 받침 유무로 '은' / '는'을 고른다. (한글이 아니면 '는')"""
    w = (word or "").strip()
    for ch in reversed(w):
        if "가" <= ch <= "힣":
            return "은" if (ord(ch) - 0xAC00) % 28 else "는"
        if ch.isalnum():
            # 숫자·영문으로 끝나는 이름은 읽는 소리 기준이 필요하지만, 안전하게 '는' 사용
            break
    return "는"


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def parse_date(s):
    try:
        return datetime.strptime((s or "")[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def date_ko(d: date) -> str:
    return f"{d.year}년 {d.month}월 {d.day}일({WEEKDAY[d.weekday()]})"


def page_url_for(ev_id: str) -> str:
    return f"{SITE}/e/{quote(ev_id)}.html"


def build_summary(ev: dict) -> str:
    """events.json의 실제 값만으로 조립한 요약 문장."""
    d = parse_date(ev.get("date"))
    sport = SPORT_LABEL.get(ev.get("sport"), "스포츠")
    name = ev.get("name", "")
    place = (ev.get("location") or "").strip()
    parts = []

    is_past = bool(d) and d < date.today()
    when = date_ko(d) if d else "일정 미확인"
    t = ev.get("time")
    if t and re.match(r"^\d{1,2}:\d{2}", str(t)):
        when += f" {t[:5]} 출발"
    verb = "열린" if is_past else "열리는"
    if place:
        parts.append(f"{name}{josa_eun_neun(name)} {when}, {place}에서 {verb} {sport} 대회입니다.")
    else:
        parts.append(f"{name}{josa_eun_neun(name)} {when}에 {verb} {sport} 대회입니다.")

    # 원본에 낱개와 합친 문자열이 섞여 들어온다. 목록 페이지에만 쓰던
    # 손질을 여기에도 건다. 안 그러면 "26km, 18km, 10km, 26km,18km,10km"
    # 처럼 같은 거리가 두 번 찍힌다. (822개 중 34개가 이 상태였다)
    dist = dedupe_distances(ev.get("distances"))
    if dist:
        parts.append(f"종목은 {', '.join(dist)}입니다.")

    org = (ev.get("organizer") or "").strip()
    if org:
        parts.append(f"주최는 {org}입니다.")

    rd = parse_date(ev.get("regDeadline"))
    if is_past:
        # 끝난 대회 설명도 '접수'가 아니라 '기록'으로 맺는다. 검색 결과에
        # 제목 바로 아래 붙는 문장이라, 여기까지 맞춰야 말이 이어진다.
        parts.append("이미 종료된 대회입니다. 완주 기록을 넣으면 나이와 성별을 "
                     "반영한 등급을 바로 확인할 수 있습니다.")
        return " ".join(parts)
    if ev.get("regClosed"):
        parts.append("접수는 이미 마감되었습니다.")
    elif rd:
        parts.append(f"접수 마감일은 {date_ko(rd)}입니다.")
    else:
        parts.append("접수 기간은 주최 측 공지에서 확인해 주세요.")
    return " ".join(parts)


# --- 기록 수준 한 단락 (level.js / 등급표와 같은 모델) ---
_NAMED_DIST = {"하프": 21.0975, "풀코스": 42.195, "풀": 42.195}

_GRADE_SLUG = {5.0: "5km", 10.0: "10km", 21.0975: "half", 42.195: "full"}

# 등급 기준은 등급표·계산기와 같은 WMA 2025 연령 기준표를 쓴다.
# 여기서만 다른 모델을 쓰면 같은 기록에 다른 등급이 나온다.
import wma_standards as wma  # noqa: E402

TIER_BOUNDS = [(72, "상당한 러너"), (65, "러닝 상급자"), (59, "매우 좋은 편"),
               (51, "상당히 좋은 편"), (45, "꾸준한 러너"), (39, "보통"), (0, "이제 시작")]
BOUND = {label: pct for pct, label in TIER_BOUNDS}
_DIST_KEY = ((5.0, "5km"), (10.0, "10km"), (21.0975, "half"), (42.195, "full"))


def _dist_key(km):
    for value, key in _DIST_KEY:
        if abs(km - value) < 0.05:
            return key
    return None


def _boundary(bound_pct, age, gender, km):
    """그 등급을 받을 수 있는 가장 느린 기록(초). 표 밖 거리는 None."""
    key = _dist_key(km)
    if key is None:
        return None
    return math.floor(wma.standard(gender, key, age) / (bound_pct / 100.0))


def _fmt_time(sec):
    h, r = divmod(int(sec), 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _parse_km(raw):
    """events.json의 distances에서 Riegel 환산이 유효한 거리만 뽑는다."""
    out = []
    items = raw if isinstance(raw, list) else [raw]
    for item in items:
        for part in re.split(r"[·,/]| 및 ", str(item)):
            t = part.strip().lower()
            if not t:
                continue
            km = None
            for nm, v in _NAMED_DIST.items():
                if nm in t:
                    km = v
                    break
            if km is None:
                m = re.search(r"(\d+(?:\.\d+)?)\s*km", t)
                if m:
                    km = float(m.group(1))
            # 울트라는 Riegel 환산 신뢰도가 떨어져 제외한다
            if km is not None and 3.0 <= km <= 42.3 and km not in out:
                out.append(km)
    return sorted(out)


def _km_label(km):
    if abs(km - 21.0975) < 0.01:
        return "하프"
    if abs(km - 42.195) < 0.01:
        return "풀코스"
    return f"{km:g}km"


# 등급 계산기로 보낼 때 쓸 주 거리. build_record_standards 와 같은 우선순위라,
# 페이지가 설명하는 거리와 링크가 가리키는 거리가 어긋나지 않는다.
def _main_km(ev: dict):
    kms = _parse_km(ev.get("distances"))
    for pref in (10.0, 21.0975, 5.0, 42.195):
        if pref in kms:
            return pref
    return None


def build_record_standards(ev: dict) -> str:
    """이 대회 거리 기준으로 '어느 정도면 어느 수준인지'를 짧은 산문으로."""
    kms = _parse_km(ev.get("distances"))
    if not kms:
        return ""
    # 가장 수요가 많은 거리 하나만 문장으로 다룬다 (페이지가 표로 뒤덮이지 않게)
    main = None
    for pref in (10.0, 21.0975, 5.0, 42.195):
        if pref in kms:
            main = pref
            break
    if main is None:
        # WMA가 기준을 내는 네 거리가 아니면 등급 문단을 쓰지 않는다.
        # 억지로 환산해 붙이면 숫자의 근거가 사라진다. (822개 중 72개)
        return ""

    lab = _km_label(main)
    m_avg = _fmt_time(_boundary(BOUND["꾸준한 러너"], 40, "male", main))
    m_good = _fmt_time(_boundary(BOUND["매우 좋은 편"], 40, "male", main))
    f_avg = _fmt_time(_boundary(BOUND["꾸준한 러너"], 40, "female", main))
    f_good = _fmt_time(_boundary(BOUND["매우 좋은 편"], 40, "female", main))

    slug = _GRADE_SLUG.get(main)
    link = ""
    if slug:
        link = (f' 나이별 전체 기준표는 '
                f'<a href="/grade-{slug}-male.html">남성</a>·'
                f'<a href="/grade-{slug}-female.html">여성</a> 등급표에 있습니다.')

    return (
        f"이 대회 {lab}에서 40대 남성 {m_avg}, 40대 여성 {f_avg}이 "
        f"'꾸준한 러너' 선입니다. 나이와 성별, 자기 기록을 넣으면 등급이 바로 나옵니다 — "
        f'<a href="/level.html?d={main:g}">{lab} 등급 확인하기 →</a>'
        f"{link}"
    )


def build_meta_description(ev: dict) -> str:
    text = build_summary(ev)
    return text if len(text) <= 150 else text[:147] + "…"


def _time_placeholder(km: float) -> str:
    """입력 예시는 그 거리에서 흔한 기록으로 보여 준다."""
    if not km:
        return "52:30"
    if km <= 6:
        return "25:30"
    if km <= 12:
        return "52:30"
    if km <= 25:
        return "1:45:30"
    return "3:55:00"


def build_title(ev: dict) -> str:
    d = parse_date(ev.get("date"))
    base = ev.get("name", "")
    tail = []
    if d:
        tail.append(f"{d.year}.{d.month:02d}.{d.day:02d}")
    if ev.get("region") and ev["region"] not in ("전국", "미표기"):
        tail.append(ev["region"])
    suffix = " ".join(tail)
    # 끝난 대회 제목에 "일정·접수"를 그대로 두면, 검색 결과에 보이는 문구가
    # 아무도 더는 찾지 않는 말이 된다(728장이 그 상태였다). 대회가 끝나면
    # 사람들이 찾는 건 '내 기록이 몇 등급인가'다 — 본문은 이미 그렇게
    # 바뀌는데 제목만 안 따라갔다. 한 번 지난 대회는 계속 이 제목을 쓴다.
    # 기간을 두면 대회가 그 기간을 벗어날 때 제목이 되돌아가 버린다.
    is_past = bool(d) and d < date.today()
    kind = "완주 기록 등급" if is_past else "대회 일정·접수"
    return f"{base} — {suffix} {kind} | calrank" if suffix else f"{base} {kind} | calrank"


def build_event_jsonld(ev: dict, url: str, desc: str) -> dict:
    d = parse_date(ev.get("date"))
    start = ev.get("date", "")[:10]
    t = ev.get("time")
    if d and t and re.match(r"^\d{1,2}:\d{2}", str(t)):
        hh, mm = str(t)[:5].split(":")
        start = f"{start}T{int(hh):02d}:{mm}:00+09:00"
    place = (ev.get("location") or ev.get("region") or "대한민국").strip()
    schema = {
        "@context": "https://schema.org",
        "@type": "SportsEvent",
        "name": ev.get("name", ""),
        "description": desc,
        "startDate": start,
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "eventStatus": "https://schema.org/EventScheduled",
        "location": {
            "@type": "Place",
            "name": place,
            "address": {"@type": "PostalAddress", "addressCountry": "KR", "streetAddress": place},
        },
        "image": f"{SITE}/og-image.png",
        "url": url,
    }
    if ev.get("region") and ev["region"] not in ("전국", "미표기"):
        schema["location"]["address"]["addressRegion"] = ev["region"]
    if ev.get("organizer"):
        schema["organizer"] = {"@type": "Organization", "name": ev["organizer"]}
    # aggregateRating은 실제 후기가 있을 때 event.js가 채워 넣는다. 여기선 절대 넣지 않는다.
    return schema


def build_breadcrumb_jsonld(ev: dict) -> dict:
    items = [{"@type": "ListItem", "position": 1, "name": "calrank", "item": f"{SITE}/index.html"}]
    if ev.get("sport") in SPORT_LABEL:
        items.append({"@type": "ListItem", "position": len(items) + 1,
                      "name": SPORT_LABEL[ev["sport"]],
                      "item": f"{SITE}/index.html?sport={ev['sport']}"})
    if ev.get("region") and ev["region"] not in ("전국", "미표기"):
        items.append({"@type": "ListItem", "position": len(items) + 1,
                      "name": ev["region"],
                      "item": f"{SITE}/index.html?region={quote(ev['region'])}"})
    items.append({"@type": "ListItem", "position": len(items) + 1, "name": ev.get("name", "")})
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items}


def ld_script(script_id: str, data: dict) -> str:
    body = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/ld+json" id="{script_id}">{body}</script>'


def build_static_content(ev: dict) -> str:
    """event.js가 렌더링하는 것과 같은 마크업(같은 클래스)으로 미리 채운 본문."""
    sport = SPORT_LABEL.get(ev.get("sport"), "")
    d = parse_date(ev.get("date"))
    when = date_ko(d) if d else "미확인"
    t = ev.get("time")
    if t and re.match(r"^\d{1,2}:\d{2}", str(t)):
        when += f" {t[:5]}"
    organizer = esc(ev.get("organizer") or "미확인")
    if ev.get("organizerPhone"):
        organizer += " · " + esc(ev["organizerPhone"])
    apply_url = ev.get("applyUrl") or ev.get("sourceUrl") or "#"

    # 지난 대회에 "신청하기"를 그대로 띄우면 죽은 링크를 약속하는 셈이다.
    # 660장이 그 상태였다. 라벨을 사실대로 바꾸고, 대신 그 자리에
    # 기록을 넣어 볼 길을 놓는다 — 대회를 막 뛰고 온 사람에게는 그게 용건이다.
    d = parse_date(ev.get("date"))
    is_past = bool(d) and d < date.today()
    km = _main_km(ev)
    grade_href = f"level.html?d={km:g}" if km else ""

    if is_past:
        cta = (
            f'<a class="modal-apply-btn ev-cta-sub" style="display:inline-block;'
            f'text-decoration:none;margin-top:24px;" href="{esc(apply_url)}" '
            f'target="_blank" rel="noopener">대회 홈페이지 ↗</a>'
        )
        if grade_href:
            # 링크 하나로 끝내면 누른 다음에야 입력창을 만난다. 그 사이에
            # 사람이 빠진다. JS 없이 GET 폼으로 넘기면 거리와 시간이 채워진
            # level.html 이 열린다(prefillFromUrl 이 d·t 를 읽는다).
            # 계산도 기록 저장도 그대로 level.html 이 맡으므로 자산 경로는
            # 건드리지 않는다.
            ph = _time_placeholder(km)
            # 그 대회 당일 기상청 실측 일평균기온이 있으면 같이 넘긴다.
            # level.js 가 이걸 받아 15℃ 기준으로 환산한 등급을 함께 보여 준다.
            # 평년값(climate)은 넘기지 않는다 — 그 날의 날씨가 아니라 그
            # 날짜의 10년 평균이라서, 보정의 근거로 쓰면 거짓말이 된다.
            wx = ev.get("weather")
            avg_ta = wx.get("avgTa") if isinstance(wx, dict) else None
            if not isinstance(avg_ta, (int, float)):
                avg_ta = None
            ev_name = (ev.get("name") or "").strip()[:40]
            ask = "이 대회 다녀오셨나요? 기록을 넣어 보세요."
            if avg_ta is not None and avg_ta > 15:
                ask = (f"이 대회는 당일 평균 {avg_ta:.1f}℃였습니다. "
                       f"그 더위까지 반영해서 등급을 봅니다.")
            elif avg_ta is not None:
                ask = (f"이 대회는 당일 평균 {avg_ta:.1f}℃였습니다. "
                       f"기록을 넣어 보세요.")
            extra = ""
            if avg_ta is not None:
                extra = (f'<input type="hidden" name="tc" value="{avg_ta:.1f}">'
                         f'<input type="hidden" name="ev" value="{esc(ev_name)}">')
            cta = (
                f'<div class="ev-after">'
                f'<p class="ev-after-q">{esc(ask)}</p>'
                f'<form class="ev-grade-form" action="/level.html" method="get">'
                f'<input type="hidden" name="d" value="{km:g}">'
                f'{extra}'
                f'<label class="ev-grade-sr" for="evGradeTime">완주시간</label>'
                f'<input class="ev-grade-t" id="evGradeTime" name="t" type="text" '
                f'inputmode="numeric" autocomplete="off" placeholder="{ph}" '
                f'aria-describedby="evGradeHint">'
                f'<button type="submit">등급 보기 →</button>'
                f'</form>'
                # 형식 안내는 placeholder 가 아니라 여기에 둔다. 스크린리더는
                # placeholder 를 건너뛰는 일이 있어서, 읽히는 쪽에 적어야 한다.
                f'<p class="ev-after-n" id="evGradeHint">분:초 또는 시:분:초로 '
                f'적어 주세요. 나이와 성별까지 반영하고, 가입은 필요 없습니다.</p>'
                f'</div>'
            ) + cta
    else:
        cta = (
            f'<a class="modal-apply-btn" style="display:inline-block;'
            f'text-decoration:none;margin-top:24px;" href="{esc(apply_url)}" '
            f'target="_blank" rel="noopener">신청하기 ↗</a>'
        )
        if grade_href:
            cta += (
                f'<p class="ev-goal"><a href="{grade_href}">'
                f'목표 기록을 정해 볼까요 — 등급으로 확인하기 →</a></p>'
            )

    return (
        f'<section class="hero"><p class="hero-sub">{esc(sport)}</p><h1>{esc(ev.get("name"))}</h1></section>'
        f'<div class="modal-fields" style="margin-top:24px;">'
        f'<div class="modal-field-row"><span class="k">일시</span><span class="v">{esc(when)}</span></div>'
        f'<div class="modal-field-row"><span class="k">장소</span><span class="v">{esc(ev.get("location") or "미확인")}</span></div>'
        f'<div class="modal-field-row"><span class="k">종목/거리</span><span class="v">{esc(" / ".join(dedupe_distances(ev.get("distances"))))}</span></div>'
        f'<div class="modal-field-row"><span class="k">주최</span><span class="v">{organizer}</span></div>'
        f'</div>'
        f'{cta}'
    )


# ── 대회 당일의 사정 ────────────────────────────────────────────────
#
# 822장이 서로 2/3쯤 같은 글이라 색인이 안 되고 있었다. 틀을 두껍게 하는 걸로는
# 안 되고, 대회마다 실제로 다른 사실이 들어가야 한다. 지금 가진 것 중에
# 그런 게 둘 있다 — 좌표와 날짜로 계산되는 해 뜨는 시각, 그리고 같은 날
# 전국에 몇 개가 열리는지. 둘 다 계산이지 베낀 글이 아니다.
import sun_times  # noqa: E402


def _hhmm(minutes):
    m = int(round(minutes))
    return "%d:%02d" % (m // 60 % 24, m % 60)


def _start_minutes(ev):
    t = str(ev.get("time") or "")
    m = re.match(r"^(\d{1,2}):(\d{2})", t)
    if not m:
        return None
    h, mm = int(m.group(1)), int(m.group(2))
    if not (0 <= h <= 23 and 0 <= mm <= 59):
        return None
    return h * 60 + mm


def build_day_context(ev: dict, same_day: dict) -> str:
    """해 뜨는 시각과 같은 날 사정. 대회마다 다른 값만 쓴다."""
    lat, lng = ev.get("lat"), ev.get("lng")
    d = parse_date(ev.get("date"))
    if not (lat and lng and d):
        return ""
    try:
        rise, set_ = sun_times.sun_times(float(lat), float(lng), d)
    except Exception:                               # noqa: BLE001
        return ""
    if rise is None:
        return ""

    place = (ev.get("location") or "").split()[0] if ev.get("location") else ""
    where = place or (ev.get("region") or "이 지역")
    bits = []

    evening = False
    start = _start_minutes(ev)
    if start is None:
        bits.append(
            "대회 날 %s의 해는 %s에 떠서 %s에 집니다. 출발 시각은 주최 측 공지를 "
            "확인해 주세요." % (esc(where), _hhmm(rise), _hhmm(set_)))
    else:
        # 해 뜨는 쪽만 보면 저녁 대회에 한낮 조언이 붙는다(울릉나이트런 19:30 에
        # "모자와 선크림"이 붙었던 적이 있다). 일출과 일몰을 같이 본다.
        gap = start - rise
        to_set = set_ - start
        head = "%s 출발입니다. 그날 %s의 일출은 %s, 일몰은 %s인데," % (
            _hhmm(start), esc(where), _hhmm(rise), _hhmm(set_))

        if start > set_ + 20:
            evening = True
            bits.append(
                "%s 해가 진 뒤에 출발하는 야간 대회입니다. 처음부터 끝까지 "
                "어두우니 헤드랜턴과 반사 띠는 선택이 아니라 필수고, 발밑이 안 "
                "보이는 구간에서 속도를 줄이는 편이 안전합니다." % head)
        elif to_set <= 10:
            evening = True
            bits.append(
                "%s 해가 지는 시각에 맞춰 출발합니다. 몇 분 지나지 않아 어두워지니 "
                "헤드랜턴이나 반사 띠를 챙기고, 해가 지면 기온이 빠르게 떨어집니다."
                % head)
        elif to_set < 90:
            evening = True
            bits.append(
                "%s 해 지기 %d분 전에 출발합니다. 달리는 중에 어두워지니 "
                "반사 띠를 챙기고, 해가 지면 기온이 빠르게 떨어집니다."
                % (head, int(to_set)))
        elif gap < -30:
            evening = False
            bits.append(
                "%s 출발이 해 뜨기 %d분 전입니다. 처음 한동안은 어두운 채로 "
                "달리게 되니 헤드랜턴과 반사 띠를 챙기세요. 기온도 해 뜨기 직전이 "
                "가장 낮습니다." % (head, -gap))
        elif gap < 20:
            evening = False
            bits.append(
                "%s 해가 막 뜨는 시각에 출발합니다. 출발선에서는 아직 어둑하고 "
                "몇 km 지나며 밝아집니다." % head)
        elif gap < 120:
            evening = False
            bits.append(
                "%s 해가 뜨고 %d분 뒤에 출발합니다. 아침 기온이 아직 오르기 전이라 "
                "출발 전 겉옷을 어떻게 맡길지 정해 두는 편이 낫습니다." % (head, gap))
        else:
            evening = False
            h, m = divmod(gap, 60)
            when = "%d시간" % h + (" %d분" % m if m else "")
            bits.append(
                "%s 해가 뜨고 %s 지난 뒤 출발합니다. 해가 꽤 올라온 시간이라 "
                "모자와 선크림을 생각해 두세요." % (head, when))

        # 긴 거리는 제한시간 안에 해가 지는지가 실제로 갈린다
        km = _main_km(ev)
        if km and km >= 21.0 and not evening and 0 < to_set < 8 * 60:
            bits.append(
                "완주에 %d시간 %d분 넘게 걸리면 해가 지고 나서 들어오게 됩니다."
                % (int(to_set // 60), int(to_set % 60)))

    # 같은 날 전국 사정
    key = ev.get("date")
    others = [o for o in same_day.get(key, []) if o.get("id") != ev.get("id")]
    if others:
        near = [o for o in others if o.get("region") and o.get("region") == ev.get("region")]
        if len(near) >= 2:
            when_word = "교통" if evening else "아침 교통"
            bits.append(
                "같은 날 전국에서 %d개 대회가 더 열리고, 그중 %d개가 %s입니다. "
                "숙소와 %s이 겹칠 수 있습니다."
                % (len(others), len(near), esc(ev.get("region")), when_word))
        elif len(others) >= 5:
            bits.append("같은 날 전국에서 %d개 대회가 더 열립니다." % len(others))

    if not bits:
        return ""
    start_for_title = _start_minutes(ev)
    if start_for_title is not None and start_for_title > set_ - 90:
        title = "대회 날 저녁은 이렇습니다"
    elif start_for_title is not None and start_for_title >= 12 * 60:
        title = "대회 날 그 시간대는 이렇습니다"
    else:
        title = "대회 날 아침은 이렇습니다"
    return ('<h2 class="ev-h2">%s</h2>' % title
            + "".join('<p class="ev-p">%s</p>' % b for b in bits))

# ── 그날 보통 어떤 날씨였나 ──────────────────────────────────────────
#
# 대회마다 숫자가 아니라 '결론'이 달라지는 유일한 자료다. 기상청 종관기상관측
# 일자료로 대회 날 ±3일을 최근 10년 모아 접은 값이고, fetch_race_climate.py 가
# events.json 의 climate 칸에 넣어 둔다.
#
# 기온 기준은 사이트 다른 곳과 같은 걸 쓴다 — 마라톤 기록이 가장 잘 나오는
# 구간 3.8~9.9℃ (El Helou 외, PLoS ONE 2012;7(5):e37407). 여기서만 다른 숫자를
# 쓰면 같은 사이트에서 말이 엇갈린다.
OPT_LO, OPT_HI = 3.8, 9.9


# ── 기온 평년값 붙이기 ──────────────────────────────────────────
# events.json 에 실려 오기를 기다리지 않는다. update-events 가 events.json 을
# 새로 만들면 fetch_race_climate 가 붙여 둔 climate 가 통째로 날아가고,
# 그러면 822장에서 기온 문단만 조용히 사라진다. (실제로 707개 → 183개가 됐다)
# 캐시 파일 두 개만 있으면 여기서 다시 붙일 수 있으므로, 순서에 기대지 않는다.

_STATIONS_PATH = ROOT / "data" / "asos_stations.json"
_CLIMATE_PATH = ROOT / "data" / "race_climate.json"
_MAX_STATION_KM = 60      # fetch_race_climate.py 와 같은 값


def _haversine(lat1, lon1, lat2, lon2):
    import math
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = (math.sin(dp / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))


def attach_climate(events: list) -> int:
    """캐시에서 기온 평년값을 각 대회에 붙인다. 붙인 개수를 돌려준다."""
    if not (_STATIONS_PATH.exists() and _CLIMATE_PATH.exists()):
        return 0
    try:
        stations = json.loads(_STATIONS_PATH.read_text(encoding="utf-8"))
        cache = json.loads(_CLIMATE_PATH.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return 0
    if not stations or not cache:
        return 0

    filled = 0
    for ev in events:
        lat, lng, d = ev.get("lat"), ev.get("lng"), ev.get("date")
        if not (lat and lng and d):
            ev.pop("climate", None)
            continue
        day = parse_date(d)
        if not day:
            ev.pop("climate", None)
            continue
        # 가장 가까운 관측소에 그 날짜 자료가 없으면 포기하지 않고,
        # 자료가 있는 다음 관측소로 넘어간다. 캐시는 (관측소, 월일)별이라
        # 바로 옆 관측소라도 그 날짜만 비어 있는 일이 흔하다. 그 탓에
        # 11/15 대회 3건이 기온 문단 없이 나갔다. 거리는 페이지에 그대로
        # 밝히므로, 먼 관측소를 쓰면 쓴다고 독자가 알 수 있다.
        key = "%02d%02d" % (day.month, day.day)
        near = sorted(
            ((_haversine(float(lat), float(lng), st["lat"], st["lon"]), st)
             for st in stations), key=lambda t: t[0])
        picked = None
        for bd, st in near:
            if bd > _MAX_STATION_KM:
                break
            row = cache.get("%d:%s" % (st["id"], key))
            if row:
                picked = (row, st, bd)
                break
        if not picked:
            ev.pop("climate", None)
            continue
        row, st, bd = picked
        ev["climate"] = dict(row, station=st["name"], stationKm=round(bd),
                             approx=bool(ev.get("geoApprox")))
        filled += 1
    return filled


def build_climate(ev: dict) -> str:
    c = ev.get("climate") or {}
    need = ("years", "minAvg", "maxAvg", "station", "stationKm")
    if not all(k in c for k in need):
        return ""
    lo, hi, yrs = c["minAvg"], c["maxAvg"], c["years"]
    rain, station, km = c.get("rainYears", 0), esc(c["station"]), c["stationKm"]

    # 좌표를 장소명이 아니라 행정구역에서 얻은 대회가 있다. 그럴 때
    # '대회장에서 N km' 는 실제로 '시·군 중심에서 N km' 라서, 가진 것보다
    # 정확한 척하는 문장이 된다. 그런 경우에는 거리를 말하지 않는다.
    head = ("최근 %d년 이 대회 날 둘레의 기온은 아침 최저 평균 %.1f도, 낮 최고 평균 "
            "%.1f도였습니다. " % (yrs, lo, hi))
    if c.get("approx"):
        head += "%s 관측소 기준입니다." % station
    else:
        head += "%s 관측소 기준이고 대회장에서 %dkm 떨어져 있습니다." % (station, km)
    bits = [head]

    # 아침 기온이 최적 구간의 어디에 있느냐로 결론이 갈린다
    if lo > OPT_HI:
        over = lo - OPT_HI
        bits.append("기록이 가장 잘 나오는 %.1f~%.1f도 구간을 아침부터 %.1f도 "
                    "웃돌던 날씨입니다. 더위에 맞춰 페이스를 낮춰 잡고 물을 "
                    "자주 마시는 편이 안전합니다." % (OPT_LO, OPT_HI, over))
    elif hi < OPT_LO:
        bits.append("기록이 가장 잘 나오는 %.1f~%.1f도 구간보다 하루 종일 추웠던 "
                    "날씨입니다. 출발 전 체온을 지키는 것과 장갑·귀마개가 "
                    "기록보다 먼저입니다." % (OPT_LO, OPT_HI))
    elif lo >= OPT_LO and hi <= OPT_HI:
        bits.append("기록이 가장 잘 나오는 %.1f~%.1f도 구간에 하루가 통째로 "
                    "들어옵니다. 날씨만 보면 기록을 노려볼 만한 때입니다."
                    % (OPT_LO, OPT_HI))
    elif lo < OPT_LO and hi <= OPT_HI:
        bits.append("아침에는 %.1f~%.1f도 구간보다 춥고 낮이 되어야 그 안에 "
                    "들어옵니다. 출발할 때 입고 있다가 벗을 수 있는 옷차림이 "
                    "낫습니다." % (OPT_LO, OPT_HI))
    elif lo >= OPT_LO and hi > OPT_HI:
        bits.append("아침은 %.1f~%.1f도 구간 안이지만 낮에는 그 위로 올라갑니다. "
                    "뒤로 갈수록 더워지니 초반에 무리하지 않는 편이 낫습니다."
                    % (OPT_LO, OPT_HI))
    else:
        # 아침은 구간보다 춥고 낮에는 구간 위로 올라간다 — 일교차가 큰 날이다
        bits.append("아침은 %.1f~%.1f도 구간보다 춥고 낮에는 그 위로 올라갑니다. "
                    "하루 사이 %.1f도가 움직이니, 출발 전 겉옷을 어디에 맡길지 "
                    "미리 정해 두는 편이 낫습니다."
                    % (OPT_LO, OPT_HI, hi - lo))

    tail = []
    if rain >= 3:
        tail.append("%d년 중 %d번은 이 날 비가 왔습니다" % (yrs, rain))
    elif rain == 0:
        tail.append("최근 %d년 동안 이 날 비가 온 해는 없었습니다" % yrs)
    hy, hm = c.get("hottestYear"), c.get("hottestMax")
    if hy and hm and hm - hi >= 3.0:
        tail.append("가장 더웠던 %d년에는 %.1f도까지 올랐습니다" % (hy, hm))
    if tail:
        bits.append(" · ".join(tail) + ".")

    return ('<h2 class="ev-h2">이 날은 보통 어떤 날씨였나</h2>'
            + "".join('<p class="ev-p">%s</p>' % b for b in bits)
            + '<p class="ev-src">기상청 종관기상관측(ASOS) 일자료 · '
              '기온 기준은 El Helou 외, <i>PLoS ONE</i> 2012;7(5):e37407</p>')

def build_related_links(ev: dict) -> str:
    links = []
    sport = ev.get("sport")
    region = ev.get("region")
    slug = REGION_SLUG.get(region)
    if slug and sport in SPORT_LABEL:
        fname = f"landing-{slug}-{sport}.html"
        if (ROOT / fname).exists():
            links.append(f'<a href="{fname}">{esc(region)} {esc(SPORT_LABEL[sport])} 대회 전체 일정</a>')
    if sport in SPORT_LABEL:
        links.append(f'<a href="index.html?sport={esc(sport)}">{esc(SPORT_LABEL[sport])} 대회 캘린더</a>')
    links.append('<a href="column.html">러닝·사이클 칼럼</a>')
    return " · ".join(links)


# ──────────────────────────────────────────────────────────────
# 대회마다 다른 내용. 상세 페이지 857개의 본문이 평균 860자인데 대부분이
# 모든 페이지에 똑같이 들어가는 머리말·꼬리말이었다. 고유한 문장은 두세 개뿐.
# 구글이 "발견됨 - 현재 색인이 생성되지 않음" 으로 묶은 이유다.
# 아래 세 블록은 events.json 에 실제로 있는 값만 써서 만든다. 지어내지 않는다.
# ──────────────────────────────────────────────────────────────

_PACE_MIN = [4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0]   # km당 분


def _hms(total_sec: int) -> str:
    h, rem = divmod(int(round(total_sec)), 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def build_pace_table(ev: dict) -> str:
    """페이스·등급 표는 거리별 전용 페이지에 한 장만 둔다.

    km당 페이스 → 완주 시간은 거리만 정해지면 내용이 완전히 같아지는 표다.
    822장에 같은 표를 복제하면 검색엔진에는 822장이 한 장으로 보이고,
    방문자에게도 자기 기록을 넣어 볼 곳이 없다. 그래서 여기서는
    이 대회 거리로 미리 맞춰 둔 계산기로 보낸다.
    """
    kms = _parse_km(ev.get("distances"))
    if not kms:
        return ""
    km = kms[-1]
    label = _km_label(km)
    return (
        f'<p class="ev-p ev-tool">목표 시간을 정하는 중이라면 '
        f'<a href="/level.html?d={km:g}">{esc(label)} 페이스·등급 계산기</a>에서 '
        f"이 대회 거리로 바로 맞춰 볼 수 있습니다. "
        f"기록을 넣으면 km당 페이스와 등급이 같이 나옵니다.</p>"
    )


def _norm_name(name: str) -> str:
    s = re.sub(r"^\s*20\d{2}\s*년?\s*", "", str(name or ""))
    s = re.sub(r"제?\s*\d+\s*회", "", s)
    s = re.sub(r"\s*20\d{2}\s*$", "", s)
    return re.sub(r"[^0-9A-Za-z가-힣]", "", s).lower()


def _ev_link(ev: dict) -> str:
    d = parse_date(ev.get("date"))
    when = f"{d.year}.{d.month:02d}.{d.day:02d}" if d else ""
    # 장소가 지역명과 같을 때가 있다 ("경기 · 경기"). 같은 값은 한 번만 쓴다.
    bits = []
    for b in (ev.get("region"), ev.get("location")):
        b = (b or "").strip()
        if b and b != "미정" and b not in bits:
            bits.append(b)
    return (f'<li><a href="e/{esc(quote(str(ev["id"])))}.html">'
            f'<b>{esc(ev.get("name") or "대회")}</b></a> '
            f'<span>{esc(when)}{" · " + esc(bits[0]) if bits else ""}</span></li>')


def build_nearby(ev: dict, ctx: dict) -> str:
    """같은 종목·같은 지역에서 비슷한 시기에 열리는 다른 대회."""
    d = parse_date(ev.get("date"))
    if not d:
        return ""
    sport, region = ev.get("sport"), ev.get("region")
    pool = [o for o in ctx["by_sport"].get(sport, [])
            if o.get("id") != ev.get("id") and parse_date(o.get("date"))]
    near = [o for o in pool
            if o.get("region") == region
            and abs((parse_date(o["date"]) - d).days) <= 45]
    scope = f"{region} " if region and region != "전국" else ""
    if len(near) < 3:                      # 지역에 몇 개 없으면 전국에서 가까운 날짜로
        near = [o for o in pool if abs((parse_date(o["date"]) - d).days) <= 14]
        scope = ""
    if not near:
        return ""
    near.sort(key=lambda o: abs((parse_date(o["date"]) - d).days))
    picked = sorted(near[:6], key=lambda o: o["date"])
    label = SPORT_LABEL.get(sport, "대회")
    return (f'<h2 class="ev-h2">비슷한 시기에 열리는 {esc(scope)}{esc(label)} 대회</h2>'
            f'<ul class="ev-list">{"".join(_ev_link(o) for o in picked)}</ul>')


def build_other_editions(ev: dict, ctx: dict) -> str:
    """같은 대회의 다른 회차. '○○마라톤 기록' 은 대회가 끝난 뒤에 검색된다."""
    key = _norm_name(ev.get("name"))
    if not key:
        return ""
    others = [o for o in ctx["by_norm"].get(key, [])
              if o.get("id") != ev.get("id") and parse_date(o.get("date"))]
    if not others:
        return ""
    others.sort(key=lambda o: o["date"], reverse=True)
    return ('<h2 class="ev-h2">같은 대회의 다른 회차</h2>'
            f'<ul class="ev-list">{"".join(_ev_link(o) for o in others[:4])}</ul>')


EXTRA_CSS = """
<style>
  .ev-extra{margin-top:40px;}
  .ev-h2{font-size:17px;margin:32px 0 10px;}
  .ev-p{font-size:14px;line-height:1.8;color:var(--ink-soft);margin:0 0 12px;}
  .ev-src{font-size:12px;line-height:1.7;color:var(--ink-faint);margin:6px 0 0;}
  .ev-pace{width:100%;max-width:420px;border-collapse:collapse;font-size:14px;}
  .ev-pace th,.ev-pace td{padding:8px 10px;text-align:left;
    border-bottom:1px solid rgba(255,255,255,.08);}
  .ev-pace th{color:#fff;background:rgba(255,255,255,.03);}
  .ev-pace td:first-child{color:var(--ink-soft);}
  .ev-list{list-style:none;margin:0;padding:0;}
  .ev-list li{padding:9px 0;border-bottom:1px solid rgba(255,255,255,.06);
    font-size:14px;line-height:1.6;}
  .ev-list a{color:inherit;text-decoration:none;}
  .ev-list a:hover b{text-decoration:underline;}
  .ev-list span{display:block;color:var(--ink-faint);font-size:12px;margin-top:2px;}
</style>"""


def render_page(template: str, ev: dict, ctx: dict) -> str:
    url = page_url_for(ev["id"])
    title = build_title(ev)
    desc = build_meta_description(ev)
    summary = build_summary(ev)

    out = template
    out = out.replace("<meta charset=\"UTF-8\">", '<meta charset="UTF-8">\n<base href="/">', 1)

    def sub_tag(pattern, repl):
        nonlocal out
        out, n = re.subn(pattern, lambda m: repl, out, count=1)
        if n != 1:
            raise RuntimeError(f"템플릿에서 {pattern} 를 찾지 못했습니다")

    sub_tag(r'<title id="pageTitleTag">.*?</title>', f'<title id="pageTitleTag">{esc(title)}</title>')
    sub_tag(r'<meta id="metaDesc" name="description" content=".*?">', f'<meta id="metaDesc" name="description" content="{esc(desc)}">')
    sub_tag(r'<meta id="ogType" property="og:type" content=".*?">', '<meta id="ogType" property="og:type" content="article">')
    sub_tag(r'<meta id="ogTitle" property="og:title" content=".*?">', f'<meta id="ogTitle" property="og:title" content="{esc(title)}">')
    sub_tag(r'<meta id="ogDesc" property="og:description" content=".*?">', f'<meta id="ogDesc" property="og:description" content="{esc(desc)}">')
    sub_tag(r'<meta id="ogUrl" property="og:url" content=".*?">', f'<meta id="ogUrl" property="og:url" content="{esc(url)}">')
    sub_tag(r'<meta id="twTitle" name="twitter:title" content=".*?">', f'<meta id="twTitle" name="twitter:title" content="{esc(title)}">')
    sub_tag(r'<meta id="twDesc" name="twitter:description" content=".*?">', f'<meta id="twDesc" name="twitter:description" content="{esc(desc)}">')

    head_extra = "\n".join([
        f'<link rel="canonical" href="{esc(url)}">',
        EXTRA_CSS,
        ld_script("eventLd", build_event_jsonld(ev, url, desc)),
        ld_script("breadcrumbLd", build_breadcrumb_jsonld(ev)),
    ])
    out = out.replace("</head>", head_extra + "\n</head>", 1)

    boot = (
        "<script>"
        f"window.EVENT_ID={json.dumps(ev['id'], ensure_ascii=False)};"
        f"window.EVENT_STATIC_URL={json.dumps(url)};"
        f"window.EVENT_STATIC_TITLE={json.dumps(title, ensure_ascii=False)};"
        f"window.EVENT_STATIC_DESC={json.dumps(desc, ensure_ascii=False)};"
        "</script>"
    )
    out = out.replace("<body>", "<body>\n" + boot, 1)

    placeholder = '<p class="result-count">불러오는 중…</p>'
    if placeholder not in out:
        raise RuntimeError("템플릿에서 로딩 문구 자리를 찾지 못했습니다")
    out = out.replace(placeholder, build_static_content(ev), 1)

    standards = build_record_standards(ev)
    standards_html = (
        f'<p style="margin-top:10px;">{standards}</p>' if standards else ""
    )
    summary_block = (
        '<section id="eventSummary" style="margin-top:20px;line-height:1.8;color:var(--ink-soft);font-size:14px;">'
        f"<p>{esc(summary)}</p>"
        f"{standards_html}"
        f'<p style="margin-top:8px;font-size:13px;">{build_related_links(ev)}</p>'
        "</section>\n"
    )
    marker = '<div id="saveWidget"'
    if marker not in out:
        raise RuntimeError("템플릿에서 saveWidget 자리를 찾지 못했습니다")
    out = out.replace(marker, summary_block + marker, 1)

    extra = "".join(filter(None, [
        build_climate(ev),
        build_day_context(ev, ctx.get("by_date", {})),
        build_pace_table(ev),
        build_other_editions(ev, ctx),
        build_nearby(ev, ctx),
    ]))
    if extra:
        tail = '<footer class="site-footer"'
        if tail not in out:
            raise RuntimeError("템플릿에서 꼬리말 자리를 찾지 못했습니다")
        out = out.replace(tail, f'<section class="ev-extra">{extra}</section>\n' + tail, 1)
    return out


INDEX_PATH = ROOT / "events-index.html"
SPORT_ORDER = ["marathon", "trail", "cycling", "triathlon", "inline"]


def write_event_index(wanted: dict) -> None:
    """대회 상세 페이지 전체를 평범한 <a href> 로 엮은 목록 페이지를 만든다.

    이 페이지가 없는 동안 e/<id>.html 은 사이트맵에만 존재하는 외톨이였다.
    홈 화면의 대회 목록은 자바스크립트가 그리고, 그마저도 링크가 아니라
    클릭 이벤트였다. 검색엔진은 주소를 "발견"만 하고 크롤링하지 않았다
    (구글 색인 보고서: 발견됨 - 현재 색인이 생성되지 않음 493개).

    그래서 이 목록은 자바스크립트 없이 그대로 읽히도록 서버에서 미리 만든다.
    """
    today = date.today()
    by_month: dict[str, list[dict]] = {}
    for fname, ev in wanted.items():
        d = parse_date(ev.get("date"))
        if not d or d < today:
            continue  # 지난 대회는 사이트맵에만 남긴다
        by_month.setdefault(f"{d.year}-{d.month:02d}", []).append(ev)

    total = sum(len(v) for v in by_month.values())
    sections = []
    for key in sorted(by_month):
        year, month = key.split("-")
        rows = sorted(by_month[key], key=lambda e: (e.get("date") or "", e.get("name") or ""))
        items = []
        for ev in rows:
            d = parse_date(ev["date"])
            # 장소가 지역명과 같을 때가 있다 ("경기 · 경기"). 같은 값은 한 번만 쓴다.
            bits = []
            for b in (ev.get("region"), ev.get("location")):
                b = (b or "").strip()
                if b and b != "미정" and b not in bits:
                    bits.append(b)
            dist = " · ".join(dedupe_distances(ev.get("distances"))[:4])
            if dist:
                bits.append(dist)
            items.append(
                f'<li><a href="e/{esc(quote(str(ev["id"])))}.html">'
                f'<b>{esc(ev.get("name") or "대회")}</b></a> '
                f'<span>{d.month}월 {d.day}일'
                + (f' · {esc(" · ".join(bits))}' if bits else "")
                + "</span></li>"
            )
        sections.append(
            f'<section class="ei-month">\n'
            f'<h2>{year}년 {int(month)}월 대회 일정 ({len(rows)}개)</h2>\n'
            f'<ul class="ei-list">\n' + "\n".join(items) + "\n</ul>\n</section>"
        )

    desc = (f"국내 마라톤·트레일러닝·자전거·철인3종·인라인 대회 {total}개의 "
            "일정을 월별로 모은 전체 목록입니다. 대회마다 코스 거리, 접수 "
            "마감일, 신청 링크를 확인할 수 있습니다.")
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>전국 마라톤 대회 일정 전체 목록 | 월별 대회 {total}개 - calrank</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{SITE}/events-index.html">
<meta property="og:title" content="전국 마라톤 대회 일정 전체 목록 - calrank">
<meta property="og:description" content="{esc(desc)}">
<link rel="stylesheet" href="style.css">
<style>
  .ei-wrap{{max-width:860px;margin:0 auto;padding:32px 18px 80px;}}
  .ei-lead{{font-size:13.5px;line-height:1.85;color:var(--ink-soft);margin:0 0 28px;}}
  .ei-month{{margin:0 0 34px;}}
  .ei-month h2{{font-size:16px;margin:0 0 12px;padding-bottom:8px;
    border-bottom:1px solid var(--line,#222);}}
  .ei-list{{list-style:none;margin:0;padding:0;}}
  .ei-list li{{padding:9px 0;border-bottom:1px solid rgba(255,255,255,.06);
    font-size:13.5px;line-height:1.6;}}
  .ei-list a{{color:inherit;text-decoration:none;}}
  .ei-list a:hover b{{text-decoration:underline;}}
  .ei-list span{{display:block;color:var(--ink-faint);font-size:12px;margin-top:2px;}}
</style>
</head>
<body>
<header class="site-header">
<div class="wrap header-inner">
<a href="index.html" class="wordmark">CALRANK</a>
<nav class="main-nav">
<a href="index.html" class="nav-link">캘린더</a>
<a href="ranking.html" class="nav-link">대회랭킹</a>
<a href="news.html" class="nav-link">종목뉴스</a>
<a href="column.html" class="nav-link">칼럼</a>
<a href="grade.html" class="nav-link">등급표</a>
</nav>
</div>
</header>

<main class="ei-wrap">
<h1>전국 마라톤 대회 일정 전체 목록</h1>
<p class="ei-lead">{esc(desc)} 월별로 묶어 두었고, 대회 이름을 누르면
상세 페이지로 갑니다. 종목·지역·거리로 걸러 보려면
<a href="index.html">대회 캘린더</a>를 쓰세요.</p>
{"".join(chr(10) + s for s in sections)}
</main>

<footer class="site-footer">
<div class="wrap">
<p class="footer-links"><a href="terms.html">이용약관</a> · <a href="privacy.html">개인정보처리방침</a> · <a href="contact.html">제휴·광고 문의</a></p>
</div>
</footer>
</body>
</html>
"""
    if not INDEX_PATH.exists() or INDEX_PATH.read_text(encoding="utf-8") != html:
        INDEX_PATH.write_text(html, encoding="utf-8")
    print(f"[events-index] 예정 대회 {total}개를 {len(by_month)}개 달로 묶어 링크")


# ── 지난 대회 보관소 ──────────────────────────────────────────
ARCHIVE_PATH = ROOT / "events-archive.html"

# 이만큼 열린 달만 따로 페이지를 준다. 더 적은 달은 목차에 그대로 펼친다.
# 대회 두세 개짜리 페이지를 만들어 봐야 읽을 것도, 검색될 것도 없다.
ARCHIVE_MONTH_MIN = 20

ARCHIVE_CSS = """
  .ei-wrap{max-width:860px;margin:0 auto;padding:32px 18px 80px;}
  .ei-lead{font-size:13.5px;line-height:1.85;color:var(--ink-soft);margin:0 0 28px;}
  .ei-lead a{color:var(--accent,#FF3D1A);text-decoration:none;border-bottom:1px solid rgba(255,61,26,.4);}
  .ei-lead a:hover{border-bottom-color:var(--accent,#FF3D1A);}
  .ei-month{margin:0 0 34px;}
  .ei-month h2{font-size:16px;margin:0 0 12px;padding-bottom:8px;
    border-bottom:1px solid var(--line,#222);}
  .ei-list{list-style:none;margin:0;padding:0;}
  .ei-list li{padding:9px 0;border-bottom:1px solid rgba(255,255,255,.06);
    font-size:13.5px;line-height:1.6;}
  .ei-list a{color:inherit;text-decoration:none;}
  .ei-list a:hover b{text-decoration:underline;}
  .ei-list span{display:block;color:var(--ink-faint);font-size:12px;margin-top:2px;}
  .ar-months{list-style:none;margin:0 0 34px;padding:0;
    display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px;}
  .ar-months li{border:1px solid var(--line,#222);border-radius:10px;padding:14px 16px;}
  .ar-months a{color:inherit;text-decoration:none;display:block;}
  .ar-months a:hover strong{text-decoration:underline;}
  .ar-months strong{display:block;font-size:14.5px;margin-bottom:4px;}
  .ar-months em{font-style:normal;color:var(--ink-faint);font-size:12px;line-height:1.6;}
  .ar-pager{display:flex;justify-content:space-between;gap:12px;margin:34px 0 0;
    padding-top:18px;border-top:1px solid var(--line,#222);font-size:13px;}
  .ar-pager a{color:var(--ink-soft);text-decoration:none;}
  .ar-pager a:hover{text-decoration:underline;}
"""


def dedupe_distances(values) -> list[str]:
    """거리 목록을 손질한다.

    원본에 ['10km', '5km', '10km · 5km'] 처럼 낱개와 합친 문자열이 섞여 들어와
    화면에 "10km · 5km · 10km · 5km" 로 찍혔다. 합친 것은 쪼개고 중복만 뺀다.
    """
    out, seen = [], set()
    for v in (values or []):
        for part in re.split(r"[·,/]|\s+및\s+", str(v)):
            part = part.strip()
            if part and part not in seen:
                seen.add(part)
                out.append(part)
    return out


def archive_slug(key: str) -> str:
    return f"events-archive-{key}.html"


def month_label(key: str) -> str:
    year, month = key.split("-")
    return f"{year}년 {int(month)}월"


def archive_month_mix(rows: list[dict]) -> str:
    """그 달의 지역·거리 분포를 한 문장으로. 대회 이름은 쓰지 않는다."""
    regions: dict[str, int] = {}
    dists: dict[str, int] = {}
    for ev in rows:
        r = (ev.get("region") or "").strip()
        if r and r != "전국":
            regions[r] = regions.get(r, 0) + 1
        for d in (ev.get("distances") or []):
            d = str(d).strip()
            if d:
                dists[d] = dists.get(d, 0) + 1
    bits = []
    top_r = sorted(regions.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    if top_r:
        bits.append(" · ".join(f"{k} {n}개" for k, n in top_r))
    top_d = sorted(dists.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    if top_d:
        bits.append("거리는 " + "·".join(k for k, _ in top_d) + " 중심")
    return ", ".join(bits)


def archive_items(rows: list[dict]) -> str:
    out = []
    for ev in sorted(rows, key=lambda e: (e.get("date") or ""), reverse=True):
        d = parse_date(ev["date"])
        # 장소가 지역명과 같을 때가 있다 ("경기 · 경기"). 같은 값은 한 번만 쓴다.
        bits = []
        for b in (ev.get("region"), ev.get("location")):
            b = (b or "").strip()
            if b and b != "미정" and b not in bits:
                bits.append(b)
        dist = " · ".join(dedupe_distances(ev.get("distances"))[:4])
        if dist:
            bits.append(dist)
        out.append(
            f'<li><a href="e/{esc(quote(str(ev["id"])))}.html">'
            f'<b>{esc(ev.get("name") or "대회")}</b></a> '
            f'<span>{d.month}월 {d.day}일'
            + (f' · {esc(" · ".join(bits))}' if bits else "")
            + "</span></li>"
        )
    return "\n".join(out)


def archive_shell(title: str, desc: str, canonical: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{SITE}/{canonical}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<link rel="stylesheet" href="style.css">
<style>{ARCHIVE_CSS}</style>
</head>
<body>
{site_header("calendar")}

<main class="ei-wrap">
{body}
</main>

<footer class="site-footer">
<div class="wrap">
<p class="footer-links"><a href="events-index.html">전국 대회 일정 전체 목록</a> ·
<a href="events-archive.html">지난 대회 기록</a> ·
<a href="terms.html">이용약관</a> · <a href="privacy.html">개인정보처리방침</a> ·
<a href="contact.html">제휴·광고 문의</a></p>
</div>
</footer>
</body>
</html>
"""


def build_archive_month(key, rows, prev_key, next_key) -> str:
    label = month_label(key)
    mix = archive_month_mix(rows)
    desc = (f"{label}에 열린 국내 마라톤·트레일러닝·자전거·철인3종 대회 "
            f"{len(rows)}개 목록입니다." + (f" {mix}." if mix else "")
            + " 대회별 코스 거리, 장소, 개최일을 확인할 수 있습니다.")
    pager = []
    if next_key:
        pager.append(f'<a href="{archive_slug(next_key)}">← {month_label(next_key)}</a>')
    else:
        pager.append("<span></span>")
    if prev_key:
        pager.append(f'<a href="{archive_slug(prev_key)}">{month_label(prev_key)} →</a>')
    else:
        pager.append("<span></span>")
    body = (
        f"<h1>{label}에 열린 마라톤 대회</h1>\n"
        f'<p class="ei-lead">{esc(desc)} 앞으로 열릴 대회는 '
        '<a href="events-index.html">전국 대회 일정 전체 목록</a>, '
        '달별 전체 목록은 <a href="events-archive.html">지난 대회 기록 보관소</a>에 있습니다.</p>\n'
        f'<section class="ei-month">\n<ul class="ei-list">\n{archive_items(rows)}\n</ul>\n</section>\n'
        f'<nav class="ar-pager">{"".join(pager)}</nav>'
    )
    title = f"{label} 마라톤 대회 {len(rows)}개 — 지난 대회 기록 | calrank"
    return archive_shell(title, desc, archive_slug(key), body)


def build_archive_hub(by_month, keys, own_page, total) -> str:
    desc = (f"이미 열린 국내 마라톤·트레일러닝·자전거·철인3종 대회 {total}개를 "
            f"{len(keys)}개 달로 나눠 모은 기록 보관소입니다. "
            "대회별 코스 거리, 장소, 개최일을 확인할 수 있습니다.")
    cards, inline = [], []
    for key in keys:
        rows = by_month[key]
        mix = archive_month_mix(rows)
        if key in own_page:
            cards.append(
                f'<li><a href="{archive_slug(key)}">'
                f"<strong>{month_label(key)} · {len(rows)}개</strong>"
                + (f"<em>{esc(mix)}</em>" if mix else "")
                + "</a></li>"
            )
        else:
            inline.append(
                f'<section class="ei-month">\n'
                f"<h2>{month_label(key)}에 열린 대회 ({len(rows)}개)</h2>\n"
                f'<ul class="ei-list">\n{archive_items(rows)}\n</ul>\n</section>'
            )
    body = (
        "<h1>지난 마라톤 대회 기록 보관소</h1>\n"
        f'<p class="ei-lead">{esc(desc)} 앞으로 열릴 대회를 찾으신다면 '
        '<a href="events-index.html">전국 대회 일정 전체 목록</a>을 보세요. '
        '종목별 완주 기록 순위는 <a href="ranking.html">대회랭킹</a>에 있습니다.</p>\n'
        + (f'<ul class="ar-months">\n{chr(10).join(cards)}\n</ul>\n' if cards else "")
        + ("".join(chr(10) + s for s in inline))
    )
    title = f"지난 마라톤 대회 기록 {total}개 | 월별 대회 결과 보관소 - calrank"
    return archive_shell(title, desc, "events-archive.html", body)


def update_sitemap(slugs) -> int:
    path = ROOT / "sitemap.xml"
    if not path.exists():
        return 0
    xml = path.read_text(encoding="utf-8")
    marker = "</urlset>"
    added, count = "", 0
    for slug in slugs:
        loc = f"{SITE}/{slug}"
        if f"<loc>{loc}</loc>" in xml:
            continue
        added += ("  <url>\n"
                  f"    <loc>{loc}</loc>\n"
                  "    <changefreq>monthly</changefreq>\n"
                  "    <priority>0.5</priority>\n"
                  "  </url>\n")
        count += 1
    if added and marker in xml:
        path.write_text(xml.replace(marker, added + marker), encoding="utf-8")
    return count



# ── 사이트맵의 lastmod ───────────────────────────────────────────────
#
# 822개 URL 에 lastmod 가 하나도 없었다. 크롤러에게 "이 페이지가 언제 바뀌었다"를
# 알려 주는 유일한 신호인데 비어 있고, 대신 들어간 changefreq·priority 는 구글이
# 공식적으로 무시한다. 재크롤 우선순위가 낮을 수밖에 없다.
#
# CI 는 체크아웃마다 파일 시각을 새로 찍으므로 mtime 은 쓸 수 없다. 내용이 실제로
# 바뀐 날만 대장에 적어 두고 그 값을 사이트맵에 넣는다.
LASTMOD = ROOT / "data" / "event_lastmod.json"


def load_lastmod() -> dict:
    try:
        return json.loads(LASTMOD.read_text(encoding="utf-8"))
    except Exception:                               # noqa: BLE001
        return {}


def save_lastmod(book: dict) -> None:
    LASTMOD.parent.mkdir(exist_ok=True)
    LASTMOD.write_text(json.dumps(book, ensure_ascii=False, sort_keys=True,
                                  indent=0) + "\n", encoding="utf-8")


def patch_sitemap_lastmod(book: dict) -> int:
    """sitemap-events.xml 의 각 <url> 에 lastmod 를 넣거나 고친다."""
    path = ROOT / "sitemap-events.xml"
    if not path.exists():
        return 0
    xml = path.read_text(encoding="utf-8")
    touched = 0

    def fix(m):
        nonlocal touched
        block = m.group(0)
        loc = re.search(r"<loc>([^<]+)</loc>", block)
        if not loc:
            return block
        name = unquote(loc.group(1).rsplit("/", 1)[-1])
        when = book.get(name)
        if not when:
            return block
        block = re.sub(r"\s*<lastmod>[^<]*</lastmod>", "", block)
        block = block.replace("</loc>", "</loc>\n    <lastmod>%s</lastmod>" % when, 1)
        touched += 1
        return block

    new = re.sub(r"<url>.*?</url>", fix, xml, flags=re.S)
    if new != xml:
        path.write_text(new, encoding="utf-8")
    return touched


def write_event_archive(wanted: dict) -> None:
    """이미 열린 대회의 상세 페이지를 월별로 엮은 아카이브.

    events-index.html 은 예정 대회만 담는다. 지난 대회 페이지는 3년간
    남겨 두는데, 그쪽도 링크가 없으면 똑같이 외톨이가 된다.
    "○○마라톤 기록", "2026 ○○마라톤 결과" 는 대회가 끝난 뒤에 검색되므로
    페이지를 남겨 둔 의미가 있으려면 닿을 수 있어야 한다.

    한 장에 555개를 전부 담았더니 151KB가 됐다. 방문자의 3분의 2가
    휴대폰이라 그 무게를 그대로 내려받게 하는 건 낭비다. 달이 쌓일수록
    더 나빠지기만 한다. 그래서 큰 달은 각자 페이지로 떼고, 남는 자리에는
    달마다 지역·거리 분포를 적어 목차 자체가 읽을거리가 되게 한다.
    """
    today = date.today()
    by_month: dict[str, list[dict]] = {}
    for fname, ev in wanted.items():
        d = parse_date(ev.get("date"))
        if not d or d >= today:
            continue
        by_month.setdefault(f"{d.year}-{d.month:02d}", []).append(ev)

    total = sum(len(v) for v in by_month.values())
    if not total:
        if ARCHIVE_PATH.exists():
            ARCHIVE_PATH.unlink()
        for old in ROOT.glob("events-archive-20*.html"):
            old.unlink()
        print("[events-archive] 지난 대회 없음")
        return

    keys = sorted(by_month, reverse=True)           # 최근 달이 위로
    own_page = [k for k in keys if len(by_month[k]) >= ARCHIVE_MONTH_MIN]

    written: list[str] = []
    for i, key in enumerate(own_page):
        prev_key = own_page[i + 1] if i + 1 < len(own_page) else None   # 더 과거
        next_key = own_page[i - 1] if i > 0 else None                   # 더 최근
        slug = archive_slug(key)
        html = build_archive_month(key, by_month[key], prev_key, next_key)
        path = ROOT / slug
        if not path.exists() or path.read_text(encoding="utf-8") != html:
            path.write_text(html, encoding="utf-8")
        written.append(slug)

    # 기준에 못 미치게 된 달의 페이지는 남겨 두면 외톨이가 된다.
    for old in ROOT.glob("events-archive-20*.html"):
        if old.name not in written:
            old.unlink()
            print(f"[events-archive] {old.name} 삭제 (대회 수가 기준 미만)")

    hub = build_archive_hub(by_month, keys, own_page, total)
    if not ARCHIVE_PATH.exists() or ARCHIVE_PATH.read_text(encoding="utf-8") != hub:
        ARCHIVE_PATH.write_text(hub, encoding="utf-8")

    added = update_sitemap(["events-archive.html"] + written)
    print(f"[events-archive] 지난 대회 {total}개 · 달 {len(keys)}개 "
          f"(단독 페이지 {len(written)}개) · sitemap 추가 {added}개")


def main():
    events = json.loads((ROOT / "events.json").read_text(encoding="utf-8"))
    n_clim = attach_climate(events)
    print("[event pages] 기온 평년값 %d개 붙임" % n_clim)
    template = (ROOT / "event.html").read_text(encoding="utf-8")
    cutoff = date.today() - timedelta(days=KEEP_DAYS_AFTER)

    OUT_DIR.mkdir(exist_ok=True)
    wanted = {}
    for ev in events:
        d = parse_date(ev.get("date"))
        if not ev.get("id") or not d or d < cutoff:
            continue
        wanted[f"{ev['id']}.html"] = ev

    # 관련 대회를 찾으려면 전체 목록이 필요하다. 한 번만 만들어 돌려 쓴다.
    ctx = {"by_sport": {}, "by_norm": {}, "by_date": {}}
    for e in wanted.values():
        ctx["by_sport"].setdefault(e.get("sport"), []).append(e)
        key = _norm_name(e.get("name"))
        if key:
            ctx["by_norm"].setdefault(key, []).append(e)
        if e.get("date"):
            ctx["by_date"].setdefault(e["date"], []).append(e)

    book = load_lastmod()
    _today_iso = date.today().isoformat()
    written = 0
    for fname, ev in wanted.items():
        content = render_page(template, ev, ctx)
        p = OUT_DIR / fname
        if not p.exists() or p.read_text(encoding="utf-8") != content:
            p.write_text(content, encoding="utf-8")
            book[fname] = _today_iso
            written += 1
        else:
            # 대장에 없는 장은 처음 한 번만 오늘로 채운다. 이 스크립트가
            # 내용이 같으면 파일을 건드리지 않으므로, 이후로는 실제로 바뀐
            # 날만 찍힌다. 없는 날짜를 지어내지 않으려는 것이다.
            book.setdefault(fname, _today_iso)

    removed = 0
    for p in OUT_DIR.glob("*.html"):
        if p.name not in wanted:
            p.unlink()
            removed += 1
    print(f"[event pages] 대상 {len(wanted)}개, 갱신 {written}개, 정리 {removed}개")

    # 지금 돌면서 내용이 바뀐 장만 대장에 날짜가 찍혔다. 그 값을 사이트맵에 넣는다.
    save_lastmod(book)
    n_lm = patch_sitemap_lastmod(book)
    print("[sitemap-events.xml] lastmod %d개 반영 (대장 %d칸)" % (n_lm, len(book)))

    write_event_index(wanted)
    write_event_archive(wanted)


if __name__ == "__main__":
    main()
