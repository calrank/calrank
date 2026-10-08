"""
calrank 대회 일정 자동 수집 (다중 소스, 상호 독립).

현재 소스: roadrun.co.kr, cyclo.kr, runningwikii.com, triathlon.or.kr, runningmap.kr, runneron.com
(hyroxsouthkorea.com은 robots.txt에서 AI 크롤러를 명시적으로 차단하여 2026-08-27부로 사용 중단)

사용 예시:
  python scripts/fetch_events.py --out events.json
"""

import os
import json
import re
import argparse
import random
import time
from datetime import datetime, timedelta
from urllib.parse import quote

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


# location에 광역 약칭("경기")이 아니라 정식 명칭("경기도")이나 시/군 단위
# 지명("충주", "홍천")만 있는 경우가 자전거·인라인 소스에서 흔해, 이 둘을
# 보강하지 않으면 전부 "전국"으로 떨어져 지역 랜딩이 텅 비게 된다.
REGION_FULL_NAME = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구",
    "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
    "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기",
    "강원도": "강원", "강원특별자치도": "강원",
    "충청북도": "충북", "충청남도": "충남",
    "전라북도": "전북", "전북특별자치도": "전북", "전라남도": "전남",
    "경상북도": "경북", "경상남도": "경남",
    "제주도": "제주", "제주특별자치도": "제주",
}
CITY_TO_REGION = {
    "영월": "강원", "원주": "강원", "홍천": "강원", "춘천": "강원", "삼척": "강원",
    "가평": "경기", "여주": "경기", "양평": "경기",
    "부안": "전북", "정읍": "전북", "무주": "전북", "전주": "전북",
    "예천": "경북", "문경": "경북", "상주": "경북", "안동": "경북",
    "김해": "경남", "고성": "강원",  # "경상남도 고성군"은 정식 명칭 단계에서 먼저 "경남"으로 잡힌다
    "여수": "전남", "나주": "전남",
    "제천": "충북", "영동": "충북", "충주": "충북",
    "공주": "충남", "부여": "충남",
}


def guess_region(location: str) -> str:
    for full, short in REGION_FULL_NAME.items():
        if full in location:
            return short
    for r in REGIONS:
        if r in location:
            return r
    for city, region in CITY_TO_REGION.items():
        if city in location:
            return region
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
        "regClosed": None,
        "lat": None,
        "lng": None,
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


def fetch_roadrun_deadline(detail_url: str) -> str | None:
    """roadrun.co.kr 목록 페이지엔 접수기간이 없고, 개별 상세 페이지(view.php?no=...)에만
    '접수기간: 2026년6월30일~2026년7월31일' 형태로 존재한다. 상세 페이지를 추가로 방문해
    종료일(~ 뒤 날짜)만 뽑아 ISO 형식으로 반환한다. 실패해도 조용히 None을 반환해
    전체 수집이 중단되지 않도록 한다."""
    try:
        resp = requests.get(detail_url, timeout=10, headers=HEADERS)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")
        tds = soup.find_all("td")
        for i, td in enumerate(tds):
            if td.get_text(strip=True) == "접수기간" and i + 1 < len(tds):
                period_text = tds[i + 1].get_text(strip=True)
                m = re.search(r"~\s*(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", period_text)
                if m:
                    y, mo, d = m.groups()
                    return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
                return None
    except Exception:
        return None
    return None


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

        # 목록에 없는 접수기간을 상세 페이지에서 추가로 가져온다. 대상 사이트에
        # 부담을 주지 않도록 매 요청 사이 짧은 랜덤 딜레이를 둔다.
        reg_deadline = None
        if detail_url:
            reg_deadline = fetch_roadrun_deadline(detail_url)
            time.sleep(random.uniform(0.15, 0.35))

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
            regDeadline=reg_deadline,
            sourceUrl=ROADRUN_URL,
            applyUrl=homepage_url or detail_url or ROADRUN_URL,
        ))

    return events


CYCLO_MEETUP_API_BASE = "https://cyclo.kr/api/meetup/"


def format_km(distance: float) -> str:
    if distance == int(distance):
        return f"{int(distance)}km"
    return f"{distance}km"


