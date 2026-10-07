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
from pathlib import Path
from urllib.parse import quote

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

    dist = [x for x in (ev.get("distances") or []) if x]
    if dist:
        parts.append(f"종목은 {', '.join(dist)}입니다.")

    org = (ev.get("organizer") or "").strip()
    if org:
        parts.append(f"주최는 {org}입니다.")

    rd = parse_date(ev.get("regDeadline"))
    if is_past:
        parts.append("이미 종료된 대회입니다. 다음 회차 일정은 주최 측 공지를 확인해 주세요.")
        return " ".join(parts)
    if ev.get("regClosed"):
        parts.append("접수는 이미 마감되었습니다.")
    elif rd:
        parts.append(f"접수 마감일은 {date_ko(rd)}입니다.")
    else:
        parts.append("접수 기간은 주최 측 공지에서 확인해 주세요.")
    return " ".join(parts)


# --- 기록 수준 한 단락 (level.js / 등급표와 같은 모델) ---
_AGE_ANCHORS = [(20, 0.90), (30, 0.93), (40, 0.96), (50, 1.00),
                (60, 1.10), (70, 1.25), (80, 1.45)]
_GENDER_FACTOR = {"male": 1.00, "female": 1.11}
_RIEGEL = 1.06
_GRADE_SLUG = {5.0: "5km", 10.0: "10km", 21.0975: "half", 42.195: "full"}
_NAMED_DIST = {"하프": 21.0975, "풀코스": 42.195, "풀": 42.195}


def _age_factor(age):
    if age <= 20:
        return 0.90
    if age >= 80:
        return 1.45
    for i in range(len(_AGE_ANCHORS) - 1):
        a0, f0 = _AGE_ANCHORS[i]
        a1, f1 = _AGE_ANCHORS[i + 1]
        if a0 <= age <= a1:
            return f0 + (f1 - f0) * (age - a0) / (a1 - a0)
    return 1.0


def _norm_pace(sec, age, gender, km):
    return (sec * (10.0 / km) ** _RIEGEL) / 10.0 / _age_factor(age) / _GENDER_FACTOR[gender]


def _boundary(bound, age, gender, km):
    s = math.floor(bound * _age_factor(age) * _GENDER_FACTOR[gender] * 10.0 * (km / 10.0) ** _RIEGEL)
    while s > 0 and _norm_pace(s, age, gender, km) > bound:
        s -= 1
    while _norm_pace(s + 1, age, gender, km) <= bound:
        s += 1
    return int(s)


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
        main = kms[0]

    lab = _km_label(main)
    m_avg = _fmt_time(_boundary(390, 40, "male", main))
    m_good = _fmt_time(_boundary(300, 40, "male", main))
    f_avg = _fmt_time(_boundary(390, 40, "female", main))
    f_good = _fmt_time(_boundary(300, 40, "female", main))

    slug = _GRADE_SLUG.get(main)
    link = ""
    if slug:
        link = (f' 20대부터 75세까지 나이별 전체 기준은 '
                f'<a href="/grade-{slug}-male.html">{lab} 남성 등급표</a>와 '
                f'<a href="/grade-{slug}-female.html">여성 등급표</a>에 있습니다.')

    return (
        f"이 대회 {lab}를 기준으로 보면, 40대 남성은 {m_avg} 안에 들어오면 '평균 이상', "
        f"{m_good} 안쪽이면 '매우 좋은 편'에 해당합니다. 40대 여성은 각각 {f_avg}, {f_good}입니다. "
        f"나이와 성별을 보정한 calrank 자체 기준이며 공인 통계는 아닙니다.{link}"
    )


def build_meta_description(ev: dict) -> str:
    text = build_summary(ev)
    return text if len(text) <= 150 else text[:147] + "…"


def build_title(ev: dict) -> str:
    d = parse_date(ev.get("date"))
    base = ev.get("name", "")
    tail = []
    if d:
        tail.append(f"{d.year}.{d.month:02d}.{d.day:02d}")
    if ev.get("region") and ev["region"] not in ("전국", "미표기"):
        tail.append(ev["region"])
    suffix = " ".join(tail)
    return f"{base} — {suffix} 대회 일정·접수 | calrank" if suffix else f"{base} 대회 일정·접수 | calrank"


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
    return (
        f'<section class="hero"><p class="hero-sub">{esc(sport)}</p><h1>{esc(ev.get("name"))}</h1></section>'
        f'<div class="modal-fields" style="margin-top:24px;">'
        f'<div class="modal-field-row"><span class="k">일시</span><span class="v">{esc(when)}</span></div>'
        f'<div class="modal-field-row"><span class="k">장소</span><span class="v">{esc(ev.get("location") or "미확인")}</span></div>'
        f'<div class="modal-field-row"><span class="k">종목/거리</span><span class="v">{esc(" / ".join(ev.get("distances") or []))}</span></div>'
        f'<div class="modal-field-row"><span class="k">주최</span><span class="v">{organizer}</span></div>'
        f'</div>'
        f'<a class="modal-apply-btn" style="display:inline-block;text-decoration:none;margin-top:24px;" '
        f'href="{esc(apply_url)}" target="_blank" rel="noopener">신청하기 ↗</a>'
    )


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


def render_page(template: str, ev: dict) -> str:
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
    return out


def main():
    events = json.loads((ROOT / "events.json").read_text(encoding="utf-8"))
    template = (ROOT / "event.html").read_text(encoding="utf-8")
    cutoff = date.today() - timedelta(days=KEEP_DAYS_AFTER)

    OUT_DIR.mkdir(exist_ok=True)
    wanted = {}
    for ev in events:
        d = parse_date(ev.get("date"))
        if not ev.get("id") or not d or d < cutoff:
            continue
        wanted[f"{ev['id']}.html"] = ev

    written = 0
    for fname, ev in wanted.items():
        content = render_page(template, ev)
        p = OUT_DIR / fname
        if not p.exists() or p.read_text(encoding="utf-8") != content:
            p.write_text(content, encoding="utf-8")
            written += 1

    removed = 0
    for p in OUT_DIR.glob("*.html"):
        if p.name not in wanted:
            p.unlink()
            removed += 1
    print(f"[event pages] 대상 {len(wanted)}개, 갱신 {written}개, 정리 {removed}개")


if __name__ == "__main__":
    main()
