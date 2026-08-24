"""
calrank 대회 일정 자동 수집 (다중 소스, 상호 독립).

현재 소스: roadrun.co.kr, cyclo.kr, runningwikii.com, hyroxsouthkorea.com, triathlon.or.kr, runningmap.kr, runneron.com

사용 예시:
  python scripts/fetch_events.py --out events.json
"""

import json
import re
import argparse
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# 일부 사이트가 requests 라이브러리의 기본 User-Agent를 자동 차단하는 경우가 있어,
# 실제 브라우저처럼 보이는 공통 헤더를 모든 요청에 씁니다.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

ROADRUN_URL = "http://www.roadrun.co.kr/schedule/list.php"
ROADRUN_DETAIL_BASE = "http://www.roadrun.co.kr/schedule/"
CYCLO_API_URL = "https://cyclo.kr/api/meetup/schedule"
CYCLO_FALLBACK_URL = "https://cyclo.kr/schedule"

TRAIL_KEYWORDS = ["트레일", "UTMB", "산악", "임도", "알프스"]
CYCLING_KEYWORDS = ["그란폰도", "메디오폰도", "자전거", "사이클"]

REGIONS = [
    "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
    "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
]


def guess_sport(name: str) -> tuple[str, str]:
    if any(k in name for k in TRAIL_KEYWORDS):
        return "trail", "트레일"
    if any(k in name for k in CYCLING_KEYWORDS):
        return "cycling", "자전거"
    return "marathon", "마라톤"


def guess_region(location: str) -> str:
    for r in REGIONS:
        if r in location:
            return r
    return "전국"


def guess_year(month: int, day: int) -> int:
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    candidate = datetime(today.year, month, day)
    grace_period_days = 90
    if (today - candidate).days > grace_period_days:
        return today.year + 1
    return today.year


def slugify(name: str, date: str, prefix: str) -> str:
    base = re.sub(r"[^0-9A-Za-z가-힣]+", "-", name).strip("-").lower()
    return f"{prefix}-{base}-{date}"


def blank_event(**kwargs) -> dict:
    base = {
        "id": None,
        "sport": "marathon",
        "sportLabel": "마라톤",
        "name": "",
        "date": None,
        "time": "미확인",
        "location": "",
        "region": "전국",
        "distances": ["거리 미확인"],
        "organizer": None,
        "organizerPhone": None,
        "regDeadline": None,
        "saves": 0,
        "savesTrend7d": 0,
        "sourceUrl": None,
        "applyUrl": None,
    }
    base.update(kwargs)
    return base


def parse_date_cell(text: str) -> str | None:
    m = re.search(r"(\d{1,2})/(\d{1,2})", text)
    if not m:
        return None
    month, day = int(m.group(1)), int(m.group(2))
    year = guess_year(month, day)
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_name_cell(text: str) -> tuple[str, list[str]]:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return "", []
    name = lines[0]
    distances = []
    for l in lines[1:]:
        distances.extend([d.strip() for d in l.split(",") if d.strip()])
    return name, distances or ["거리 미확인"]


def parse_organizer_cell(cell) -> tuple[str | None, str | None]:
    text = cell.get_text("\n", strip=True)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return None, None
    name = None
    phone = None
    for l in lines:
        if l.startswith("☎"):
            phone = l.replace("☎", "").strip()
        elif name is None:
            name = l
    return name, phone


def parse_homepage_url(organizer_cell) -> str | None:
    for a in organizer_cell.find_all("a"):
        href = a.get("href", "").strip()
        if href.startswith("http://") or href.startswith("https://"):
            return href
    return None


def parse_detail_url(cell) -> str | None:
    a = cell.find("a")
    if not a:
        return None
    href = a.get("href", "")
    m = re.search(r"view\.php\?no=\d+", href)
    if not m:
        return None
    return ROADRUN_DETAIL_BASE + m.group(0)