def fetch_cyclo_detail(meetup_id: int) -> tuple[str | None, list[str], bool | None, float | None, float | None]:
    """개별 대회 상세 API에서 원문 링크, 코스 거리, 접수 마감 여부, 좌표를 함께 가져옵니다.
    cyclo.kr API는 명시적인 접수 마감일 필드가 없고, 대신 is_closed(현재 마감 여부) 불리언만 제공합니다.
    위경도는 최상위가 아니라 address.latitude/longitude에 중첩되어 있습니다."""
    try:
        resp = requests.get(f"{CYCLO_MEETUP_API_BASE}{meetup_id}", timeout=10, headers=HEADERS)
        data = resp.json()
        outlink = data.get("outlink") or None
        courses = data.get("courses") or []
        distances = [format_km(c["distance"]) for c in courses if c.get("distance")]
        is_closed = data.get("is_closed")
        address = data.get("address") or {}
        lat = address.get("latitude")
        lng = address.get("longitude")
        return outlink, distances, is_closed, lat, lng
    except Exception:
        return None, [], None, None, None


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

            outlink, distances, is_closed, lat, lng = fetch_cyclo_detail(meetup_id) if meetup_id else (None, [], None, None, None)
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
                regClosed=is_closed,
                lat=lat,
                lng=lng,
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
        race_time = row.get("race_time") or "미확인"
        lat = row.get("lat")
        lng = row.get("lng")

        sport, sport_label = guess_sport(name)

        events.append(blank_event(
            id=slugify(name, date_iso, "rm"),
            sport=sport,
            sportLabel=sport_label,
            name=name,
            date=date_iso,
            time=race_time,
            location=location,
            region=region,
            distances=distances,
            organizer=organizer,
            regDeadline=str(reg_deadline)[:10] if reg_deadline else None,
            lat=lat,
            lng=lng,
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


KOREASKATE_API_URL = "https://koreaskate.or.kr/api/schedule"
KOREASKATE_BASE_URL = "https://koreaskate.or.kr/news/schedule/"
KOREASKATE_OVERSEAS_KEYWORDS = ["중국", "일본", "대만", "이탈리아", "브라질", "파라과이", "세네갈", "미국", "유럽"]


def fetch_koreaskate() -> list[dict]:
    """대한롤러스포츠연맹 API에서 '생활체육'/'마라톤' 카테고리(동호인 참가형)만 골라 수집합니다.
    학교/실업팀 대항전, 국가대표 선발전 등 엘리트 전용 대회와 해외 대회는 제외합니다."""
    events = []
    current_year = datetime.now().year
    for year in (current_year, current_year + 1):
        try:
            resp = requests.get(f"{KOREASKATE_API_URL}?year={year}", timeout=15, headers=HEADERS)
            resp.raise_for_status()
            items = resp.json()
        except Exception:
            continue

        for item in items:
            title = (item.get("title") or "").strip()
            if not title or not ("생활체육" in title or "마라톤" in title):
                continue
            location = item.get("location") or "장소 미확인"
            if any(kw in location for kw in KOREASKATE_OVERSEAS_KEYWORDS):
                continue
            event_date = item.get("eventDate")
            if not event_date:
                continue
            date_iso = str(event_date)[:10]

            events.append(blank_event(
                id=slugify(title, date_iso, "ks"),
                sport="inline",
                sportLabel="인라인",
                name=title,
                date=date_iso,
                location=location,
                region=guess_region(location),
                distances=["거리 미확인"],
                sourceUrl=KOREASKATE_BASE_URL,
                applyUrl=KOREASKATE_BASE_URL,
            ))
    return events


SOURCES = [
    ("roadrun.co.kr", fetch_roadrun),
    ("cyclo.kr", fetch_cyclo),
    ("runningwikii.com", fetch_runningwiki),
    # ("hyroxsouthkorea.com", fetch_hyrox),  # 2026-08-27: robots.txt에서 anthropic-ai 등 AI 크롤러를 명시적으로 차단하고 있어 사용 중단
    ("triathlon.or.kr", fetch_triathlon),
    ("runningmap.kr", fetch_runningmap),
    ("runneron.com", fetch_runneron),
    ("koreaskate.or.kr", fetch_koreaskate),
]


# 같은 대회가 소스마다 조금씩 다르게 적혀 들어온다.
#   "제3회서울트레일런 대회" / "제3회 서울트레일런 대회"   (띄어쓰기)
#   "2026 연수 꿈이음길 러닝대회" / "연수 꿈이음길 러닝대회"  (앞머리 연도)
# 예전에는 이름을 글자 그대로 비교해서 이런 것들이 전부 별개 대회로 남았고,
# 그 결과 전체의 19%가 중복이었다. 캘린더에 같은 대회가 세 번 뜨고,
# e/<id>.html 도 세 벌씩 생겨 검색엔진에는 중복 콘텐츠로 보인다.
def normalize_name(name: str) -> str:
    s = str(name or "")
    s = re.sub(r"^\s*20\d{2}\s*년?\s*", "", s)   # 앞머리 연도
    s = re.sub(r"제?\s*\d+\s*회", "", s)          # 제N회
    s = re.sub(r"[^0-9A-Za-z가-힣]", "", s)        # 공백·기호
    return s.lower()


def _meaningful(v) -> bool:
    if v is None:
        return False
    s = str(v).strip()
    return bool(s) and not _PLACEHOLDER_RE.fullmatch(s)


def _completeness(ev: dict) -> int:
    """정보가 더 많이 찬 레코드를 대표로 삼기 위한 점수."""
    score = 0
    for f in ("regDeadline", "applyUrl", "organizer", "organizerPhone", "sourceUrl"):
        if _meaningful(ev.get(f)):
            score += 1
    if ev.get("lat") and ev.get("lng"):
        score += 2
    score += len([d for d in (ev.get("distances") or []) if _meaningful(d)])
    # 지역명("서울")보다 실제 장소("낙산공원 중앙광장")가 쓸모 있다
    loc, region = ev.get("location"), ev.get("region")
    if _meaningful(loc) and str(loc).strip() != str(region or "").strip():
        score += 2
    return score


def dedupe_across_sources(
    events: list[dict], known_ids: "set[str] | None" = None
) -> "tuple[list[dict], dict[str, str]]":
    """이름을 정규화해 같은 대회를 하나로 합친다.

    돌려주는 두 번째 값은 {사라진 id: 살아남은 id} 다. 이미 색인된 주소가
    404 가 되지 않도록 vercel.json 에 301 리다이렉트로 깔기 위한 것이다.
    """
    known = known_ids or set()
    groups: "dict[tuple, list[dict]]" = {}
    for ev in events:
        groups.setdefault((normalize_name(ev.get("name")), ev.get("date")), []).append(ev)

    out: list[dict] = []
    aliases: dict[str, str] = {}

    for items in groups.values():
        # 대표는 '이미 배포된 주소'를 최우선으로 고른다. 검색엔진이 알고 있는
        # 주소를 유지해야 쌓인 색인이 날아가지 않는다.
        published = [e for e in items if e.get("id") in known]
        pool = published or items
        winner = max(pool, key=_completeness)

        merged = {**winner}
        for other in items:
            if other is winner:
                continue
            for field in ("regDeadline", "organizer", "organizerPhone", "applyUrl",
                          "sourceUrl", "time", "region"):
                if not _meaningful(merged.get(field)) and _meaningful(other.get(field)):
                    merged[field] = other[field]
            # "전국"은 소스가 지역을 안 적었을 때 들어가는 기본값이다. 다른 소스가
            # 실제 지역을 알고 있으면 그쪽을 쓴다. 안 그러면 지역별 페이지에서
            # 그 대회가 통째로 빠진다(현재 전체의 22%가 "전국"으로 묶여 있다).
            if merged.get("region") == "전국" and _meaningful(other.get("region")) \
               and other["region"] != "전국":
                merged["region"] = other["region"]
            if not (merged.get("lat") and merged.get("lng")) and other.get("lat") and other.get("lng"):
                merged["lat"], merged["lng"] = other["lat"], other["lng"]
            # 지역명뿐이면 구체적인 장소로 바꾼다
            if _meaningful(other.get("location")) and \
               str(other["location"]).strip() != str(other.get("region") or "").strip() and \
               (not _meaningful(merged.get("location")) or
                    str(merged["location"]).strip() == str(merged.get("region") or "").strip()):
                merged["location"] = other["location"]
            # 거리는 소스마다 일부만 적어 두는 일이 많아 합집합으로 모은다
            seen = [d for d in (merged.get("distances") or []) if _meaningful(d)]
            for d in (other.get("distances") or []):
                if _meaningful(d) and d not in seen:
                    seen.append(d)
            merged["distances"] = seen
            merged["saves"] = max(merged.get("saves") or 0, other.get("saves") or 0)

        out.append(merged)
        for other in items:
            if other.get("id") and other["id"] != merged["id"]:
                aliases[other["id"]] = merged["id"]

    return out, aliases


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
        # hyroxsouthkorea.com은 2026-08-27부로 소스에서 제외되어 더 이상 갱신되지 않으므로,
        # 남아있는 하이록스 데이터도 함께 정리합니다.
        and ev.get("sport") != "hyrox"
    ]
    return sorted(values, key=lambda e: e["date"])


# 주최측이 아직 안 정한 항목에 들어오는 문구들. 라벨이 붙은 형태도 함께 잡는다.
_PLACEHOLDER_RE = re.compile(r"(장소|시간|주최|접수|코스|거리|종목)?\s*(미확인|미정|확인\s*중|추후\s*공지|별도\s*공지)")


def ics_escape(text: str) -> str:
    return (text or "").replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def ics_fold(line: str) -> str:
    """RFC 5545: 한 줄은 75옥텟을 넘지 못한다. 넘으면 접고 다음 줄을 공백으로 시작한다.
    한글은 UTF-8에서 3바이트라 글자 중간에서 자르면 캘린더 앱이 깨뜨린다.
    그래서 바이트가 아니라 '글자를 더해 가며 바이트를 세는' 방식으로 자른다."""
    out, cur, used, first = [], [], 0, True
    for ch in line:
        n = len(ch.encode("utf-8"))
        limit = 75 if first else 74   # 이어지는 줄은 앞의 공백 1옥텟을 쓴다
        if used + n > limit:
            out.append("".join(cur))
            cur, used, first = [ch], n, False
        else:
            cur.append(ch)
            used += n
    out.append("".join(cur))
    return "\r\n ".join(out)


# 구독자가 실제로 받고 싶은 알림은 둘이다: 접수 마감(놓치면 출전 불가)과 대회 당일.
# 둘 다 VALARM 으로 넣으면 구글/애플 캘린더가 알아서 푸시를 보내 준다.
# 서버도, 계정도, 이메일 발송도 필요 없다.
def _valarm(trigger: str, text: str) -> list[str]:
    return ["BEGIN:VALARM", "ACTION:DISPLAY",
            f"TRIGGER:{trigger}", f"DESCRIPTION:{ics_escape(text)}", "END:VALARM"]


def _event_block(ev: dict, now_stamp: str) -> list[str]:
    """대회 하루 + (접수 마감이 아직 안 지났으면) 접수 마감일, 두 개의 일정을 만든다."""
    blocks: list[str] = []
    name = ev.get("name", "대회")
    dt = ev["date"].replace("-", "")
    url = f"https://calrank.vercel.app/e/{quote(ev['id'])}.html"

    def val(key):
        """'미확인', '장소 미확인' 같은 자리채움 값은 빼고 돌려준다.
        캘린더에 그대로 들어가면 알림마다 의미 없는 줄이 하나씩 붙는다."""
        v = ev.get(key)
        if v is None:
            return None
        v = str(v).strip()
        if not v or v in {"-", "none", "None"}:
            return None
        if _PLACEHOLDER_RE.fullmatch(v):
            return None
        return v

    desc_parts = []
    dists = [str(d).strip() for d in (ev.get("distances") or [])]
    dists = [d for d in dists if d and not _PLACEHOLDER_RE.fullmatch(d)]
    if dists:
        desc_parts.append("종목: " + ", ".join(dists))
    for key, label in (("time", "시간"), ("location", "장소"),
                       ("regDeadline", "접수 마감"), ("organizer", "주최"),
                       ("applyUrl", "신청")):
        v = val(key)
        if v:
            desc_parts.append(f"{label}: {v}")
    desc_parts.append(url)
    desc = ics_escape("\n".join(desc_parts))

    blocks += [
        "BEGIN:VEVENT",
        f"UID:{ev['id']}@calrank.vercel.app",
        f"DTSTAMP:{now_stamp}",
        f"DTSTART;VALUE=DATE:{dt}",
        f"SUMMARY:{ics_escape(name)}",
        f"LOCATION:{ics_escape(ev.get('location', ''))}",
        f"DESCRIPTION:{desc}",
        f"URL:{url}",
        "TRANSP:TRANSPARENT",
    ]
    blocks += _valarm("-P7D", f"{name} D-7 — 준비물과 교통편을 확인하세요")
    blocks += _valarm("-P1D", f"{name} 내일입니다 — 배번과 출발 시간을 확인하세요")
    blocks.append("END:VEVENT")

    # 접수 마감일: 아직 지나지 않았고 대회일보다 앞설 때만 별도 일정으로 넣는다
    dl = ev.get("regDeadline")
    if dl and isinstance(dl, str) and len(dl) == 10:
        try:
            dl_date = datetime.strptime(dl, "%Y-%m-%d").date()
        except ValueError:
            dl_date = None
        if dl_date and dl_date >= datetime.now().date() and dl < ev["date"]:
            blocks += [
                "BEGIN:VEVENT",
                f"UID:{ev['id']}-deadline@calrank.vercel.app",
                f"DTSTAMP:{now_stamp}",
                f"DTSTART;VALUE=DATE:{dl.replace('-', '')}",
                f"SUMMARY:{ics_escape('[접수 마감] ' + name)}",
                f"DESCRIPTION:{desc}",
                f"URL:{url}",
                "TRANSP:TRANSPARENT",
            ]
            blocks += _valarm("-P3D", f"{name} 접수 마감 3일 전입니다")
            blocks += _valarm("-P1D", f"{name} 접수가 내일 마감됩니다")
            blocks.append("END:VEVENT")
    return blocks


def _write_ics(path: str, cal_name: str, cal_desc: str, events: list[dict]) -> int:
    now_stamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//calrank//KO",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{ics_escape(cal_name)}",
        f"X-WR-CALDESC:{ics_escape(cal_desc)}",
        "X-WR-TIMEZONE:Asia/Seoul",
        # 캘린더 앱이 하루 두 번 다시 받아 가도록 (새 대회가 알아서 들어온다)
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
        "X-PUBLISHED-TTL:PT12H",
    ]
    for ev in events:
        lines += _event_block(ev, now_stamp)
    lines.append("END:VCALENDAR")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\r\n".join(ics_fold(l) for l in lines) + "\r\n")
    return len(events)


def generate_ics_feed(events: list[dict], out_path: str = "feed.ics") -> None:
    """예정 대회를 iCalendar 구독 피드로 만든다.

    전체 1,000여 개를 한 덩어리로 주면 아무도 구독하지 못하므로 종목별 피드도 같이 낸다.
    구독해 두면 새 대회가 올라올 때마다 캘린더가 알아서 받아 가고, 접수 마감과
    대회 당일에 알림이 울린다 — 계정도 이메일 발송 설비도 필요 없는 재방문 장치다."""
    today = datetime.now().date()
    upcoming = []
    for ev in events:
        try:
            ev_date = datetime.strptime(ev["date"], "%Y-%m-%d").date()
        except (KeyError, ValueError, TypeError):
            continue
        if ev_date >= today:
            upcoming.append(ev)
    upcoming.sort(key=lambda e: e["date"])

    n = _write_ics(out_path, "calrank 전체 대회 일정",
                   "calrank.vercel.app — 마라톤·자전거·트레일·철인3종·인라인 대회 일정", upcoming)
    print(f"[feed.ics] {n}개 대회 캘린더 구독 피드 생성 완료")

    # 종목 라벨은 상수로 두지 않고 데이터에서 그대로 읽는다 (새 종목이 생겨도 따라온다)
    sports: dict[str, str] = {}
    for e in upcoming:
        sp = e.get("sport")
        if sp and sp not in sports:
            sports[sp] = e.get("sportLabel") or sp

    for sport, label in sorted(sports.items()):
        subset = [e for e in upcoming if e.get("sport") == sport]
        if not subset:
            continue
        _write_ics(f"feed-{sport}.ics", f"calrank {label} 대회 일정",
                   f"calrank.vercel.app — {label} 대회 일정과 접수 마감 알림", subset)
        print(f"[feed-{sport}.ics] {len(subset)}개 {label} 대회")