def fetch_roadrun() -> list[dict]:
    resp = requests.get(ROADRUN_URL, timeout=15, headers=HEADERS)
    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")

    tables = soup.find_all("table")
    target = max(tables, key=lambda t: len(t.find_all("tr")))

    events = []
    for row in target.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) != 4:
            continue

        date_text = cells[0].get_text("\n", strip=True)
        name_text = cells[1].get_text("\n", strip=True)
        location = cells[2].get_text(" ", strip=True)

        date_iso = parse_date_cell(date_text)
        name, distances = parse_name_cell(name_text)
        if not date_iso or not name:
            continue

        sport, sport_label = guess_sport(name)
        organizer, phone = parse_organizer_cell(cells[3])
        detail_url = parse_detail_url(cells[1])
        homepage_url = parse_homepage_url(cells[3])

        events.append(blank_event(
            id=slugify(name, date_iso, "rr"),
            sport=sport,
            sportLabel=sport_label,
            name=name,
            date=date_iso,
            location=location,
            region=guess_region(location),
            distances=distances,
            organizer=organizer,
            organizerPhone=phone,
            sourceUrl=ROADRUN_URL,
            applyUrl=homepage_url or detail_url or ROADRUN_URL,
        ))

    return events


CYCLO_MEETUP_API_BASE = "https://cyclo.kr/api/meetup/"


def format_km(distance: float) -> str:
    if distance == int(distance):
        return f"{int(distance)}km"
    return f"{distance}km"


def fetch_cyclo_detail(meetup_id: int) -> tuple[str | None, list[str]]:
    """개별 대회 상세 API에서 원문 링크와 코스 거리를 함께 가져옵니다."""
    try:
        resp = requests.get(f"{CYCLO_MEETUP_API_BASE}{meetup_id}", timeout=10, headers=HEADERS)
        data = resp.json()
        outlink = data.get("outlink") or None
        courses = data.get("courses") or []
        distances = [format_km(c["distance"]) for c in courses if c.get("distance")]
        return outlink, distances
    except Exception:
        return None, []


def fetch_cyclo() -> list[dict]:
    resp = requests.get(CYCLO_API_URL, timeout=15, headers=HEADERS)
    resp.raise_for_status()
    groups = resp.json()

    events = []
    for group in groups:
        for m in group.get("meetups", []):
            name = m.get("name", "").strip()
            dest_date = m.get("dest_date")
            if not name or not dest_date:
                continue

            date_iso = dest_date.split(" ")[0]
            time_str = dest_date.split(" ")[1][:5] if " " in dest_date else "미확인"
            location = (m.get("address") or {}).get("name", "장소 미확인")
            organizer = m.get("organizer")
            meetup_id = m.get("id")

            outlink, distances = fetch_cyclo_detail(meetup_id) if meetup_id else (None, [])
            detail_url = f"https://cyclo.kr/event_detail/{meetup_id}" if meetup_id else CYCLO_FALLBACK_URL

            events.append(blank_event(
                id=slugify(name, date_iso, "cy"),
                sport="cycling",
                sportLabel="자전거",
                name=name,
                date=date_iso,
                time=time_str,
                location=location,
                region=guess_region(location),
                distances=distances or ["거리 미확인"],
                organizer=organizer,
                sourceUrl=CYCLO_FALLBACK_URL,
                applyUrl=outlink or detail_url,
            ))

    return events


RUNNINGWIKI_URL = "https://runningwikii.com/"


def fetch_runningwiki() -> list[dict]:
    resp = requests.get(RUNNINGWIKI_URL, timeout=15, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    table = soup.find("table")
    if not table:
        return []

    events = []
    this_year = datetime.now().year

    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) != 4:
            continue

        date_text = cells[0].get_text(" ", strip=True)
        m = re.search(r"(\d{1,2})월\s*(\d{1,2})일", date_text)
        if not m:
            continue
        month, day = int(m.group(1)), int(m.group(2))
        date_iso = f"{this_year:04d}-{month:02d}-{day:02d}"

        name_link = cells[1].find("a")
        if not name_link:
            continue
        name = name_link.get_text(strip=True)
        course_span = cells[1].find("span", class_="race-courses")
        distances = [course_span.get_text(strip=True)] if course_span else ["거리 미확인"]

        region = cells[2].get_text(strip=True) or "전국"

        status_span = cells[3].find("span")
        reg_deadline = status_span.get("data-deadline") if status_span else None

        detail_url = name_link.get("href")

        sport, sport_label = guess_sport(name)

        events.append(blank_event(
            id=slugify(name, date_iso, "rw"),
            sport=sport,
            sportLabel=sport_label,
            name=name,
            date=date_iso,
            location=region,
            region=guess_region(region),
            distances=distances,
            regDeadline=reg_deadline,
            sourceUrl=RUNNINGWIKI_URL,
            applyUrl=detail_url or RUNNINGWIKI_URL,
        ))

    return events