# 첫 화면의 제목·설명은 검색에서 가장 큰 자리다. 경쟁 사이트들은 전부
# "마라톤 대회 일정"이라는 말을 제목에 그대로 넣는데, 예전 제목은
# "calrank — 전종목 대회 캘린더"여서 사람들이 치는 말이 하나도 없었다.
# 연도와 대회 수가 들어가므로 매일 갱신해 준다(안 그러면 해가 바뀌어도 그대로다).
HOME_PATH = "index.html"


def refresh_home_meta(events: list[dict]) -> None:
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), HOME_PATH)
    if not os.path.exists(path):
        return
    today = datetime.now().date()
    today_iso = today.isoformat()
    upcoming = [e for e in events if (e.get("date") or "") >= today_iso]
    opening = [e for e in upcoming
               if e.get("regDeadline") and str(e["regDeadline"]) >= today_iso]
    year = today.year

    title = (f"{year} 마라톤 대회 일정 | 전국 마라톤·트레일러닝·자전거 접수 캘린더 - calrank")
    desc = (f"{year} 전국 마라톤 대회 일정을 월별·지역별·거리(5km·10km·하프·풀코스)로 "
            f"정리했습니다. 예정 대회 {len(upcoming)}개, 접수 진행 중 {len(opening)}개. "
            f"접수 마감일과 신청 링크를 한눈에 보고, 캘린더에 추가하면 마감 전에 알림을 받습니다.")
    og_desc = (f"{year} 전국 마라톤·트레일러닝·자전거 대회 일정과 접수 마감일을 한곳에서. "
               f"예정 대회 {len(upcoming)}개.")
    h1 = f"{year} 마라톤 대회 일정 — 전국 마라톤·자전거·트레일러닝·철인3종·인라인 캘린더"

    with open(path, encoding="utf-8") as f:
        html = f.read()
    before = html

    def swap(pattern: str, replacement: str) -> None:
        nonlocal html
        html = re.sub(pattern, lambda _m: replacement, html, count=1)

    swap(r"<title>[^<]*</title>", f"<title>{title}</title>")
    swap(r'<meta name="description" content="[^"]*">',
         f'<meta name="description" content="{desc}">')
    swap(r'<meta property="og:title" content="[^"]*">',
         f'<meta property="og:title" content="{title}">')
    swap(r'<meta property="og:description" content="[^"]*">',
         f'<meta property="og:description" content="{og_desc}">')
    swap(r'<meta name="twitter:title" content="[^"]*">',
         f'<meta name="twitter:title" content="{title}">')
    swap(r'<meta name="twitter:description" content="[^"]*">',
         f'<meta name="twitter:description" content="{og_desc}">')
    swap(r"<h1>[^<]*</h1>", f"<h1>{h1}</h1>")

    if html != before:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[index.html] 제목·설명 갱신 (예정 {len(upcoming)}개, 접수중 {len(opening)}개)")