HYROX_LIST_URL = "https://hyroxsouthkorea.com/find-your-race/"
HYROX_CITY_KEYWORDS = ["SEOUL", "INCHEON"]
MONTH_ABBR = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def parse_hyrox_date(text: str) -> str | None:
    m = re.search(r"(\d{1,2})\.\s*([A-Za-z]{3})\.?\s*(\d{4})", text)
    if not m:
        return None
    day = int(m.group(1))
    month = MONTH_ABBR.get(m.group(2))
    year = int(m.group(3))
    if not month:
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def fetch_hyrox_ticket_url(detail_url: str) -> str | None:
    try:
        resp = requests.get(detail_url, timeout=15, headers=HEADERS)
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a"):
            href = a.get("href", "")
            if "hyrox.com/event" in href:
                return href
    except Exception:
        pass
    return None


def fetch_hyrox() -> list[dict]:
    resp = requests.get(HYROX_LIST_URL, timeout=15, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items = soup.select(".w-grid-item.event")
    events = []

    for item in items:
        text = item.get_text(" ", strip=True)
        if not any(city in text.upper() for city in HYROX_CITY_KEYWORDS):
            continue

        link = item.find("a")
        if not link:
            continue
        detail_url = link.get("href")

        name_el = item.select_one(".post_title")
        name = name_el.get_text(strip=True) if name_el else text[:40]

        date_iso = parse_hyrox_date(text)
        if not date_iso:
            continue

        location = "서울" if "SEOUL" in text.upper() else "인천"
        ticket_url = fetch_hyrox_ticket_url(detail_url) if detail_url else None

        events.append(blank_event(
            id=slugify(name, date_iso, "hx"),
            sport="hyrox",
            sportLabel="하이록스",
            name=name,
            date=date_iso,
            location=location,
            region=location,
            distances=["하이록스"],
            sourceUrl=HYROX_LIST_URL,
            applyUrl=ticket_url or detail_url or HYROX_LIST_URL,
        ))

    return events


TRIATHLON_URL = "https://triathlon.or.kr/events/tour/"
TRIATHLON_BASE = "https://triathlon.or.kr"

TRIATHLON_NON_RACE_KEYWORDS = ["정기교육", "세미나", "강습회", "심판"]
TRIATHLON_COURSE_KEYWORDS = [
    "아이언맨", "하프코스", "올림픽코스", "스탠다드", "스프린트", "슈퍼스프린트",
    "아쿠아슬론", "듀애슬론", "킹코스", "숏코스", "미니코스",
]


def parse_triathlon_date(text: str) -> str | None:
    m = re.match(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", text.strip())
    if not m:
        return None
    year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return f"{year:04d}-{month:02d}-{day:02d}"


def is_triathlon_non_race(name: str) -> bool:
    """대회규정 정기교육, 심판 강습회, 승급 세미나 등 실제 대회가 아닌 협회 공지를 걸러냅니다."""
    return any(k in name for k in TRIATHLON_NON_RACE_KEYWORDS)


def parse_triathlon_course(info_text: str, name: str = "") -> list[str]:
    """목록 페이지의 '코스: ...' 텍스트, 없으면 제목의 괄호/키워드에서 종목·코스 정보를 추출합니다."""
    m = re.search(r"코스:\s*(.+)", info_text)
    if m:
        course_text = m.group(1).strip()
        if course_text:
            return [course_text]

    # Fallback 1: 제목 괄호 안에 코스 정보가 있는 경우
    # 예: "...전국 철인3종대회(토요일: 스프린트 / 일요일: 스탠다드)"
    paren_m = re.search(r"\(([^)]+)\)", name)
    if paren_m and any(k in paren_m.group(1) for k in TRIATHLON_COURSE_KEYWORDS):
        parts = [p.strip() for p in re.split(r"[/,]", paren_m.group(1)) if p.strip()]
        if parts:
            return parts

    # Fallback 2: 제목 자체에 코스 키워드가 포함된 경우
    found = [k for k in TRIATHLON_COURSE_KEYWORDS if k in name]
    if found:
        return found

    return ["종목 미확인"]


def fetch_triathlon() -> list[dict]:
    resp = requests.get(TRIATHLON_URL, timeout=15, headers=HEADERS)
    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []
    for row in soup.select("table tr"):
        cells = row.find_all("td")
        if len(cells) != 3:
            continue

        info_text = cells[0].get_text("\n", strip=True)
        lines = [l for l in info_text.split("\n") if l.strip()]
        if len(lines) < 2:
            continue

        name = lines[1] if lines[0] in ("접수중", "접수예정", "접수마감") else lines[0]
        if is_triathlon_non_race(name):
            continue

        location_match = re.search(r"장소:\s*(.+)", info_text)
        location = location_match.group(1).strip() if location_match else "전국"
        distances = parse_triathlon_course(info_text, name)

        date_text = cells[1].get_text(strip=True)
        date_iso = parse_triathlon_date(date_text)
        if not date_iso or not name:
            continue

        link = cells[0].find("a")
        detail_url = None
        if link:
            href = link.get("href", "")
            detail_url = TRIATHLON_BASE + href if href.startswith("/") else href

        events.append(blank_event(
            id=slugify(name, date_iso, "tri"),
            sport="triathlon",
            sportLabel="철인3종",
            name=name,
            date=date_iso,
            location=location,
            region=guess_region(location),
            distances=distances,
            sourceUrl=TRIATHLON_URL,
            applyUrl=detail_url or TRIATHLON_URL,
        ))

    return events

RUNNINGMAP_BASE = "https://runningmap.kr"
RUNNINGMAP_SUPABASE_URL = "https://cukapfkyrfchluxgpixt.supabase.co/rest/v1/races"


def find_runningmap_supabase_key() -> str | None:
    try:
        html = requests.get(RUNNINGMAP_BASE, timeout=15, headers=HEADERS).text
        script_match = re.search(r'src="(/assets/index-[^"]+\.js)"', html)
        if not script_match:
            return None
        js_url = RUNNINGMAP_BASE + script_match.group(1)
        js_text = requests.get(js_url, timeout=15, headers=HEADERS).text

        new_format = re.search(r"sb_publishable_[\w-]+", js_text)
        if new_format:
            return new_format.group(0)
        old_format = re.search(r"eyJ[\w-]+\.[\w-]+\.[\w-]+", js_text)
        return old_format.group(0) if old_format else None
    except Exception:
        return None


def fetch_runningmap() -> list[dict]:
    key = find_runningmap_supabase_key()
    if not key:
        return []

    headers = {**HEADERS, "apikey": key, "Authorization": f"Bearer {key}"}
    resp = requests.get(
        f"{RUNNINGMAP_SUPABASE_URL}?select=*&order=race_date.asc",
        headers=headers, timeout=15,
    )
    resp.raise_for_status()
    rows = resp.json()

    events = []
    for row in rows:
        name = row.get("name")
        date_iso = row.get("race_date")
        if not name or not date_iso:
            continue
        date_iso = str(date_iso)[:10]

        location = row.get("location") or "장소 미확인"
        region = row.get("region") or guess_region(location)
        reg_deadline = row.get("reg_end")
        apply_url = row.get("apply_url") or row.get("homepage_url")
        organizer = row.get("organizer")
        courses = row.get("courses")
        distances = courses if isinstance(courses, list) and courses else ["거리 미확인"]

        sport, sport_label = guess_sport(name)

        events.append(blank_event(
            id=slugify(name, date_iso, "rm"),
            sport=sport,
            sportLabel=sport_label,
            name=name,
            date=date_iso,
            location=location,
            region=region,
            distances=distances,
            organizer=organizer,
            regDeadline=str(reg_deadline)[:10] if reg_deadline else None,
            sourceUrl=RUNNINGMAP_BASE,
            applyUrl=apply_url or RUNNINGMAP_BASE,
        ))

    return events


RUNNERON_LIST_URL = "https://www.runneron.com/marathon"
RUNNERON_BASE = "https://www.runneron.com"


def fetch_runneron_detail(detail_url: str) -> tuple[str | None, str | None, str | None]:
    try:
        resp = requests.get(detail_url, timeout=15, headers=HEADERS)
        soup = BeautifulSoup(resp.text, "html.parser")

        homepage = None
        for a in soup.find_all("a"):
            if "공식 홈페이지" in a.get_text() or "접수 페이지" in a.get_text():
                href = a.get("href", "")
                if href.startswith("http"):
                    homepage = href
                    break

        text = soup.get_text()
        m = re.search(r"접수기간\s*([\d.]+)\s*~\s*([\d.]+)", text)
        reg_start = reg_end = None
        if m:
            reg_start = m.group(1).replace(".", "-")
            reg_end = m.group(2).replace(".", "-")

        return homepage, reg_start, reg_end
    except Exception:
        return None, None, None


def fetch_runneron() -> list[dict]:
    resp = requests.get(RUNNERON_LIST_URL, timeout=15, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []
    for card in soup.select("a.marathon_card"):
        name = card.select_one(".marathon_card_name")
        if not name:
            continue
        name = name.get_text(strip=True)

        date_el = card.select_one(".marathon_card_date")
        date_text = date_el.get_text(" ", strip=True) if date_el else ""
        m = re.search(r"(\d{1,2})\.(\d{1,2})", date_text)
        if not m:
            continue
        month, day = int(m.group(1)), int(m.group(2))
        date_iso = f"{guess_year(month, day):04d}-{month:02d}-{day:02d}"

        loc_el = card.select_one(".marathon_card_loc")
        location = loc_el.get_text(strip=True) if loc_el else "장소 미확인"
        region_el = card.select_one(".marathon_card_region")
        region = region_el.get_text(strip=True) if region_el else guess_region(location)

        meta_el = card.select_one(".marathon_card_meta")
        distances = ["거리 미확인"]
        if meta_el:
            meta_lines = [l.strip() for l in meta_el.get_text("\n").split("\n") if l.strip() and l.strip() != location]
            if meta_lines:
                distances = meta_lines

        detail_href = card.get("href", "")
        detail_url = RUNNERON_BASE + detail_href if detail_href.startswith("/") else detail_href

        homepage, reg_start, reg_end = fetch_runneron_detail(detail_url) if detail_url else (None, None, None)

        sport, sport_label = guess_sport(name)

        events.append(blank_event(
            id=slugify(name, date_iso, "ro"),
            sport=sport,
            sportLabel=sport_label,
            name=name,
            date=date_iso,
            location=location,
            region=region,
            distances=distances,
            regDeadline=reg_end,
            sourceUrl=RUNNERON_LIST_URL,
            applyUrl=homepage or detail_url or RUNNERON_LIST_URL,
        ))

    return events


SOURCES = [
    ("roadrun.co.kr", fetch_roadrun),
    ("cyclo.kr", fetch_cyclo),
    ("runningwikii.com", fetch_runningwiki),
    ("hyroxsouthkorea.com", fetch_hyrox),
    ("triathlon.or.kr", fetch_triathlon),
    ("runningmap.kr", fetch_runningmap),
    ("runneron.com", fetch_runneron),
]


def dedupe_across_sources(events: list[dict]) -> list[dict]:
    groups: dict[tuple, dict] = {}
    for ev in events:
        key = (ev["name"].strip(), ev["date"])
        if key not in groups:
            groups[key] = ev
        else:
            existing = groups[key]
            for field in ("regDeadline", "organizer", "organizerPhone", "region", "location"):
                if not existing.get(field) and ev.get(field):
                    existing[field] = ev[field]
    return list(groups.values())


def merge_and_dedupe(existing: list[dict], new_events: list[dict]) -> list[dict]:
    by_id = {ev["id"]: ev for ev in existing}
    for ev in new_events:
        prev = by_id.get(ev["id"], {})
        merged = {**ev}
        merged["saves"] = prev.get("saves", ev["saves"])
        merged["savesTrend7d"] = prev.get("savesTrend7d", ev["savesTrend7d"])
        by_id[ev["id"]] = merged

    # 예전에 저장된 철인3종 비-대회 게시물(정기교육/세미나/강습회 등)은
    # 이후 수집에서 더 이상 나타나지 않아도 계속 남아있으므로 여기서 함께 제거합니다.
    values = [
        ev for ev in by_id.values()
        if not (ev.get("sport") == "triathlon" and is_triathlon_non_race(ev.get("name", "")))
    ]
    return sorted(values, key=lambda e: e["date"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="events.json")
    args = parser.parse_args()

    try:
        with open(args.out, encoding="utf-8") as f:
            existing = json.load(f)
    except FileNotFoundError:
        existing = []

    all_new = []
    for source_name, fetch_fn in SOURCES:
        try:
            new_events = fetch_fn()
            print(f"[{source_name}] {len(new_events)}개 수집 성공")
            all_new.extend(new_events)
        except Exception as e:
            print(f"[{source_name}] 수집 실패, 건너뜀: {e}")

    merged = merge_and_dedupe(existing, dedupe_across_sources(all_new))

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"[{datetime.now().isoformat()}] {len(merged)}개 대회 저장 완료 ({args.out})")


if __name__ == "__main__":
    main()
AiPrice