def generate_event_sitemap(events: list[dict], out_path: str = "sitemap-events.xml") -> None:
    """대회별 정적 상세 페이지(e/<id>.html) URL을 모은 sitemap을 자동 생성합니다.
    구글이 개별 대회 페이지를 빠르게 발견할 수 있도록, 매 크롤링마다 최신 상태로 갱신됩니다."""
    today = datetime.now().date()
    # generate_event_pages.py가 지난 대회 페이지도 약 3년간 남긴다.
    # "○○마라톤 기록"은 대회가 끝난 뒤에 검색되므로, 지난 대회도 사이트맵에
    # 넣어야 보존한 의미가 있다. (예전에는 예정 대회만 넣어 지난 페이지가
    # 파일로만 존재하고 검색엔진에는 제출되지 않았다.)
    oldest = today - timedelta(days=1095)
    listed = []
    for ev in events:
        try:
            ev_date = datetime.strptime(ev["date"], "%Y-%m-%d").date()
        except (KeyError, ValueError, TypeError):
            continue
        if ev_date >= oldest:
            listed.append((ev, ev_date >= today))

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for ev, is_upcoming in listed:
        # 검색엔진이 내용을 바로 읽을 수 있는 정적 페이지(e/<id>.html)를 가리킨다.
        # (event.html?id=... 는 내용을 JS가 채워서 색인에 불리했다)
        url = f"https://calrank.vercel.app/e/{quote(ev['id'])}.html"
        lines.append("  <url>")
        lines.append(f"    <loc>{url}</loc>")
        # 끝난 대회는 내용이 더 바뀌지 않는다
        lines.append(f"    <changefreq>{'weekly' if is_upcoming else 'yearly'}</changefreq>")
        lines.append(f"    <priority>{'0.5' if is_upcoming else '0.4'}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    past_n = sum(1 for _, up in listed if not up)
    print(f"[sitemap-events.xml] {len(listed)}개 대회 URL 기록 완료 (지난 대회 {past_n}개 포함)")


ALIAS_PATH = "event_aliases.json"
VERCEL_PATH = "vercel.json"
VERCEL_REDIRECT_CAP = 900   # Vercel 한도는 1024. 여유를 둔다.

ICS_FEEDS = ["feed.ics", "feed-marathon.ics", "feed-trail.ics",
             "feed-cycling.ics", "feed-triathlon.ics", "feed-inline.ics"]


def update_aliases(new_aliases: dict, live_ids: set) -> dict:
    """중복으로 사라진 주소를 계속 모아 둔다.

    한 번 색인된 주소는 나중에 다시 요청이 들어오므로, 이번 실행에서 합쳐진
    것만이 아니라 과거에 합쳐진 것도 계속 리다이렉트해야 한다.
    """
    stored = {}
    if os.path.exists(ALIAS_PATH):
        try:
            with open(ALIAS_PATH, encoding="utf-8") as f:
                stored = json.load(f)
        except (OSError, ValueError):
            stored = {}

    stored.update(new_aliases)

    # 사슬을 편다 (a->b, b->c  ==>  a->c). 리다이렉트가 두 번 도는 걸 막는다.
    def resolve(i, depth=0):
        while i in stored and depth < 10:
            nxt = stored[i]
            if nxt == i:
                break
            i, depth = nxt, depth + 1
        return i

    flat = {src: resolve(dst) for src, dst in stored.items()}
    # 목적지가 더 이상 존재하지 않거나 자기 자신이면 버린다
    flat = {k: v for k, v in flat.items() if v in live_ids and k != v and k not in live_ids}

    with open(ALIAS_PATH, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(flat.items())), f, ensure_ascii=False, indent=1)
    return flat


def generate_vercel_config(aliases: dict) -> None:
    """ICS 헤더와 301 리다이렉트를 vercel.json 으로 쓴다.

    Vercel 은 리다이렉트를 파일시스템보다 먼저 평가하므로, 합쳐져 사라진
    e/<id>.html 이 아직 남아 있어도 곧바로 대표 주소로 넘어간다.
    """
    redirects = [
        {"source": f"/e/{quote(src)}.html",
         "destination": f"/e/{quote(dst)}.html",
         "permanent": True}
        for src, dst in sorted(aliases.items())[:VERCEL_REDIRECT_CAP]
    ]
    cfg = {
        "$schema": "https://openapi.vercel.sh/vercel.json",
        "headers": [
            {"source": f"/{name}",
             "headers": [
                 {"key": "Content-Type", "value": "text/calendar; charset=utf-8"},
                 {"key": "Cache-Control",
                  "value": "public, max-age=0, s-maxage=3600, must-revalidate"},
             ]}
            for name in ICS_FEEDS
        ],
        "redirects": redirects,
    }
    with open(VERCEL_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"[vercel.json] 301 리다이렉트 {len(redirects)}개 기록")


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
    for i, (source_name, fetch_fn) in enumerate(SOURCES):
        try:
            new_events = fetch_fn()
            print(f"[{source_name}] {len(new_events)}개 수집 성공")
            all_new.extend(new_events)
        except Exception as e:
            print(f"[{source_name}] 수집 실패, 건너뜀: {e}")

        # 상대 사이트에 부담을 덜 주기 위해 소스 간에 짧은 랜덤 딜레이를 둡니다.
        if i < len(SOURCES) - 1:
            time.sleep(random.uniform(1.5, 3.5))

    # 이미 배포된 주소를 알려 줘야 대표를 고를 때 색인된 쪽을 남길 수 있다.
    known_ids = {ev["id"] for ev in existing if ev.get("id")}

    # 중복 제거는 '합친 뒤 전체'에 대고 한다. 새로 긁어온 것만 정리하면,
    # merge_and_dedupe 가 기존 events.json 을 통째로 seed 로 쓰기 때문에
    # 예전에 쌓인 중복이 그대로 되살아난다.
    merged = merge_and_dedupe(existing, all_new)
    merged, aliases = dedupe_across_sources(merged, known_ids=known_ids)
    merged.sort(key=lambda e: e["date"])

    live_ids = {ev["id"] for ev in merged if ev.get("id")}

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    all_aliases = update_aliases(aliases, live_ids)
    generate_vercel_config(all_aliases)
    refresh_home_meta(merged)
    generate_event_sitemap(merged)
    generate_ics_feed(merged)

    print(f"[{datetime.now().isoformat()}] {len(merged)}개 대회 저장 완료 ({args.out})")


if __name__ == "__main__":
    main()
